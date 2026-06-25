// Benchmark driver + correctness gate. AGENTS MUST NOT EDIT THIS FILE.
//
// It (1) builds deterministic inputs, (2) computes an independent reference
// result, (3) checks the agent's solution against it, and (4) times the
// solution and prints one machine-readable line:
//
//     RESULT correct=<0|1> gflops=<double> ms=<double> maxrelerr=<double> n=<N>
//
// The loop reads this line to gate on correctness and track GFLOP/s.

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

#include "solution.hpp"

// Independent reference (simple, trusted). Not visible to the agent's edits.
static void reference_matmul(const double* A, const double* B, double* C,
                             std::size_t N) {
    for (std::size_t i = 0; i < N; ++i)
        for (std::size_t j = 0; j < N; ++j) {
            double s = 0.0;
            for (std::size_t k = 0; k < N; ++k) s += A[i * N + k] * B[k * N + j];
            C[i * N + j] = s;
        }
}

int main(int argc, char** argv) {
    std::size_t N = (argc > 1) ? std::strtoul(argv[1], nullptr, 10) : 512;
    unsigned seed = (argc > 2) ? std::strtoul(argv[2], nullptr, 10) : 12345u;

    std::vector<double> A(N * N), B(N * N), C(N * N), R(N * N);
    std::mt19937 rng(seed);
    std::uniform_real_distribution<double> dist(-1.0, 1.0);
    for (auto& x : A) x = dist(rng);
    for (auto& x : B) x = dist(rng);

    // Reference + correctness check (also acts as a warmup of the solution).
    reference_matmul(A.data(), B.data(), R.data(), N);
    solution::matmul(A.data(), B.data(), C.data(), N);

    double maxrel = 0.0;
    for (std::size_t i = 0; i < N * N; ++i) {
        double diff = std::fabs(C[i] - R[i]);
        double den = std::fabs(R[i]) + 1e-12;
        maxrel = std::max(maxrel, diff / den);
    }
    bool correct = (maxrel < 1e-9);

    // Time: repeat enough to run for a stable interval; report best run.
    const double flops = 2.0 * double(N) * double(N) * double(N);
    int reps = 1;
    double best_ms = 1e30;
    auto t_total0 = std::chrono::steady_clock::now();
    while (true) {
        auto t0 = std::chrono::steady_clock::now();
        solution::matmul(A.data(), B.data(), C.data(), N);
        auto t1 = std::chrono::steady_clock::now();
        double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
        if (ms < best_ms) best_ms = ms;
        ++reps;
        double elapsed =
            std::chrono::duration<double>(t1 - t_total0).count();
        if (reps >= 3 && elapsed > 1.0) break; // >=3 runs and >=1s total
        if (reps > 200) break;
    }
    double gflops = flops / (best_ms / 1000.0) / 1e9;

    std::printf("RESULT correct=%d gflops=%.3f ms=%.3f maxrelerr=%.3e n=%zu\n",
                correct ? 1 : 0, gflops, best_ms, maxrel, N);
    return correct ? 0 : 1;
}
