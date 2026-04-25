/*
 * ripemd160.c — RIPEMD-160 implementation
 *
 * See ripemd160.h for the public API and test vectors.
 *
 * Design notes:
 *   - The function table, shift table, and message-word permutation table are
 *     kept separate for each of the two parallel lines. All are indexed by the
 *     full step number j in [0, 80).
 *   - The round function is selected by round = j / 16. The left line uses
 *     f1..f5 for rounds 0..4; the right line uses f5..f1 for rounds 0..4.
 *   - The K (additive) constants are stored in each line's own round order,
 *     so both K1[round] and K2[round] are direct lookups.
 */

#include "ripemd160.h"
#include <string.h>
#include <stdlib.h>

static inline uint32_t rol32(uint32_t x, int n) {
    return (x << n) | (x >> (32 - n));
}

/* Message-word permutations: r1 for the left line, r2 for the right line. */
static const int r1[80] = {
     0, 1, 2, 3, 4, 5, 6, 7, 8, 9,10,11,12,13,14,15,
     7, 4,13, 1,10, 6,15, 3,12, 0, 9, 5, 2,14,11, 8,
     3,10,14, 4, 9,15, 8, 1, 2, 7, 0, 6,13,11, 5,12,
     1, 9,11,10, 0, 8,12, 4,13, 3, 7,15,14, 5, 6, 2,
     4, 0, 5, 9, 7,12, 2,10,14, 1, 3, 8,11, 6,15,13
};
static const int r2[80] = {
     5,14, 7, 0, 9, 2,11, 4,13, 6,15, 8, 1,10, 3,12,
     6,11, 3, 7, 0,13, 5,10,14,15, 8,12, 4, 9, 1, 2,
    15, 5, 1, 3, 7,14, 6, 9,11, 8,12, 2,10, 0, 4,13,
     8, 6, 4, 1, 3,11,15, 0, 5,12, 2,13, 9, 7,10,14,
    12,15,10, 4, 1, 5, 8, 7, 6, 2,13,14, 0, 3, 9,11
};

/* Per-step rotation amounts. */
static const int s1[80] = {
    11,14,15,12, 5, 8, 7, 9,11,13,14,15, 6, 7, 9, 8,
     7, 6, 8,13,11, 9, 7,15, 7,12,15, 9,11, 7,13,12,
    11,13, 6, 7,14, 9,13,15,14, 8,13, 6, 5,12, 7, 5,
    11,12,14,15,14,15, 9, 8, 9,14, 5, 6, 8, 6, 5,12,
     9,15, 5,11, 6, 8,13,12, 5,12,13,14,11, 8, 5, 6
};
static const int s2[80] = {
     8, 9, 9,11,13,15,15, 5, 7, 7, 8,11,14,14,12, 6,
     9,13,15, 7,12, 8, 9,11, 7, 7,12, 7, 6,15,13,11,
     9, 7,15,11, 8, 6, 6,14,12,13, 5,14,13,13, 7, 5,
    15, 5, 8,11,14,14, 6,14, 6, 9,12, 9,12, 5,15, 8,
     8, 5,12, 9,12, 5,14, 6, 8,13, 6, 5,15,13,11,11
};

/* Additive constants, stored in each line's own round order. */
static const uint32_t K1[5] = {
    0x00000000u, 0x5A827999u, 0x6ED9EBA1u, 0x8F1BBCDCu, 0xA953FD4Eu
};
static const uint32_t K2[5] = {
    0x50A28BE6u, 0x5C4DD124u, 0x6D703EF3u, 0x7A6D76E9u, 0x00000000u
};

void ripemd160(const uint8_t *data, size_t len, uint8_t out[20]) {
    /* Initial chaining values. */
    uint32_t h[5] = {
        0x67452301u, 0xEFCDAB89u, 0x98BADCFEu, 0x10325476u, 0xC3D2E1F0u
    };

    /* Pad: 0x80 terminator, then zeros, then 8-byte little-endian bit length.
     * Padded length is the smallest multiple of 64 that is >= len + 9. */
    size_t padded_len = ((len + 9 + 63) / 64) * 64;
    uint8_t *msg = (uint8_t *)calloc(padded_len, 1);
    if (!msg) return;  /* out remains uninitialized on allocation failure */

    memcpy(msg, data, len);
    msg[len] = 0x80;
    uint64_t bits = (uint64_t)len * 8;
    for (int i = 0; i < 8; i++) {
        msg[padded_len - 8 + i] = (uint8_t)(bits >> (8 * i));
    }

    for (size_t blk = 0; blk < padded_len; blk += 64) {
        /* Load the 512-bit block as sixteen 32-bit little-endian words. */
        uint32_t X[16];
        for (int i = 0; i < 16; i++) {
            X[i] =  (uint32_t)msg[blk + i*4]
                 | ((uint32_t)msg[blk + i*4 + 1] << 8)
                 | ((uint32_t)msg[blk + i*4 + 2] << 16)
                 | ((uint32_t)msg[blk + i*4 + 3] << 24);
        }

        uint32_t A  = h[0], B  = h[1], C  = h[2], D  = h[3], E  = h[4];
        uint32_t Ap = h[0], Bp = h[1], Cp = h[2], Dp = h[3], Ep = h[4];

        for (int j = 0; j < 80; j++) {
            int round = j / 16;
            uint32_t f, fp;

            /* Left line: f1, f2, f3, f4, f5 for rounds 0..4.
             * Right line: f5, f4, f3, f2, f1 for rounds 0..4. */
            switch (round) {
                case 0:
                    f  = B ^ C ^ D;                        /* f1 */
                    fp = Bp ^ (Cp | ~Dp);                  /* f5 */
                    break;
                case 1:
                    f  = (B & C) | (~B & D);               /* f2 */
                    fp = (Bp & Dp) | (Cp & ~Dp);           /* f4 */
                    break;
                case 2:
                    f  = (B | ~C) ^ D;                     /* f3 */
                    fp = (Bp | ~Cp) ^ Dp;                  /* f3 */
                    break;
                case 3:
                    f  = (B & D) | (C & ~D);               /* f4 */
                    fp = (Bp & Cp) | (~Bp & Dp);           /* f2 */
                    break;
                default:
                    f  = B ^ (C | ~D);                     /* f5 */
                    fp = Bp ^ Cp ^ Dp;                     /* f1 */
                    break;
            }

            /* Left-line step. */
            uint32_t T = rol32(A + f + X[r1[j]] + K1[round], s1[j]) + E;
            A = E; E = D; D = rol32(C, 10); C = B; B = T;

            /* Right-line step. */
            uint32_t Tp = rol32(Ap + fp + X[r2[j]] + K2[round], s2[j]) + Ep;
            Ap = Ep; Ep = Dp; Dp = rol32(Cp, 10); Cp = Bp; Bp = Tp;
        }

        /* Combine the two parallel lines into the new chaining value. */
        uint32_t T = h[1] + C  + Dp;
        h[1]       = h[2] + D  + Ep;
        h[2]       = h[3] + E  + Ap;
        h[3]       = h[4] + A  + Bp;
        h[4]       = h[0] + B  + Cp;
        h[0]       = T;
    }

    free(msg);

    /* Output is the chaining state as 20 little-endian bytes. */
    for (int i = 0; i < 5; i++) {
        out[i*4 + 0] = (uint8_t)(h[i]);
        out[i*4 + 1] = (uint8_t)(h[i] >> 8);
        out[i*4 + 2] = (uint8_t)(h[i] >> 16);
        out[i*4 + 3] = (uint8_t)(h[i] >> 24);
    }
}
