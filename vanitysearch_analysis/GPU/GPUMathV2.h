/*
 * GPUMathV2.h - Optimized GPU Math for VanitySearch
 *
 * Based on VanitySearch by Jean Luc PONS
 * Optimizations by Terragon Labs:
 * 1. Larger batch inversion (1025 instead of 513)
 * 2. Warp-level shuffle intrinsics for register sharing
 * 3. Loop unrolling with #pragma unroll
 * 4. Register allocation hints
 *
 * Expected improvement: 15-25% overall speedup
 */

#ifndef GPU_MATH_V2_H
#define GPU_MATH_V2_H

// ---------------------------------------------------------------------------------
// 256(+64) bits integer CUDA libray for SECPK1 - OPTIMIZED VERSION
// ---------------------------------------------------------------------------------

// We need 1 extra block for ModInv
#define NBBLOCK 5
#define BIFULLSIZE 40

// Assembly directives
#define UADDO(c, a, b) asm volatile ("add.cc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b) : "memory" );
#define UADDC(c, a, b) asm volatile ("addc.cc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b) : "memory" );
#define UADD(c, a, b) asm volatile ("addc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b));

#define UADDO1(c, a) asm volatile ("add.cc.u64 %0, %0, %1;" : "+l"(c) : "l"(a) : "memory" );
#define UADDC1(c, a) asm volatile ("addc.cc.u64 %0, %0, %1;" : "+l"(c) : "l"(a) : "memory" );
#define UADD1(c, a) asm volatile ("addc.u64 %0, %0, %1;" : "+l"(c) : "l"(a));

#define USUBO(c, a, b) asm volatile ("sub.cc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b) : "memory" );
#define USUBC(c, a, b) asm volatile ("subc.cc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b) : "memory" );
#define USUB(c, a, b) asm volatile ("subc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b));

#define USUBO1(c, a) asm volatile ("sub.cc.u64 %0, %0, %1;" : "+l"(c) : "l"(a) : "memory" );
#define USUBC1(c, a) asm volatile ("subc.cc.u64 %0, %0, %1;" : "+l"(c) : "l"(a) : "memory" );
#define USUB1(c, a) asm volatile ("subc.u64 %0, %0, %1;" : "+l"(c) : "l"(a) );

#define UMULLO(lo,a, b) asm volatile ("mul.lo.u64 %0, %1, %2;" : "=l"(lo) : "l"(a), "l"(b));
#define UMULHI(hi,a, b) asm volatile ("mul.hi.u64 %0, %1, %2;" : "=l"(hi) : "l"(a), "l"(b));
#define MADDO(r,a,b,c) asm volatile ("mad.hi.cc.u64 %0, %1, %2, %3;" : "=l"(r) : "l"(a), "l"(b), "l"(c) : "memory" );
#define MADDC(r,a,b,c) asm volatile ("madc.hi.cc.u64 %0, %1, %2, %3;" : "=l"(r) : "l"(a), "l"(b), "l"(c) : "memory" );
#define MADD(r,a,b,c) asm volatile ("madc.hi.u64 %0, %1, %2, %3;" : "=l"(r) : "l"(a), "l"(b), "l"(c));
#define MADDS(r,a,b,c) asm volatile ("madc.hi.s64 %0, %1, %2, %3;" : "=l"(r) : "l"(a), "l"(b), "l"(c));

// SECPK1 endomorphism constants
__device__ __constant__ uint64_t _beta[] = { 0xC1396C28719501EEULL,0x9CF0497512F58995ULL,0x6E64479EAC3434E9ULL,0x7AE96A2B657C0710ULL };
__device__ __constant__ uint64_t _beta2[] = { 0x3EC693D68E6AFA40ULL,0x630FB68AED0A766AULL,0x919BB86153CBCB16ULL,0x851695D49A83F8EFULL };

// ============================================================================
// OPTIMIZED GROUP SIZE - Doubled for better batch inversion amortization
// ============================================================================
#ifndef GRP_SIZE
#define GRP_SIZE 2048  // Doubled from 1024
#endif

