#pragma once
#include <cstddef>
#include <algorithm>
#include <atomic>
#include <condition_variable>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

// ============================================================================
//  THE ONLY FILE AN AGENT MAY EDIT.
//
//  Task: compute C = A * B for row-major N x N double matrices, as fast as
//  possible, WITHOUT changing the result (bench.cpp checks correctness against
//  an independent reference and will reject any wrong answer).
//
//  Strategy (standard headers only, no external libraries):
//    * loop order i-k-j so the inner loop streams contiguously over B and C,
//      which the compiler auto-vectorizes into AVX2+FMA;
//    * 4-row register blocking so each loaded B[k][j] vector feeds four FMAs,
//      cutting B memory traffic 4x and raising arithmetic intensity;
//    * k-blocking so the reused B panel stays resident in cache;
//    * a persistent thread pool with dynamic (work-stealing) scheduling, which
//      load-balances cleanly across this machine's heterogeneous P/E cores.
//
//  Reordering the additions changes only floating-point rounding at the ~1e-15
//  level, far inside the benchmark's 1e-9 relative-error gate.
// ============================================================================
namespace solution {
namespace detail {

// --- Minimal persistent thread pool (barrier-style: run() blocks until done).
class ThreadPool {
public:
    explicit ThreadPool(unsigned n) : n_(n ? n : 1u) {
        workers_.reserve(n_);
        for (unsigned t = 0; t < n_; ++t)
            workers_.emplace_back([this, t] { loop(t); });
    }
    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lk(m_);
            stop_ = true;
            ++gen_;
        }
        cv_start_.notify_all();
        for (auto& w : workers_) w.join();
    }
    unsigned size() const { return n_; }

    // Run job(threadId) on every worker; returns once all have finished.
    void run(const std::function<void(unsigned)>& job) {
        {
            std::lock_guard<std::mutex> lk(m_);
            job_ = &job;
            remaining_ = n_;
            ++gen_;
        }
        cv_start_.notify_all();
        std::unique_lock<std::mutex> lk(m_);
        cv_done_.wait(lk, [this] { return remaining_ == 0; });
        job_ = nullptr;
    }

private:
    void loop(unsigned t) {
        unsigned local = 0;
        for (;;) {
            const std::function<void(unsigned)>* job = nullptr;
            {
                std::unique_lock<std::mutex> lk(m_);
                cv_start_.wait(lk, [this, local] { return gen_ != local; });
                local = gen_;
                if (stop_) return;
                job = job_;
            }
            (*job)(t);
            {
                std::lock_guard<std::mutex> lk(m_);
                if (--remaining_ == 0) cv_done_.notify_one();
            }
        }
    }

    unsigned n_;
    std::vector<std::thread> workers_;
    std::mutex m_;
    std::condition_variable cv_start_, cv_done_;
    const std::function<void(unsigned)>* job_ = nullptr;
    unsigned remaining_ = 0;
    unsigned gen_ = 0;
    bool stop_ = false;
};

inline ThreadPool& pool() {
    static ThreadPool p(std::thread::hardware_concurrency());
    return p;
}

// Compute rows [r0, r1) of C. The i-k-j order accumulates each C[i][j] over k in
// exactly the reference's ascending order; FMA contraction is disabled so each
// multiply rounds separately, matching the reference and staying inside the
// 1e-9 gate. The j-loops still auto-vectorize (AVX2 mul+add).
#if defined(__clang__)
#pragma clang fp contract(off)
#endif
#if defined(__GNUC__) && !defined(__clang__)
__attribute__((optimize("-ffp-contract=off")))
#endif
inline void mm_rows(const double* __restrict A, const double* __restrict B,
                    double* __restrict C, std::size_t N,
                    std::size_t r0, std::size_t r1) {
    constexpr std::size_t KC = 128;  // k-block: keeps the reused B panel hot

    // Zero this chunk's output rows once.
    for (std::size_t i = r0; i < r1; ++i) {
        double* Ci = C + i * N;
        for (std::size_t j = 0; j < N; ++j) Ci[j] = 0.0;
    }

    for (std::size_t kk = 0; kk < N; kk += KC) {
        const std::size_t kmax = std::min(kk + KC, N);

        std::size_t i = r0;
        for (; i + 4 <= r1; i += 4) {  // 4-row register block
            double* __restrict C0 = C + (i + 0) * N;
            double* __restrict C1 = C + (i + 1) * N;
            double* __restrict C2 = C + (i + 2) * N;
            double* __restrict C3 = C + (i + 3) * N;
            const double* A0 = A + (i + 0) * N;
            const double* A1 = A + (i + 1) * N;
            const double* A2 = A + (i + 2) * N;
            const double* A3 = A + (i + 3) * N;
            for (std::size_t k = kk; k < kmax; ++k) {
                const double a0 = A0[k], a1 = A1[k], a2 = A2[k], a3 = A3[k];
                const double* __restrict Bk = B + k * N;
                for (std::size_t j = 0; j < N; ++j) {
                    const double b = Bk[j];
                    C0[j] += a0 * b;
                    C1[j] += a1 * b;
                    C2[j] += a2 * b;
                    C3[j] += a3 * b;
                }
            }
        }
        for (; i < r1; ++i) {  // remainder rows (<4)
            double* __restrict Ci = C + i * N;
            const double* Ai = A + i * N;
            for (std::size_t k = kk; k < kmax; ++k) {
                const double a = Ai[k];
                const double* __restrict Bk = B + k * N;
                for (std::size_t j = 0; j < N; ++j) Ci[j] += a * Bk[j];
            }
        }
    }
}

} // namespace detail

inline void matmul(const double* A, const double* B, double* C, std::size_t N) {
    if (N == 0) return;

    detail::ThreadPool& tp = detail::pool();

    constexpr std::size_t CHUNK = 8;  // rows per work unit (dynamic stealing)
    const std::size_t nchunks = (N + CHUNK - 1) / CHUNK;
    std::atomic<std::size_t> next{0};

    auto job = [&](unsigned) {
        for (;;) {
            std::size_t c = next.fetch_add(1, std::memory_order_relaxed);
            if (c >= nchunks) break;
            const std::size_t r0 = c * CHUNK;
            const std::size_t r1 = std::min(r0 + CHUNK, N);
            detail::mm_rows(A, B, C, N, r0, r1);
        }
    };

    tp.run(job);
}

} // namespace solution
