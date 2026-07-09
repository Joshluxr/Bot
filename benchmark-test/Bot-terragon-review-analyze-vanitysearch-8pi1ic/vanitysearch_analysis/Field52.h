/*
 * 5x52-bit Field Element Implementation for secp256k1
 * Based on libsecp256k1's approach for maximum performance
 *
 * Key insight: 52-bit limbs allow lazy reduction since 52*2 = 104 < 128
 * This means we can accumulate multiple multiplications before reducing
 */

#ifndef FIELD52_H
#define FIELD52_H

#include <stdint.h>
#include <string.h>

// secp256k1 prime: p = 2^256 - 2^32 - 977
// In hex: FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFF FFFFFFFE FFFFFC2F

#define FIELD_LIMB_BITS 52
#define FIELD_LIMB_MASK ((1ULL << 52) - 1)

// 5 limbs of 52 bits = 260 bits (4 extra bits for overflow)
typedef struct {
    uint64_t n[5];
} field_elem;

// Magnitude: tracks how far the element is from being fully reduced
// Allows lazy reduction - only reduce when magnitude gets too high

//------------------------------------------------------------------------------
// Initialization
//------------------------------------------------------------------------------

static inline void field_clear(field_elem *r) {
    r->n[0] = 0; r->n[1] = 0; r->n[2] = 0; r->n[3] = 0; r->n[4] = 0;
}

static inline void field_set_int(field_elem *r, uint64_t a) {
    r->n[0] = a & FIELD_LIMB_MASK;
    r->n[1] = a >> 52;
    r->n[2] = 0;
    r->n[3] = 0;
    r->n[4] = 0;
}

// Convert from 4x64-bit representation to 5x52-bit
static inline void field_from_64(field_elem *r, const uint64_t *a) {
    r->n[0] = a[0] & FIELD_LIMB_MASK;
    r->n[1] = ((a[0] >> 52) | (a[1] << 12)) & FIELD_LIMB_MASK;
    r->n[2] = ((a[1] >> 40) | (a[2] << 24)) & FIELD_LIMB_MASK;
    r->n[3] = ((a[2] >> 28) | (a[3] << 36)) & FIELD_LIMB_MASK;
    r->n[4] = a[3] >> 16;
}

// Convert from 5x52-bit back to 4x64-bit
static inline void field_to_64(uint64_t *r, const field_elem *a) {
    r[0] = a->n[0] | (a->n[1] << 52);
    r[1] = (a->n[1] >> 12) | (a->n[2] << 40);
    r[2] = (a->n[2] >> 24) | (a->n[3] << 28);
    r[3] = (a->n[3] >> 36) | (a->n[4] << 16);
}

// Set from 32 bytes (big endian)
static inline void field_set_bytes(field_elem *r, const unsigned char *b) {
    r->n[0] = (uint64_t)b[31] | ((uint64_t)b[30] << 8) | ((uint64_t)b[29] << 16) |
              ((uint64_t)b[28] << 24) | ((uint64_t)b[27] << 32) | ((uint64_t)b[26] << 40) |
              (((uint64_t)b[25] & 0x0F) << 48);
    r->n[1] = ((uint64_t)b[25] >> 4) | ((uint64_t)b[24] << 4) | ((uint64_t)b[23] << 12) |
              ((uint64_t)b[22] << 20) | ((uint64_t)b[21] << 28) | ((uint64_t)b[20] << 36) |
              ((uint64_t)b[19] << 44);
    r->n[2] = (uint64_t)b[18] | ((uint64_t)b[17] << 8) | ((uint64_t)b[16] << 16) |
              ((uint64_t)b[15] << 24) | ((uint64_t)b[14] << 32) | ((uint64_t)b[13] << 40) |
              (((uint64_t)b[12] & 0x0F) << 48);
    r->n[3] = ((uint64_t)b[12] >> 4) | ((uint64_t)b[11] << 4) | ((uint64_t)b[10] << 12) |
              ((uint64_t)b[9] << 20) | ((uint64_t)b[8] << 28) | ((uint64_t)b[7] << 36) |
              ((uint64_t)b[6] << 44);
    r->n[4] = (uint64_t)b[5] | ((uint64_t)b[4] << 8) | ((uint64_t)b[3] << 16) |
              ((uint64_t)b[2] << 24) | ((uint64_t)b[1] << 32) | ((uint64_t)b[0] << 40);
}

//------------------------------------------------------------------------------
// Normalization / Reduction
//------------------------------------------------------------------------------