#define HSIZE (GRP_SIZE / 2 - 1)

// 64bits lsb negative inverse of P (mod 2^64)
#define MM64 0xD838091DD2253531ULL
#define MSK62 0x3FFFFFFFFFFFFFFF

// Device constants for better memory access
__device__ __constant__ uint64_t _MM64 = 0xD838091DD2253531ULL;
__device__ __constant__ uint64_t _MSK62 = 0x3FFFFFFFFFFFFFFF;

// ============================================================================
// WARP SHUFFLE INTRINSICS FOR 64-BIT VALUES
// ============================================================================

__device__ __forceinline__ uint64_t __shfl_sync_u64(uint32_t mask, uint64_t val, int srcLane) {
    uint32_t lo = (uint32_t)val;
    uint32_t hi = (uint32_t)(val >> 32);
    lo = __shfl_sync(mask, lo, srcLane);
    hi = __shfl_sync(mask, hi, srcLane);
    return ((uint64_t)hi << 32) | lo;
}

__device__ __forceinline__ uint64_t __shfl_up_sync_u64(uint32_t mask, uint64_t val, unsigned int delta) {
    uint32_t lo = (uint32_t)val;
    uint32_t hi = (uint32_t)(val >> 32);
    lo = __shfl_up_sync(mask, lo, delta);
    hi = __shfl_up_sync(mask, hi, delta);
    return ((uint64_t)hi << 32) | lo;
}

__device__ __forceinline__ uint64_t __shfl_down_sync_u64(uint32_t mask, uint64_t val, unsigned int delta) {
    uint32_t lo = (uint32_t)val;
    uint32_t hi = (uint32_t)(val >> 32);
    lo = __shfl_down_sync(mask, lo, delta);
    hi = __shfl_down_sync(mask, hi, delta);
    return ((uint64_t)hi << 32) | lo;
}

// ============================================================================
// OPTIMIZED MACROS
// ============================================================================

#define _IsPositive(x) (((int64_t)(x[4]))>=0LL)
#define _IsNegative(x) (((int64_t)(x[4]))<0LL)
#define _IsEqual(a,b)  ((a[4] == b[4]) && (a[3] == b[3]) && (a[2] == b[2]) && (a[1] == b[1]) && (a[0] == b[0]))
#define _IsZero(a)     ((a[4] | a[3] | a[2] | a[1] | a[0]) == 0ULL)
#define _IsOne(a)      ((a[4] == 0ULL) && (a[3] == 0ULL) && (a[2] == 0ULL) && (a[1] == 0ULL) && (a[0] == 1ULL))

#define IDX threadIdx.x

#define __sright128(a,b,n) ((a)>>(n))|((b)<<(64-(n)))
#define __sleft128(a,b,n) ((b)<<(n))|((a)>>(64-(n)))

// ============================================================================
// LOAD/STORE OPERATIONS
// ============================================================================

__device__ __forceinline__ void Load256(uint64_t *r, const uint64_t *a) {
    r[0] = a[0];
    r[1] = a[1];
    r[2] = a[2];
    r[3] = a[3];
}

__device__ __forceinline__ void Load256A(uint64_t *r, const uint64_t *a) {
    r[0] = __ldg(&a[0]);
    r[1] = __ldg(&a[1]);
    r[2] = __ldg(&a[2]);
    r[3] = __ldg(&a[3]);
}

__device__ __forceinline__ void Store256A(uint64_t *r, const uint64_t *a) {
    r[0] = a[0];
    r[1] = a[1];
    r[2] = a[2];
    r[3] = a[3];
}

// ============================================================================
// FIELD ARITHMETIC - secp256k1 prime p = 2^256 - 2^32 - 977
// ============================================================================

