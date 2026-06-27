#pragma once
#include <cstddef>

// ============================================================================
//  THE ONLY FILE AN AGENT MAY EDIT.
//
//  Task: compute C = A * B for row-major N x N double matrices, as fast as
//  possible, WITHOUT changing the result (bench.cpp checks correctness against
//  an independent reference and will reject any wrong answer).
//
//  Allowed: loop reordering, cache blocking/tiling, `restrict`, alignment,
//  SIMD-friendly code, register blocking, std headers only.
//  Not allowed: external libraries (BLAS/Eigen), changing the signature,
//  editing bench.cpp or reference correctness.
//
//  This starting point is deliberately naive (cache-unfriendly inner loop).
// ============================================================================
namespace solution {

inline void matmul(const double* A, const double* B, double* C, std::size_t N) {
    for (std::size_t i = 0; i < N; ++i) {
        for (std::size_t j = 0; j < N; ++j) {
            double s = 0.0;
            for (std::size_t k = 0; k < N; ++k) {
                s += A[i * N + k] * B[k * N + j]; // strides badly through B
            }
            C[i * N + j] = s;
        }
    }
}

} // namespace solution