// Reduce modulo p using the special form p = 2^256 - 2^32 - 977
// Key insight: 2^256 = 2^32 + 977 (mod p)
// So for overflow bits, multiply by (2^32 + 977) = 0x1000003D1
static inline void field_normalize(field_elem *r) {
    uint64_t t0, t1, t2, t3, t4;
    uint64_t c;

    t0 = r->n[0]; t1 = r->n[1]; t2 = r->n[2]; t3 = r->n[3]; t4 = r->n[4];

    // Reduce bits above 256
    // t4 can have up to 48 bits, need to bring down to 48 bits max for n[4]
    // But after reduction t4 should be < 2^48

    // First pass: propagate carries
    t1 += t0 >> 52; t0 &= FIELD_LIMB_MASK;
    t2 += t1 >> 52; t1 &= FIELD_LIMB_MASK;
    t3 += t2 >> 52; t2 &= FIELD_LIMB_MASK;
    t4 += t3 >> 52; t3 &= FIELD_LIMB_MASK;

    // Now reduce t4 overflow: anything above 2^48 needs reduction
    // 2^256 ≡ 0x1000003D1 (mod p)
    // Limb 4 represents bits 208-259, so overflow at bit 256 = bit 48 of limb 4
    c = t4 >> 48;
    t4 &= 0xFFFFFFFFFFFFULL;  // Keep only 48 bits

    // Add c * 0x1000003D1 to low limbs
    // 0x1000003D1 = 2^32 + 977
    uint64_t d = c * 0x1000003D1ULL;
    t0 += d;

    // Propagate carries again
    t1 += t0 >> 52; t0 &= FIELD_LIMB_MASK;
    t2 += t1 >> 52; t1 &= FIELD_LIMB_MASK;
    t3 += t2 >> 52; t2 &= FIELD_LIMB_MASK;
    t4 += t3 >> 52; t3 &= FIELD_LIMB_MASK;

    // Final reduction if still >= p
    // This is rare but needed for full normalization
    c = t4 >> 48;
    if (c) {
        t4 &= 0xFFFFFFFFFFFFULL;
        d = c * 0x1000003D1ULL;
        t0 += d;
        t1 += t0 >> 52; t0 &= FIELD_LIMB_MASK;
        t2 += t1 >> 52; t1 &= FIELD_LIMB_MASK;
        t3 += t2 >> 52; t2 &= FIELD_LIMB_MASK;
        t4 += t3 >> 52; t3 &= FIELD_LIMB_MASK;
    }

    r->n[0] = t0; r->n[1] = t1; r->n[2] = t2; r->n[3] = t3; r->n[4] = t4;
}

// Weak normalize - just propagate carries, don't fully reduce
static inline void field_normalize_weak(field_elem *r) {
    uint64_t t0, t1, t2, t3, t4;

    t0 = r->n[0]; t1 = r->n[1]; t2 = r->n[2]; t3 = r->n[3]; t4 = r->n[4];

    t1 += t0 >> 52; t0 &= FIELD_LIMB_MASK;
    t2 += t1 >> 52; t1 &= FIELD_LIMB_MASK;
    t3 += t2 >> 52; t2 &= FIELD_LIMB_MASK;
    t4 += t3 >> 52; t3 &= FIELD_LIMB_MASK;

    r->n[0] = t0; r->n[1] = t1; r->n[2] = t2; r->n[3] = t3; r->n[4] = t4;
}

//------------------------------------------------------------------------------
// Addition / Subtraction
//------------------------------------------------------------------------------

static inline void field_add(field_elem *r, const field_elem *a, const field_elem *b) {
    r->n[0] = a->n[0] + b->n[0];
    r->n[1] = a->n[1] + b->n[1];
    r->n[2] = a->n[2] + b->n[2];
    r->n[3] = a->n[3] + b->n[3];
    r->n[4] = a->n[4] + b->n[4];
    // Don't normalize yet - allow magnitude to grow
}

// Subtract with modular reduction guarantee
// Add 2*p to ensure positive result
static inline void field_sub(field_elem *r, const field_elem *a, const field_elem *b) {
    // 2*p in 52-bit limbs (precomputed)
    // p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    // 2*p low bits: 0x1FFFFFFFF85E
    const uint64_t M = FIELD_LIMB_MASK;
    const uint64_t R0 = 0x1FFFFFFFF85EULL; // 2 * (2^32 + 977) for wrap

    r->n[0] = a->n[0] - b->n[0] + (M * 2 + 2) - R0;
    r->n[1] = a->n[1] - b->n[1] + (M * 2 + 2);
    r->n[2] = a->n[2] - b->n[2] + (M * 2 + 2);
    r->n[3] = a->n[3] - b->n[3] + (M * 2 + 2);
    r->n[4] = a->n[4] - b->n[4] + (0xFFFFFFFFFFFFULL * 2);
}