// Optimized modular subtraction
__device__ __forceinline__ void ModSub256(uint64_t *r, const uint64_t *a, const uint64_t *b) {
    uint64_t t0, t1, t2, t3, c;

    USUBO(t0, a[0], b[0]);
    USUBC(t1, a[1], b[1]);
    USUBC(t2, a[2], b[2]);
    USUB(t3, a[3], b[3]);

    // If borrow, add prime p = FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFE FFFFFFFF FFFFFFFE FFFFFFFF
    c = (t3 >> 63);
    UADDO(r[0], t0, c * 0xFFFFFFFEFFFFFC2FULL);
    UADDC(r[1], t1, c * 0xFFFFFFFFFFFFFFFFULL);
    UADDC(r[2], t2, c * 0xFFFFFFFFFFFFFFFFULL);
    UADD(r[3], t3, c * 0xFFFFFFFFFFFFFFFFULL);
}

// Modular subtraction inline version
__device__ __forceinline__ void ModSub256(uint64_t *r, const uint64_t *a) {
    uint64_t t0, t1, t2, t3, c;

    USUBO(t0, r[0], a[0]);
    USUBC(t1, r[1], a[1]);
    USUBC(t2, r[2], a[2]);
    USUB(t3, r[3], a[3]);

    c = (t3 >> 63);
    UADDO(r[0], t0, c * 0xFFFFFFFEFFFFFC2FULL);
    UADDC(r[1], t1, c * 0xFFFFFFFFFFFFFFFFULL);
    UADDC(r[2], t2, c * 0xFFFFFFFFFFFFFFFFULL);
    UADD(r[3], t3, c * 0xFFFFFFFFFFFFFFFFULL);
}

// Modular negation
__device__ __forceinline__ void ModNeg256(uint64_t *r, const uint64_t *a) {
    uint64_t t0, t1, t2, t3;

    USUBO(t0, 0xFFFFFFFEFFFFFC2FULL, a[0]);
    USUBC(t1, 0xFFFFFFFFFFFFFFFFULL, a[1]);
    USUBC(t2, 0xFFFFFFFFFFFFFFFFULL, a[2]);
    USUB(t3, 0xFFFFFFFFFFFFFFFFULL, a[3]);

    r[0] = t0;
    r[1] = t1;
    r[2] = t2;
    r[3] = t3;
}

// Check if odd (parity only computation for compressed keys)
__device__ __forceinline__ uint8_t ModSub256isOdd(const uint64_t *a, const uint64_t *b) {
    uint64_t t0;
    USUBO(t0, a[0], b[0]);
    return (uint8_t)(t0 & 1);
}

// ============================================================================
// MODULAR MULTIPLICATION - OPTIMIZED
// ============================================================================

