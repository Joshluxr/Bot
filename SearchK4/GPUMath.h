/*
 * Optimized GPU Math Library for SECP256K1
 * Provides 256-bit arithmetic optimized for CUDA
 */

#ifndef _GPU_MATH_H_
#define _GPU_MATH_H_

#include <stdint.h>

// 256-bit type definition
typedef struct {
    uint64_t d[4];
} uint256_t;

// Optimized 256-bit addition
__device__ __forceinline__ void add256(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t carry = 0;
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        uint64_t ai = a[i], bi = b[i];
        uint64_t sum = ai + bi + carry;
        carry = (sum < ai) ? 1 : 0;  // Check for overflow
        r[i] = sum;
    }
}

// Optimized 256-bit subtraction  
__device__ __forceinline__ void sub256(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t borrow = 0;
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        uint64_t ai = a[i], bi = b[i];
        uint64_t diff = ai - bi - borrow;
        borrow = (ai < bi + borrow) ? 1 : 0;  // Check for underflow  
        r[i] = diff;
    }
}

// Optimized 256-bit multiplication
__device__ __forceinline__ void mul256(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    __uint128_t t[8] = {0};
    
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        __uint128_t c = 0;
        #pragma unroll 4
        for (int j = 0; j < 4; j++) {
            c += t[i + j] + (__uint128_t)a[i] * b[j];
            t[i + j] = (uint64_t)c;
            c >>= 64;
        }
        t[i + 4] = c;
    }
    
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        r[i] = (uint64_t)t[i];
    }
}

// Compare two 256-bit numbers: returns 1 if a > b, -1 if a < b, 0 if equal
__device__ __forceinline__ int cmp256(const uint64_t* a, const uint64_t* b) {
    #pragma unroll 4
    for (int i = 3; i >= 0; i--) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
}

// Modular addition: r = (a + b) mod p
__device__ __forceinline__ void mod_add(uint64_t* r, const uint64_t* a, const uint64_t* b, const uint64_t* p) {
    add256(r, a, b);
    if (cmp256(r, p) >= 0) sub256(r, r, p);
}

// Modular subtraction: r = (a - b) mod p  
__device__ __forceinline__ void mod_sub(uint64_t* r, const uint64_t* a, const uint64_t* b, const uint64_t* p) {
    sub256(r, a, b);
    if (cmp256(r, p) < 0) add256(r, r, p);
}

// Optimized modular multiplication for secp256k1
// p = 2^256 - 0x1000003D1 (Fermat prime)
__device__ __forceinline__ void mod_mul(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    __uint128_t t[8] = {0};
    
    // Full 4x4 multiplication
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        __uint128_t c = 0;
        #pragma unroll 4
        for (int j = 0; j < 4; j++) {
            c += t[i + j] + (__uint128_t)a[i] * b[j];
            t[i + j] = (uint64_t)c;
            c >>= 64;
        }
        t[i + 4] = c;
    }

    // Fast reduction using 0x1000003D1 = 2^32 + 0x3D1
    uint64_t low[4], high[4], res[5];
    
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        low[i] = (uint64_t)t[i];
        high[i] = (uint64_t)t[i + 4];
    }

    __uint128_t c = 0;
    #pragma unroll 4
    for (int i = 0; i < 4; i++) {
        c += (__uint128_t)low[i] + (__uint128_t)high[i] * 0x1000003D1ULL;
        res[i] = (uint64_t)c;
        c >>= 64;
    }
    res[4] = (uint64_t)c;
    
    // Handle carry beyond 256 bits
    if (res[4]) {
        c = (__uint128_t)res[0] + (__uint128_t)res[4] * 0x1000003D1ULL;
        res[0] = (uint64_t)c;
        c >>= 64;
        #pragma unroll 3
        for (int i = 1; i < 4 && c; i++) {
            c += res[i];
            res[i] = (uint64_t)c;
            c >>= 64;
        }
    }
    
    // Final modular reduction if needed
    #pragma unroll 4
    for (int i = 0; i < 4; i++) r[i] = res[i];
    if (cmp256(r, p) >= 0) sub256(r, r, p);
}

#endif // _GPU_MATH_H_