static inline void field_negate(field_elem *r, const field_elem *a) {
    field_elem zero;
    field_clear(&zero);
    field_sub(r, &zero, a);
}

static inline void field_mul_int(field_elem *r, uint64_t a) {
    r->n[0] *= a;
    r->n[1] *= a;
    r->n[2] *= a;
    r->n[3] *= a;
    r->n[4] *= a;
}

//------------------------------------------------------------------------------
// Multiplication - The core optimization
//------------------------------------------------------------------------------

#ifdef _MSC_VER
#include <intrin.h>
#define MULH(a, b) __umulh(a, b)
#define MUL128(a, b, hi) _umul128(a, b, hi)
#else
static inline uint64_t mulh(uint64_t a, uint64_t b) {
    unsigned __int128 r = (unsigned __int128)a * b;
    return (uint64_t)(r >> 64);
}
#define MULH(a, b) mulh(a, b)
static inline uint64_t mul128(uint64_t a, uint64_t b, uint64_t *hi) {
    unsigned __int128 r = (unsigned __int128)a * b;
    *hi = (uint64_t)(r >> 64);
    return (uint64_t)r;
}
#define MUL128(a, b, hi) mul128(a, b, hi)
#endif

// Optimized multiplication for secp256k1
// Uses the fact that 52*52 = 104 bits fits in 128-bit intermediate
static inline void field_mul(field_elem *r, const field_elem *a, const field_elem *b) {
    // 128-bit accumulators for intermediate products
    // We accumulate into pairs (high, low)
    uint64_t c0, c1, c2, c3, c4;
    uint64_t d0, d1, d2, d3, d4, d5, d6, d7, d8;
    uint64_t t;
    uint64_t hi;

    const uint64_t M = FIELD_LIMB_MASK;
    const uint64_t R = 0x1000003D1ULL;  // Reduction constant

    // Schoolbook multiplication with delayed reduction
    // Product terms: a[i] * b[j] contributes to result limb (i+j)

    // d0 = a0*b0
    d0 = MUL128(a->n[0], b->n[0], &hi);
    d1 = hi;

    // d1 += a0*b1 + a1*b0
    d1 += MUL128(a->n[0], b->n[1], &hi); d2 = hi;
    d1 += MUL128(a->n[1], b->n[0], &hi); d2 += hi;

    // d2 += a0*b2 + a1*b1 + a2*b0
    d2 += MUL128(a->n[0], b->n[2], &hi); d3 = hi;
    d2 += MUL128(a->n[1], b->n[1], &hi); d3 += hi;
    d2 += MUL128(a->n[2], b->n[0], &hi); d3 += hi;

    // d3 += a0*b3 + a1*b2 + a2*b1 + a3*b0
    d3 += MUL128(a->n[0], b->n[3], &hi); d4 = hi;
    d3 += MUL128(a->n[1], b->n[2], &hi); d4 += hi;
    d3 += MUL128(a->n[2], b->n[1], &hi); d4 += hi;
    d3 += MUL128(a->n[3], b->n[0], &hi); d4 += hi;

    // d4 += a0*b4 + a1*b3 + a2*b2 + a3*b1 + a4*b0
    d4 += MUL128(a->n[0], b->n[4], &hi); d5 = hi;
    d4 += MUL128(a->n[1], b->n[3], &hi); d5 += hi;
    d4 += MUL128(a->n[2], b->n[2], &hi); d5 += hi;
    d4 += MUL128(a->n[3], b->n[1], &hi); d5 += hi;
    d4 += MUL128(a->n[4], b->n[0], &hi); d5 += hi;

    // d5 += a1*b4 + a2*b3 + a3*b2 + a4*b1
    d5 += MUL128(a->n[1], b->n[4], &hi); d6 = hi;
    d5 += MUL128(a->n[2], b->n[3], &hi); d6 += hi;
    d5 += MUL128(a->n[3], b->n[2], &hi); d6 += hi;
    d5 += MUL128(a->n[4], b->n[1], &hi); d6 += hi;

    // d6 += a2*b4 + a3*b3 + a4*b2
    d6 += MUL128(a->n[2], b->n[4], &hi); d7 = hi;
    d6 += MUL128(a->n[3], b->n[3], &hi); d7 += hi;
    d6 += MUL128(a->n[4], b->n[2], &hi); d7 += hi;

    // d7 += a3*b4 + a4*b3
    d7 += MUL128(a->n[3], b->n[4], &hi); d8 = hi;
    d7 += MUL128(a->n[4], b->n[3], &hi); d8 += hi;

    // d8 += a4*b4
    d8 += MUL128(a->n[4], b->n[4], &hi);
    // hi should be 0 for valid inputs

    // Now reduce: terms d5-d8 represent bits 260-519
    // These need to be multiplied by R = 0x1000003D1 and added to d0-d3

    // Reduce d5-d8 into d0-d4
    // d5 * R -> d0, d1
    t = MUL128(d5, R, &hi);
    d0 += t;
    d1 += hi;

    // d6 * R -> d1, d2
    t = MUL128(d6, R, &hi);
    d1 += t;
    d2 += hi;

    // d7 * R -> d2, d3
    t = MUL128(d7, R, &hi);
    d2 += t;
    d3 += hi;

    // d8 * R -> d3, d4
    t = MUL128(d8, R, &hi);
    d3 += t;
    d4 += hi;

    // Extract 52-bit limbs with carry propagation
    c0 = d0 & M; d1 += d0 >> 52;
    c1 = d1 & M; d2 += d1 >> 52;
    c2 = d2 & M; d3 += d2 >> 52;
    c3 = d3 & M; d4 += d3 >> 52;
    c4 = d4;

    // Final reduction of overflow in c4
    t = c4 >> 48;
    c4 &= 0xFFFFFFFFFFFFULL;
    t *= R;
    c0 += t;

    // Propagate final carries
    c1 += c0 >> 52; c0 &= M;
    c2 += c1 >> 52; c1 &= M;
    c3 += c2 >> 52; c2 &= M;
    c4 += c3 >> 52; c3 &= M;

    r->n[0] = c0; r->n[1] = c1; r->n[2] = c2; r->n[3] = c3; r->n[4] = c4;
}