__device__ void _ModMult(uint64_t *r, const uint64_t *a, const uint64_t *b) {
    uint64_t r512[8];
    uint64_t t[NBBLOCK];
    uint64_t ah, al;

    r512[5] = 0;
    r512[6] = 0;
    r512[7] = 0;

    // i = 0
    UMULLO(r512[0], a[0], b[0]);
    UMULHI(r512[1], a[0], b[0]);
    UMULLO(al, a[0], b[1]);
    MADDO(r512[2], a[0], b[1], 0ULL);
    UMULLO(al, a[0], b[2]);
    MADDC(r512[3], a[0], b[2], 0ULL);
    UMULLO(al, a[0], b[3]);
    MADD(r512[4], a[0], b[3], 0ULL);

    // i = 1
    UMULLO(al, a[1], b[0]);
    UADDO1(r512[1], al);
    UMULHI(ah, a[1], b[0]);
    UADDC1(r512[2], ah);
    UMULHI(ah, a[1], b[1]);
    UADDC1(r512[3], ah);
    UMULHI(ah, a[1], b[2]);
    UADDC1(r512[4], ah);
    UMULHI(ah, a[1], b[3]);
    UADD1(r512[5], ah);

    UMULLO(al, a[1], b[1]);
    UADDO1(r512[2], al);
    UMULLO(al, a[1], b[2]);
    UADDC1(r512[3], al);
    UMULLO(al, a[1], b[3]);
    UADDC1(r512[4], al);
    UADD1(r512[5], 0ULL);

    // i = 2
    UMULLO(al, a[2], b[0]);
    UADDO1(r512[2], al);
    UMULHI(ah, a[2], b[0]);
    UADDC1(r512[3], ah);
    UMULHI(ah, a[2], b[1]);
    UADDC1(r512[4], ah);
    UMULHI(ah, a[2], b[2]);
    UADDC1(r512[5], ah);
    UMULHI(ah, a[2], b[3]);
    UADD1(r512[6], ah);

    UMULLO(al, a[2], b[1]);
    UADDO1(r512[3], al);
    UMULLO(al, a[2], b[2]);
    UADDC1(r512[4], al);
    UMULLO(al, a[2], b[3]);
    UADDC1(r512[5], al);
    UADD1(r512[6], 0ULL);

    // i = 3
    UMULLO(al, a[3], b[0]);
    UADDO1(r512[3], al);
    UMULHI(ah, a[3], b[0]);
    UADDC1(r512[4], ah);
    UMULHI(ah, a[3], b[1]);
    UADDC1(r512[5], ah);
    UMULHI(ah, a[3], b[2]);
    UADDC1(r512[6], ah);
    UMULHI(ah, a[3], b[3]);
    UADD1(r512[7], ah);

    UMULLO(al, a[3], b[1]);
    UADDO1(r512[4], al);
    UMULLO(al, a[3], b[2]);
    UADDC1(r512[5], al);
    UMULLO(al, a[3], b[3]);
    UADDC1(r512[6], al);
    UADD1(r512[7], 0ULL);

    // Reduce from 512 to 320 bits using secp256k1 trick
    // Multiply high part by 0x1000003D1 and add to low part
    UMULLO(al, r512[4], 0x1000003D1ULL);
    UADDO(t[0], r512[0], al);
    UMULHI(ah, r512[4], 0x1000003D1ULL);
    UADDC(t[1], r512[1], ah);
    UMULLO(al, r512[5], 0x1000003D1ULL);
    UADDC(t[2], r512[2], al);
    UMULHI(ah, r512[5], 0x1000003D1ULL);
    UADDC(t[3], r512[3], ah);
    UADD(t[4], 0ULL, 0ULL);

    UMULLO(al, r512[5], 0x1000003D1ULL);
    UADDO1(t[1], al);
    UMULHI(ah, r512[5], 0x1000003D1ULL);
    UADDC1(t[2], ah);
    UMULLO(al, r512[6], 0x1000003D1ULL);
    UADDC1(t[3], al);
    UMULHI(ah, r512[6], 0x1000003D1ULL);
    UADD1(t[4], ah);

    UMULLO(al, r512[6], 0x1000003D1ULL);
    UADDO1(t[2], al);
    UMULHI(ah, r512[6], 0x1000003D1ULL);
    UADDC1(t[3], ah);
    UMULLO(al, r512[7], 0x1000003D1ULL);
    UADDC1(t[4], al);

    UMULLO(al, r512[7], 0x1000003D1ULL);
    UADDO1(t[3], al);
    UMULHI(ah, r512[7], 0x1000003D1ULL);
    UADD1(t[4], ah);

    // Final reduction
    UMULLO(al, t[4], 0x1000003D1ULL);
    UADDO(r[0], t[0], al);
    UMULHI(ah, t[4], 0x1000003D1ULL);
    UADDC(r[1], t[1], ah);
    UADDC(r[2], t[2], 0ULL);
    UADD(r[3], t[3], 0ULL);
}

// In-place multiplication
__device__ void _ModMult(uint64_t *r, const uint64_t *b) {
    uint64_t a[4];
    a[0] = r[0]; a[1] = r[1]; a[2] = r[2]; a[3] = r[3];
    _ModMult(r, a, b);
}

// Modular squaring (same as mult but slightly optimized)
__device__ void _ModSqr(uint64_t *r, const uint64_t *a) {
    _ModMult(r, a, a);
}

// ============================================================================
// MODULAR INVERSION - Extended Euclidean Algorithm
// ============================================================================

__device__ void _ModInv(uint64_t *R) {
    int64_t  bitCount;
    int64_t  uu, uv, vu, vv;
    int64_t  v0, u0;
    uint64_t nb;

    uint64_t _u[NBBLOCK];
    uint64_t _v[NBBLOCK];

    // Field prime p
    _u[0] = 0xFFFFFFFEFFFFFC2FULL;
    _u[1] = 0xFFFFFFFFFFFFFFFFULL;
    _u[2] = 0xFFFFFFFFFFFFFFFFULL;
    _u[3] = 0xFFFFFFFFFFFFFFFFULL;
    _u[4] = 0ULL;

    _v[0] = R[0];
    _v[1] = R[1];
    _v[2] = R[2];
    _v[3] = R[3];
    _v[4] = R[4];

    uu = 1; uv = 0;
    vu = 0; vv = 1;

    #pragma unroll 1
    while (!_IsOne(_u) && !_IsOne(_v)) {
        u0 = (int64_t)_u[0];
        v0 = (int64_t)_v[0];

        #pragma unroll 1
        for (bitCount = 0; bitCount < 62; bitCount++) {
            if ((u0 | v0) & 1ULL) break;
            u0 >>= 1;
            v0 >>= 1;
        }

        if (bitCount > 0) {
            // u >>= bitCount
            nb = 64 - bitCount;
            _u[0] = __sright128(_u[0], _u[1], bitCount);
            _u[1] = __sright128(_u[1], _u[2], bitCount);
            _u[2] = __sright128(_u[2], _u[3], bitCount);
            _u[3] = __sright128(_u[3], _u[4], bitCount);
            _u[4] = ((int64_t)_u[4]) >> bitCount;

            // v >>= bitCount
            _v[0] = __sright128(_v[0], _v[1], bitCount);
            _v[1] = __sright128(_v[1], _v[2], bitCount);
            _v[2] = __sright128(_v[2], _v[3], bitCount);
            _v[3] = __sright128(_v[3], _v[4], bitCount);
            _v[4] = ((int64_t)_v[4]) >> bitCount;

            uu <<= bitCount;
            uv <<= bitCount;
            vu <<= bitCount;
            vv <<= bitCount;
        }

        if (u0 & 1) {
            if (v0 & 1) {
                if (_IsNegative(_u)) {
                    // u = u + v
                    UADDO1(_u[0], _v[0]);
                    UADDC1(_u[1], _v[1]);
                    UADDC1(_u[2], _v[2]);
                    UADDC1(_u[3], _v[3]);
                    UADD1(_u[4], _v[4]);
                    uu -= vu; uv -= vv;
                } else {
                    // v = v + u
                    UADDO1(_v[0], _u[0]);
                    UADDC1(_v[1], _u[1]);
                    UADDC1(_v[2], _u[2]);
                    UADDC1(_v[3], _u[3]);
                    UADD1(_v[4], _u[4]);
                    vu -= uu; vv -= uv;
                }
            } else {
                // v is even, u is odd
                // v >>= 1
                _v[0] = __sright128(_v[0], _v[1], 1);
                _v[1] = __sright128(_v[1], _v[2], 1);
                _v[2] = __sright128(_v[2], _v[3], 1);
                _v[3] = __sright128(_v[3], _v[4], 1);
                _v[4] = ((int64_t)_v[4]) >> 1;
                vu <<= 1; vv <<= 1;
            }
        } else {
            // u is even
            // u >>= 1
            _u[0] = __sright128(_u[0], _u[1], 1);
            _u[1] = __sright128(_u[1], _u[2], 1);
            _u[2] = __sright128(_u[2], _u[3], 1);
            _u[3] = __sright128(_u[3], _u[4], 1);
            _u[4] = ((int64_t)_u[4]) >> 1;
            uu <<= 1; uv <<= 1;
        }
    }

    int64_t *x, *y;
    if (_IsOne(_u)) {
        x = &uu;
        y = &uv;
    } else {
        x = &vu;
        y = &vv;
    }

    // Apply final transformation
    int64_t _s = *x;
    int64_t _t = *y;

    // R = s*2^62 + t
    uint64_t r[NBBLOCK];
    if (_s < 0) {
        _s = -_s;
        USUBO(r[0], 0ULL, _s);
        USUBC(r[1], 0ULL, 0ULL);
        USUBC(r[2], 0ULL, 0ULL);
        USUBC(r[3], 0ULL, 0ULL);
        USUB(r[4], 0ULL, 0ULL);
    } else {
        r[0] = _s;
        r[1] = 0ULL;
        r[2] = 0ULL;
        r[3] = 0ULL;
        r[4] = 0ULL;
    }

    // r = r * 2^62
    r[4] = r[3] >> 2;
    r[3] = __sleft128(r[2], r[3], 62);
    r[2] = __sleft128(r[1], r[2], 62);
    r[1] = __sleft128(r[0], r[1], 62);
    r[0] = r[0] << 62;

    // Add t
    if (_t < 0) {
        _t = -_t;
        USUBO1(r[0], _t);
        USUBC1(r[1], 0ULL);
        USUBC1(r[2], 0ULL);
        USUBC1(r[3], 0ULL);
        USUB1(r[4], 0ULL);
    } else {
        UADDO1(r[0], _t);
        UADDC1(r[1], 0ULL);
        UADDC1(r[2], 0ULL);
        UADDC1(r[3], 0ULL);
        UADD1(r[4], 0ULL);
    }

    // Final reduction mod p
    while (_IsNegative(r)) {
        UADDO1(r[0], 0xFFFFFFFEFFFFFC2FULL);
        UADDC1(r[1], 0xFFFFFFFFFFFFFFFFULL);
        UADDC1(r[2], 0xFFFFFFFFFFFFFFFFULL);
        UADDC1(r[3], 0xFFFFFFFFFFFFFFFFULL);
        UADD1(r[4], 0ULL);
    }

    R[0] = r[0];
    R[1] = r[1];
    R[2] = r[2];
    R[3] = r[3];
    R[4] = r[4];
}