// Optimized squaring (saves some multiplications due to symmetry)
static inline void field_sqr(field_elem *r, const field_elem *a) {
    uint64_t c0, c1, c2, c3, c4;
    uint64_t d0, d1, d2, d3, d4, d5, d6, d7, d8;
    uint64_t t;
    uint64_t hi;

    const uint64_t M = FIELD_LIMB_MASK;
    const uint64_t R = 0x1000003D1ULL;

    // Squaring: exploit symmetry a[i]*a[j] = a[j]*a[i]
    // Diagonal terms: a[i]^2
    // Off-diagonal: 2*a[i]*a[j] for i < j

    // d0 = a0^2
    d0 = MUL128(a->n[0], a->n[0], &hi);
    d1 = hi;

    // d1 += 2*a0*a1
    t = MUL128(a->n[0], a->n[1], &hi);
    d1 += t * 2; d2 = hi * 2 + (t >> 63);  // Handle overflow from doubling

    // d2 += 2*a0*a2 + a1^2
    t = MUL128(a->n[0], a->n[2], &hi);
    d2 += t * 2; d3 = hi * 2 + (t >> 63);
    d2 += MUL128(a->n[1], a->n[1], &hi); d3 += hi;

    // d3 += 2*a0*a3 + 2*a1*a2
    t = MUL128(a->n[0], a->n[3], &hi);
    d3 += t * 2; d4 = hi * 2 + (t >> 63);
    t = MUL128(a->n[1], a->n[2], &hi);
    d3 += t * 2; d4 += hi * 2 + (t >> 63);

    // d4 += 2*a0*a4 + 2*a1*a3 + a2^2
    t = MUL128(a->n[0], a->n[4], &hi);
    d4 += t * 2; d5 = hi * 2 + (t >> 63);
    t = MUL128(a->n[1], a->n[3], &hi);
    d4 += t * 2; d5 += hi * 2 + (t >> 63);
    d4 += MUL128(a->n[2], a->n[2], &hi); d5 += hi;

    // d5 += 2*a1*a4 + 2*a2*a3
    t = MUL128(a->n[1], a->n[4], &hi);
    d5 += t * 2; d6 = hi * 2 + (t >> 63);
    t = MUL128(a->n[2], a->n[3], &hi);
    d5 += t * 2; d6 += hi * 2 + (t >> 63);

    // d6 += 2*a2*a4 + a3^2
    t = MUL128(a->n[2], a->n[4], &hi);
    d6 += t * 2; d7 = hi * 2 + (t >> 63);
    d6 += MUL128(a->n[3], a->n[3], &hi); d7 += hi;

    // d7 += 2*a3*a4
    t = MUL128(a->n[3], a->n[4], &hi);
    d7 += t * 2; d8 = hi * 2 + (t >> 63);

    // d8 += a4^2
    d8 += MUL128(a->n[4], a->n[4], &hi);

    // Reduction (same as multiplication)
    t = MUL128(d5, R, &hi); d0 += t; d1 += hi;
    t = MUL128(d6, R, &hi); d1 += t; d2 += hi;
    t = MUL128(d7, R, &hi); d2 += t; d3 += hi;
    t = MUL128(d8, R, &hi); d3 += t; d4 += hi;

    c0 = d0 & M; d1 += d0 >> 52;
    c1 = d1 & M; d2 += d1 >> 52;
    c2 = d2 & M; d3 += d2 >> 52;
    c3 = d3 & M; d4 += d3 >> 52;
    c4 = d4;

    t = c4 >> 48;
    c4 &= 0xFFFFFFFFFFFFULL;
    t *= R;
    c0 += t;

    c1 += c0 >> 52; c0 &= M;
    c2 += c1 >> 52; c1 &= M;
    c3 += c2 >> 52; c2 &= M;
    c4 += c3 >> 52; c3 &= M;

    r->n[0] = c0; r->n[1] = c1; r->n[2] = c2; r->n[3] = c3; r->n[4] = c4;
}

//------------------------------------------------------------------------------
// Inversion using Fermat's little theorem: a^(-1) = a^(p-2) mod p
// For performance-critical code, use batch inversion instead
//------------------------------------------------------------------------------

static inline void field_inv(field_elem *r, const field_elem *a) {
    // p-2 for secp256k1
    // Use addition chain optimized for p-2
    field_elem x2, x3, x6, x9, x11, x22, x44, x88, x176, x220, x223, t;

    field_sqr(&x2, a);
    field_mul(&x2, &x2, a);          // x2 = a^3

    field_sqr(&x3, &x2);
    field_mul(&x3, &x3, a);          // x3 = a^7

    field_sqr(&x6, &x3);
    field_sqr(&x6, &x6);
    field_sqr(&x6, &x6);
    field_mul(&x6, &x6, &x3);        // x6 = a^63

    field_sqr(&x9, &x6);
    field_sqr(&x9, &x9);
    field_sqr(&x9, &x9);
    field_mul(&x9, &x9, &x3);        // x9

    field_sqr(&x11, &x9);
    field_sqr(&x11, &x11);
    field_mul(&x11, &x11, &x2);      // x11

    field_sqr(&x22, &x11);
    for (int i = 0; i < 10; i++) field_sqr(&x22, &x22);
    field_mul(&x22, &x22, &x11);     // x22

    field_sqr(&x44, &x22);
    for (int i = 0; i < 21; i++) field_sqr(&x44, &x44);
    field_mul(&x44, &x44, &x22);     // x44

    field_sqr(&x88, &x44);
    for (int i = 0; i < 43; i++) field_sqr(&x88, &x88);
    field_mul(&x88, &x88, &x44);     // x88

    field_sqr(&x176, &x88);
    for (int i = 0; i < 87; i++) field_sqr(&x176, &x176);
    field_mul(&x176, &x176, &x88);   // x176

    field_sqr(&x220, &x176);
    for (int i = 0; i < 43; i++) field_sqr(&x220, &x220);
    field_mul(&x220, &x220, &x44);   // x220

    field_sqr(&x223, &x220);
    field_sqr(&x223, &x223);
    field_sqr(&x223, &x223);
    field_mul(&x223, &x223, &x3);    // x223

    // Final steps
    memcpy(&t, &x223, sizeof(field_elem));
    for (int i = 0; i < 23; i++) field_sqr(&t, &t);
    field_mul(&t, &t, &x22);
    for (int i = 0; i < 6; i++) field_sqr(&t, &t);
    field_mul(&t, &t, &x2);
    field_sqr(&t, &t);
    field_sqr(&t, &t);
    field_mul(r, &t, a);

    field_normalize(r);
}

//------------------------------------------------------------------------------
// Comparison
//------------------------------------------------------------------------------

static inline int field_is_zero(const field_elem *a) {
    field_elem t;
    memcpy(&t, a, sizeof(field_elem));
    field_normalize(&t);
    return (t.n[0] | t.n[1] | t.n[2] | t.n[3] | t.n[4]) == 0;
}

static inline int field_is_odd(const field_elem *a) {
    field_elem t;
    memcpy(&t, a, sizeof(field_elem));
    field_normalize(&t);
    return t.n[0] & 1;
}

static inline int field_equal(const field_elem *a, const field_elem *b) {
    field_elem t;
    field_sub(&t, a, b);
    return field_is_zero(&t);
}

#endif // FIELD52_H