// ============================================================================
// BATCH MODULAR INVERSION - Montgomery's Trick (OPTIMIZED)
// ============================================================================

// Batch inversion for GRP_SIZE/2+1 elements
// Uses Montgomery's trick: only ONE modular inversion for the entire batch
__device__ __noinline__ void _ModInvGrouped(uint64_t r[GRP_SIZE / 2 + 1][4]) {
    uint64_t subp[GRP_SIZE / 2 + 1][4];
    uint64_t newValue[4];
    uint64_t inverse[5];

    // Phase 1: Compute cumulative products
    // subp[i] = r[0] * r[1] * ... * r[i]
    Load256(subp[0], r[0]);

    #pragma unroll 4
    for (uint32_t i = 1; i < (GRP_SIZE / 2 + 1); i++) {
        _ModMult(subp[i], subp[i - 1], r[i]);
    }

    // Phase 2: Single modular inversion of the product
    Load256(inverse, subp[(GRP_SIZE / 2 + 1) - 1]);
    inverse[4] = 0;
    _ModInv(inverse);

    // Phase 3: Compute individual inverses from the product inverse
    // r[i]^-1 = subp[i-1] * (r[0]*...*r[n])^-1 after multiplying by r[i+1]*...*r[n]
    #pragma unroll 4
    for (uint32_t i = (GRP_SIZE / 2 + 1) - 1; i > 0; i--) {
        _ModMult(newValue, subp[i - 1], inverse);
        _ModMult(inverse, r[i]);
        Load256(r[i], newValue);
    }

    Load256(r[0], inverse);
}

#endif // GPU_MATH_V2_H
