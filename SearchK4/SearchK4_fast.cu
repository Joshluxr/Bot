/*
 * SearchK4.cu - Direct vanity address search with sequential keyspace support
 * Uses proper GPU Base58 encoding and string matching
 * Based on VanitySearch by Jean Luc PONS and BloomSearch32K3 sequential logic
 *
 * Features:
 * - Sequential keyspace search from specified start point
 * - Supports both decimal and hex start values
 * - Full private key reconstruction on match
 * - Resume from state files
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <time.h>
#include <signal.h>
#include <sys/stat.h>

#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"
#include "CPUGroup.h"

#define NB_THREAD_PER_GROUP 64
#define MAX_FOUND 65536
#define STEP_SIZE 1024
#define K4_MAX_PATTERNS 256
#define P2PKH 0

// Base58 alphabet
__device__ __constant__ char pszBase58[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// Pattern storage - each pattern is null-terminated, max 35 chars
__device__ __constant__ char d_patterns[K4_MAX_PATTERNS][36];
__device__ __constant__ int d_pattern_lens[K4_MAX_PATTERNS];
__device__ __constant__ int d_num_patterns;

// Sequential mode delta: (nbThread * STEP_SIZE) * G
// This is computed at runtime and copied to device memory
// Used to advance all threads by the correct amount for non-overlapping ranges
__device__ __constant__ uint64_t d_seqDeltaX[4];
__device__ __constant__ uint64_t d_seqDeltaY[4];
__device__ __constant__ int d_useSeqDelta;  // 0 = use _2Gn, 1 = use sequential delta

volatile bool running = true;
void sighandler(int s) { running = false; printf("\nStopping...\n"); }

// =====================================================================================
// SECP256K1 CPU-SIDE ELLIPTIC CURVE MATH (for key initialization)
// =====================================================================================

static const uint64_t SECP_P[4] = {
    0xFFFFFFFEFFFFFC2FULL, 0xFFFFFFFFFFFFFFFFULL,
    0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFFULL
};

static const uint64_t SECP_N[4] = {  // Group order
    0xBFD25E8CD0364141ULL, 0xBAAEDCE6AF48A03BULL,
    0xFFFFFFFFFFFFFFFEULL, 0xFFFFFFFFFFFFFFFFULL
};

static const uint64_t SECP_GX[4] = {
    0x59F2815B16F81798ULL, 0x029BFCDB2DCE28D9ULL,
    0x55A06295CE870B07ULL, 0x79BE667EF9DCBBACULL
};

static const uint64_t SECP_GY[4] = {
    0x9C47D08FFB10D4B8ULL, 0xFD17B448A6855419ULL,
    0x5DA4FBFC0E1108A8ULL, 0x483ADA7726A3C465ULL
};

// Global base key for private key reconstruction
static uint64_t g_baseKey[4] = {0, 0, 0, 0};
static bool g_sequentialMode = false;
static int g_nbThread = 16384;

// 256-bit comparison
static int cmp256(const uint64_t* a, const uint64_t* b) {
    for (int i = 3; i >= 0; i--) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
}

// 256-bit addition: r = a + b, returns carry
static uint64_t add256(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    __uint128_t c = 0;
    for (int i = 0; i < 4; i++) {
        c += (__uint128_t)a[i] + b[i];
        r[i] = (uint64_t)c;
        c >>= 64;
    }
    return (uint64_t)c;
}

// 256-bit subtraction: r = a - b, returns borrow
static uint64_t sub256(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    __uint128_t c = 0;
    for (int i = 0; i < 4; i++) {
        __uint128_t diff = (__uint128_t)a[i] - b[i] - c;
        r[i] = (uint64_t)diff;
        c = (diff >> 64) ? 1 : 0;
    }
    return c;
}

// Add 64-bit value to 256-bit: r = a + b
static uint64_t add256_scalar(uint64_t* r, const uint64_t* a, uint64_t b) {
    __uint128_t c = b;
    for (int i = 0; i < 4; i++) {
        c += a[i];
        r[i] = (uint64_t)c;
        c >>= 64;
    }
    return (uint64_t)c;
}

// Modular addition: r = (a + b) mod p
static void mod_add(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t c = add256(r, a, b);
    if (c || cmp256(r, SECP_P) >= 0) {
        sub256(r, r, SECP_P);
    }
}

// Modular subtraction: r = (a - b) mod p
static void mod_sub(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t c = sub256(r, a, b);
    if (c) {
        add256(r, r, SECP_P);
    }
}

// Modular multiplication: r = (a * b) mod p
// Fixed modular multiplication for secp256k1
// p = 2^256 - 0x1000003D1
static void mod_mul(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    __uint128_t t[8] = {0};
    for (int i = 0; i < 4; i++) {
        __uint128_t c = 0;
        for (int j = 0; j < 4; j++) {
            c += t[i + j] + (__uint128_t)a[i] * b[j];
            t[i + j] = (uint64_t)c;
            c >>= 64;
        }
        t[i + 4] = c;
    }

    uint64_t low[4] = {(uint64_t)t[0], (uint64_t)t[1], (uint64_t)t[2], (uint64_t)t[3]};
    uint64_t high[4] = {(uint64_t)t[4], (uint64_t)t[5], (uint64_t)t[6], (uint64_t)t[7]};

    uint64_t res[5];
    __uint128_t c = 0;
    
    // First reduction: res = low + high * 0x1000003D1
    for (int i = 0; i < 4; i++) {
        c += (__uint128_t)low[i] + (__uint128_t)high[i] * 0x1000003D1ULL;
        res[i] = (uint64_t)c;
        c >>= 64;
    }
    res[4] = (uint64_t)c;
    
    // Second reduction if needed
    c = 0;
    for (int i = 0; i < 4; i++) {
        c += (__uint128_t)res[i];
        if (i == 0) c += (__uint128_t)res[4] * 0x1000003D1ULL;
        res[i] = (uint64_t)c;
        c >>= 64;
    }
    res[4] = (uint64_t)c;
    
    // Third reduction if there is still carry
    if (res[4]) {
        c = (__uint128_t)res[0] + (__uint128_t)res[4] * 0x1000003D1ULL;
        res[0] = (uint64_t)c;
        c >>= 64;
        for (int i = 1; i < 4 && c; i++) {
            c += res[i];
            res[i] = (uint64_t)c;
            c >>= 64;
        }
    }
    
    for (int i = 0; i < 4; i++) r[i] = res[i];
    
    if (cmp256(r, SECP_P) >= 0) {
        sub256(r, r, SECP_P);
    }
}
// Modular inversion using Fermat's little theorem: a^(-1) = a^(p-2) mod p
static void mod_inv(uint64_t* r, const uint64_t* a) {
    uint64_t exp[4] = {
        0xFFFFFFFEFFFFFC2DULL, 0xFFFFFFFFFFFFFFFFULL,
        0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFFULL
    };

    uint64_t base[4], result[4] = {1, 0, 0, 0};
    memcpy(base, a, 32);

    for (int i = 0; i < 256; i++) {
        if ((exp[i / 64] >> (i % 64)) & 1) {
            mod_mul(result, result, base);
        }
        mod_mul(base, base, base);
    }

    memcpy(r, result, 32);
}

// Check if point is at infinity
static int is_infinity(const uint64_t* x, const uint64_t* y) {
    return (x[0] | x[1] | x[2] | x[3] | y[0] | y[1] | y[2] | y[3]) == 0;
}

// Point addition: R = P + Q
static void point_add(uint64_t* rx, uint64_t* ry,
                      const uint64_t* px, const uint64_t* py,
                      const uint64_t* qx, const uint64_t* qy) {
    if (is_infinity(px, py)) {
        memcpy(rx, qx, 32); memcpy(ry, qy, 32); return;
    }
    if (is_infinity(qx, qy)) {
        memcpy(rx, px, 32); memcpy(ry, py, 32); return;
    }

    uint64_t s[4], dx[4], dy[4], s2[4], tmp[4];

    mod_sub(dx, qx, px);

    if ((dx[0] | dx[1] | dx[2] | dx[3]) == 0) {
        mod_sub(dy, qy, py);
        if ((dy[0] | dy[1] | dy[2] | dy[3]) == 0) {
            // P == Q, use point doubling formula
            mod_mul(s, px, px);
            mod_add(tmp, s, s);
            mod_add(s, tmp, s);  // s = 3*x^2
            mod_add(dy, py, py);
            mod_inv(tmp, dy);
            mod_mul(s, s, tmp);  // s = 3*x^2 / (2*y)
        } else {
            // P == -Q, result is infinity
            memset(rx, 0, 32); memset(ry, 0, 32); return;
        }
    } else {
        mod_sub(dy, qy, py);
        mod_inv(tmp, dx);
        mod_mul(s, dy, tmp);  // s = (qy - py) / (qx - px)
    }

    mod_mul(s2, s, s);
    mod_sub(rx, s2, px);
    mod_sub(rx, rx, qx);

    mod_sub(tmp, px, rx);
    mod_mul(ry, s, tmp);
    mod_sub(ry, ry, py);
}

// Point doubling: R = 2*P
static void point_double(uint64_t* rx, uint64_t* ry,
                         const uint64_t* px, const uint64_t* py) {
    if (is_infinity(px, py) || (py[0] | py[1] | py[2] | py[3]) == 0) {
        memset(rx, 0, 32); memset(ry, 0, 32); return;
    }

    uint64_t s[4], s2[4], tmp[4], dy[4];

    mod_mul(s, px, px);
    mod_add(tmp, s, s);
    mod_add(s, tmp, s);  // s = 3*x^2
    mod_add(dy, py, py);
    mod_inv(tmp, dy);
    mod_mul(s, s, tmp);  // s = 3*x^2 / (2*y)

    mod_mul(s2, s, s);
    mod_sub(rx, s2, px);
    mod_sub(rx, rx, px);

    mod_sub(tmp, px, rx);
    mod_mul(ry, s, tmp);
    mod_sub(ry, ry, py);
}

// Scalar multiplication: R = k * G
// =====================================================================================
// JACOBIAN COORDINATE ELLIPTIC CURVE OPERATIONS (faster - only 1 mod_inv at the end)
// =====================================================================================

// Jacobian point doubling: R = 2*P
// Cost: 4M + 4S (no division\!)
static void jacobian_double(uint64_t* x3, uint64_t* y3, uint64_t* z3,
                            const uint64_t* x1, const uint64_t* y1, const uint64_t* z1) {
    if ((z1[0] | z1[1] | z1[2] | z1[3]) == 0) {
        memset(x3, 0, 32); memset(y3, 0, 32); memset(z3, 0, 32);
        return;
    }
    
    uint64_t s[4], m[4], t[4], tmp[4], y1sq[4];
    
    mod_mul(y1sq, y1, y1);       // y1sq = Y1^2
    mod_mul(s, y1sq, x1);        // s = X1*Y1^2
    mod_add(s, s, s);            // s = 2*X1*Y1^2
    mod_add(s, s, s);            // s = 4*X1*Y1^2 (this is S)
    
    mod_mul(m, x1, x1);          // m = X1^2
    mod_add(tmp, m, m);          // tmp = 2*X1^2
    mod_add(m, tmp, m);          // m = 3*X1^2 (this is M, since a=0 for secp256k1)
    
    mod_mul(x3, m, m);           // x3 = M^2
    mod_add(tmp, s, s);          // tmp = 2*S
    mod_sub(x3, x3, tmp);        // x3 = M^2 - 2*S
    
    mod_sub(tmp, s, x3);         // tmp = S - X3
    mod_mul(y3, m, tmp);         // y3 = M*(S - X3)
    mod_mul(tmp, y1sq, y1sq);    // tmp = Y1^4
    mod_add(tmp, tmp, tmp);      // tmp = 2*Y1^4
    mod_add(tmp, tmp, tmp);      // tmp = 4*Y1^4
    mod_add(tmp, tmp, tmp);      // tmp = 8*Y1^4
    mod_sub(y3, y3, tmp);        // y3 = M*(S - X3) - 8*Y1^4
    
    mod_mul(z3, y1, z1);         // z3 = Y1*Z1
    mod_add(z3, z3, z3);         // z3 = 2*Y1*Z1
}

// Jacobian mixed addition: R = P(Jacobian) + Q(Affine)
// Cost: 8M + 3S (no division\!)
static void jacobian_add_affine(uint64_t* x3, uint64_t* y3, uint64_t* z3,
                                const uint64_t* x1, const uint64_t* y1, const uint64_t* z1,
                                const uint64_t* x2, const uint64_t* y2) {
    if ((z1[0] | z1[1] | z1[2] | z1[3]) == 0) {
        memcpy(x3, x2, 32); memcpy(y3, y2, 32);
        uint64_t one[4] = {1, 0, 0, 0};
        memcpy(z3, one, 32);
        return;
    }
    
    uint64_t z1z1[4], u2[4], s2[4], h[4], hh[4], i[4], j[4], r[4], v[4], tmp[4];
    
    mod_mul(z1z1, z1, z1);       // Z1Z1 = Z1^2
    mod_mul(u2, x2, z1z1);       // U2 = X2*Z1Z1
    mod_mul(s2, z1, z1z1);       // s2 = Z1^3
    mod_mul(s2, s2, y2);         // S2 = Y2*Z1^3
    
    mod_sub(h, u2, x1);          // H = U2 - X1
    
    if ((h[0] | h[1] | h[2] | h[3]) == 0) {
        mod_sub(tmp, s2, y1);
        if ((tmp[0] | tmp[1] | tmp[2] | tmp[3]) == 0) {
            jacobian_double(x3, y3, z3, x1, y1, z1);
            return;
        } else {
            memset(x3, 0, 32); memset(y3, 0, 32); memset(z3, 0, 32);
            return;
        }
    }
    
    mod_add(i, h, h);            // i = 2*H
    mod_mul(i, i, i);            // I = (2*H)^2
    mod_mul(j, h, i);            // J = H*I
    mod_sub(r, s2, y1);          // r = S2 - Y1
    mod_add(r, r, r);            // r = 2*(S2 - Y1)
    mod_mul(v, x1, i);           // V = X1*I
    
    mod_mul(x3, r, r);           // x3 = r^2
    mod_sub(x3, x3, j);          // x3 = r^2 - J
    mod_add(tmp, v, v);          // tmp = 2*V
    mod_sub(x3, x3, tmp);        // X3 = r^2 - J - 2*V
    
    mod_sub(tmp, v, x3);         // tmp = V - X3
    mod_mul(y3, r, tmp);         // y3 = r*(V - X3)
    mod_mul(tmp, y1, j);         // tmp = Y1*J
    mod_add(tmp, tmp, tmp);      // tmp = 2*Y1*J
    mod_sub(y3, y3, tmp);        // Y3 = r*(V - X3) - 2*Y1*J
    
    mod_mul(z3, z1, h);          // z3 = Z1*H
    mod_add(z3, z3, z3);         // Z3 = 2*Z1*H
}

// Convert Jacobian to Affine (single mod_inv\!)
static void jacobian_to_affine(uint64_t* ax, uint64_t* ay,
                               const uint64_t* jx, const uint64_t* jy, const uint64_t* jz) {
    if ((jz[0] | jz[1] | jz[2] | jz[3]) == 0) {
        memset(ax, 0, 32); memset(ay, 0, 32);
        return;
    }
    uint64_t zinv[4], zinv2[4], zinv3[4];
    mod_inv(zinv, jz);
    mod_mul(zinv2, zinv, zinv);
    mod_mul(zinv3, zinv2, zinv);
    mod_mul(ax, jx, zinv2);
    mod_mul(ay, jy, zinv3);
}

// Fast scalar multiplication using Jacobian coordinates
// Only 1 mod_inv at the very end\!
static void scalar_mult_G(uint64_t* rx, uint64_t* ry, const uint64_t* k) {
    uint64_t jx[4] = {0}, jy[4] = {0}, jz[4] = {0};
    uint64_t tmpx[4], tmpy[4], tmpz[4];
    
    // Process from MSB to LSB (double-and-add)
    for (int i = 255; i >= 0; i--) {
        jacobian_double(tmpx, tmpy, tmpz, jx, jy, jz);
        memcpy(jx, tmpx, 32); memcpy(jy, tmpy, 32); memcpy(jz, tmpz, 32);
        
        if ((k[i / 64] >> (i % 64)) & 1) {
            jacobian_add_affine(tmpx, tmpy, tmpz, jx, jy, jz, SECP_GX, SECP_GY);
            memcpy(jx, tmpx, 32); memcpy(jy, tmpy, 32); memcpy(jz, tmpz, 32);
        }
    }
    
    jacobian_to_affine(rx, ry, jx, jy, jz);
}


// =====================================================================================
// KEY PARSING FUNCTIONS
// =====================================================================================

// Convert decimal string to 256-bit integer
static void decimal_to_256bit(const char* decimal, uint64_t* result) {
    memset(result, 0, 32);

    // Skip any commas/underscores in the input (user-friendly format)
    char clean[256];
    int j = 0;
    for (int i = 0; decimal[i] && j < 255; i++) {
        if (decimal[i] >= '0' && decimal[i] <= '9') {
            clean[j++] = decimal[i];
        }
    }
    clean[j] = '\0';

    // Process each digit: result = result * 10 + digit
    for (int i = 0; clean[i]; i++) {
        // Multiply by 10
        __uint128_t carry = 0;
        for (int k = 0; k < 4; k++) {
            __uint128_t prod = (__uint128_t)result[k] * 10 + carry;
            result[k] = (uint64_t)prod;
            carry = prod >> 64;
        }

        // Add digit
        int digit = clean[i] - '0';
        carry = digit;
        for (int k = 0; k < 4 && carry; k++) {
            __uint128_t sum = (__uint128_t)result[k] + carry;
            result[k] = (uint64_t)sum;
            carry = sum >> 64;
        }
    }
}

// Convert hex string to 256-bit integer
static void hex_to_256bit(const char* hex, uint64_t* result) {
    memset(result, 0, 32);

    // Skip 0x prefix
    if (hex[0] == '0' && (hex[1] == 'x' || hex[1] == 'X')) {
        hex += 2;
    }

    int len = strlen(hex);
    uint8_t* bytes = (uint8_t*)result;

    // Parse from right to left (little-endian)
    for (int i = 0; i < len && i < 64; i++) {
        char c = hex[len - 1 - i];
        int val;
        if (c >= '0' && c <= '9') val = c - '0';
        else if (c >= 'a' && c <= 'f') val = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') val = c - 'A' + 10;
        else continue;

        int byteIdx = i / 2;
        if (i % 2 == 0) {
            bytes[byteIdx] = val;
        } else {
            bytes[byteIdx] |= val << 4;
        }
    }
}

// Format 256-bit as hex string
static void format_256bit_hex(const uint64_t* val, char* out) {
    sprintf(out, "%016lx%016lx%016lx%016lx", val[3], val[2], val[1], val[0]);
}

// =====================================================================================
// GPU KERNEL CODE
// =====================================================================================

// GPU Base58 address generation (from VanitySearch)
__device__ __noinline__ void _GetAddress(int type, uint32_t *hash, char *b58Add) {
    uint32_t addBytes[16];
    uint32_t s[16];
    unsigned char A[25];
    unsigned char *addPtr = A;
    int retPos = 0;
    unsigned char digits[128];

    A[0] = (type == P2PKH) ? 0x00 : 0x05;
    memcpy(A + 1, (char *)hash, 20);

    addBytes[0] = __byte_perm(hash[0], (uint32_t)A[0], 0x4012);
    addBytes[1] = __byte_perm(hash[0], hash[1], 0x3456);
    addBytes[2] = __byte_perm(hash[1], hash[2], 0x3456);
    addBytes[3] = __byte_perm(hash[2], hash[3], 0x3456);
    addBytes[4] = __byte_perm(hash[3], hash[4], 0x3456);
    addBytes[5] = __byte_perm(hash[4], 0x80, 0x3456);
    addBytes[6] = 0; addBytes[7] = 0; addBytes[8] = 0; addBytes[9] = 0;
    addBytes[10] = 0; addBytes[11] = 0; addBytes[12] = 0; addBytes[13] = 0;
    addBytes[14] = 0; addBytes[15] = 0xA8;

    SHA256Initialize(s);
    SHA256Transform(s, addBytes);

    #pragma unroll 8
    for (int i = 0; i < 8; i++) addBytes[i] = s[i];

    addBytes[8] = 0x80000000; addBytes[9] = 0; addBytes[10] = 0; addBytes[11] = 0;
    addBytes[12] = 0; addBytes[13] = 0; addBytes[14] = 0; addBytes[15] = 0x100;

    SHA256Initialize(s);
    SHA256Transform(s, addBytes);

    A[21] = ((uint8_t *)s)[3];
    A[22] = ((uint8_t *)s)[2];
    A[23] = ((uint8_t *)s)[1];
    A[24] = ((uint8_t *)s)[0];

    while (addPtr[0] == 0) {
        b58Add[retPos++] = '1';
        addPtr++;
    }
    int length = 25 - retPos;

    int digitslen = 1;
    digits[0] = 0;
    for (int i = 0; i < length; i++) {
        uint32_t carry = addPtr[i];
        for (int j = 0; j < digitslen; j++) {
            carry += (uint32_t)(digits[j]) << 8;
            digits[j] = (unsigned char)(carry % 58);
            carry /= 58;
        }
        while (carry > 0) {
            digits[digitslen++] = (unsigned char)(carry % 58);
            carry /= 58;
        }
    }

    for (int i = 0; i < digitslen; i++)
        b58Add[retPos++] = pszBase58[digits[digitslen - 1 - i]];

    b58Add[retPos] = 0;
}

__device__ __noinline__ bool _MatchPrefix(const char *addr, const char *pattern, int patLen) {
    for (int i = 0; i < patLen; i++) {
        if (addr[i] != pattern[i]) return false;
    }
    return true;
}

__device__ bool CheckVanityPatternsK4(uint32_t *h, int *matched_idx, char *gen_addr) {
    _GetAddress(P2PKH, h, gen_addr);
    for (int i = 0; i < d_num_patterns; i++) {
        if (_MatchPrefix(gen_addr, d_patterns[i], d_pattern_lens[i])) {
            *matched_idx = i;
            return true;
        }
    }
    *matched_idx = -1;
    return false;
}

__device__ void OutputMatchK4(uint32_t* out, uint32_t tid, int32_t incr, uint32_t* h, int pattern_idx, uint8_t isOdd) {
    uint32_t pos = atomicAdd(out, 1);
    if (pos < MAX_FOUND) {
        uint32_t* entry = out + 1 + pos * 8;
        entry[0] = tid;          // Thread ID for key reconstruction
        entry[1] = (uint32_t)incr;
        entry[2] = (pattern_idx << 8) | isOdd;
        entry[3] = h[0];
        entry[4] = h[1];
        entry[5] = h[2];
        entry[6] = h[3];
        entry[7] = h[4];
    }
}

__device__ __noinline__ void CheckHashCompSymK4(
    uint64_t* px, uint64_t* py, uint32_t tid, int32_t incr,
    uint32_t maxFound, uint32_t* out
) {
    uint32_t h1[5], h2[5], h_uncomp[5];
    char addr[40];
    int matched_idx;

    // Check compressed addresses (even and odd Y parity)
    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);

    if (CheckVanityPatternsK4(h1, &matched_idx, addr)) {
        OutputMatchK4(out, tid, incr, h1, matched_idx, 0);
    }

    if (CheckVanityPatternsK4(h2, &matched_idx, addr)) {
        OutputMatchK4(out, tid, -incr, h2, matched_idx, 1);
    }

    // Check uncompressed address (uses both X and Y)
    _GetHash160(px, py, (uint8_t*)h_uncomp);

    if (CheckVanityPatternsK4(h_uncomp, &matched_idx, addr)) {
        // Use parity=2 to indicate uncompressed
        OutputMatchK4(out, tid, incr, h_uncomp, matched_idx, 2);
    }
}

__device__ void ComputeKeysK4(
    uint32_t mode, uint64_t* startx, uint64_t* starty,
    uint32_t maxFound, uint32_t* out
) {
    uint64_t dx[GRP_SIZE/2+1][4];
    uint64_t px[4], py[4], pyn[4], sx[4], sy[4], dy[4], _s[4], _p2[4];

    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;

    __syncthreads();
    Load256A(sx, startx);
    Load256A(sy, starty);
    Load256(px, sx);
    Load256(py, sy);

    for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {
        uint32_t i;
        for (i = 0; i < HSIZE; i++)
            ModSub256(dx[i], Gx[i], sx);
        ModSub256(dx[i], Gx[i], sx);
        ModSub256(dx[i+1], _2Gnx, sx);

        _ModInvGrouped(dx);

        CheckHashCompSymK4(px, py, tid, j*GRP_SIZE + GRP_SIZE/2, maxFound, out);

        ModNeg256(pyn, py);

        for (i = 0; i < HSIZE; i++) {
            Load256(px, sx);
            Load256(py, sy);
            ModSub256(dy, Gy[i], py);
            _ModMult(_s, dy, dx[i]);
            _ModSqr(_p2, _s);
            ModSub256(px, _p2, px);
            ModSub256(px, Gx[i]);
            ModSub256(py, Gx[i], px);
            _ModMult(py, _s);
            ModSub256(py, Gy[i]);

            CheckHashCompSymK4(px, py, tid, j*GRP_SIZE + GRP_SIZE/2 + (i+1), maxFound, out);

            Load256(px, sx);
            ModSub256(dy, pyn, Gy[i]);
            _ModMult(_s, dy, dx[i]);
            _ModSqr(_p2, _s);
            ModSub256(px, _p2, px);
            ModSub256(px, Gx[i]);
            ModSub256(py, Gx[i], px);
            _ModMult(py, _s);
            ModSub256(py, Gy[i]);
            ModNeg256(py, py);

            CheckHashCompSymK4(px, py, tid, j*GRP_SIZE + GRP_SIZE/2 - (i+1), maxFound, out);
        }

        Load256(px, sx);
        Load256(py, sy);
        ModNeg256(dy, Gy[i]);
        ModSub256(dy, py);
        _ModMult(_s, dy, dx[i]);
        _ModSqr(_p2, _s);
        ModSub256(px, _p2, px);
        ModSub256(px, Gx[i]);
        ModSub256(py, Gx[i], px);
        _ModMult(py, _s);
        ModSub256(py, Gy[i]);
        ModNeg256(py, py);
        CheckHashCompSymK4(px, py, tid, j*GRP_SIZE, maxFound, out);

        i++;
        Load256(px, sx);
        Load256(py, sy);
        ModSub256(dy, _2Gny, py);
        _ModMult(_s, dy, dx[i]);
        _ModSqr(_p2, _s);
        ModSub256(px, _p2, px);
        ModSub256(px, _2Gnx);
        ModSub256(py, _2Gnx, px);
        _ModMult(py, _s);
        ModSub256(py, _2Gny);
    }

    // For sequential mode: advance by the additional delta to reach (nbThread * STEP_SIZE) * G
    // The loop above already advanced by STEP_SIZE * G = _2Gn
    // Now add the extra (nbThread - 1) * STEP_SIZE * G from d_seqDelta
    if (d_useSeqDelta) {
        // Point addition: (px, py) = (px, py) + (d_seqDeltaX, d_seqDeltaY)
        // Using standard EC point addition formula
        uint64_t dxSeq[4], dySeq[4], sSeq[4], s2Seq[4], rxSeq[4], rySeq[4];

        // dx = deltaX - px
        ModSub256(dxSeq, d_seqDeltaX, px);

        // dy = deltaY - py
        ModSub256(dySeq, d_seqDeltaY, py);

        // s = dy / dx (need modular inverse of dx)
        // _ModInv operates on a 320-bit extended value and inverts in place
        uint64_t invDx[5];  // 320 bits for _ModInv
        Load256(invDx, dxSeq);
        invDx[4] = 0;
        _ModInv(invDx);
        _ModMult(sSeq, dySeq, invDx);

        // s^2
        _ModSqr(s2Seq, sSeq);

        // rx = s^2 - px - deltaX
        ModSub256(rxSeq, s2Seq, px);
        ModSub256(rxSeq, d_seqDeltaX);

        // ry = s * (px - rx) - py
        ModSub256(rySeq, px, rxSeq);
        _ModMult(rySeq, sSeq, rySeq);
        ModSub256(rySeq, py);

        Load256(px, rxSeq);
        Load256(py, rySeq);
    }

    __syncthreads();
    Store256A(startx, px);
    Store256A(starty, py);
}

__global__ void searchK4_kernel(
    uint32_t mode, uint64_t* keys,
    uint32_t maxFound, uint32_t* found
) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    ComputeKeysK4(mode, keys + xPtr, keys + yPtr, maxFound, found);
}

// =====================================================================================
// HOST UTILITY FUNCTIONS
// =====================================================================================

void secure_random(void* buf, size_t len) {
    FILE* f = fopen("/dev/urandom", "rb");
    if (f) { fread(buf, 1, len, f); fclose(f); }
}

// State file format for sequential mode:
// [8 bytes: total keys] [32 bytes: base key] [keys data...]
void save_state_seq(const char* f, uint64_t* k, int n, uint64_t t, const uint64_t* baseKey) {
    FILE* fp = fopen(f, "wb");
    if (fp) {
        fwrite(&t, 8, 1, fp);
        fwrite(baseKey, 8, 4, fp);  // Save base key
        fwrite(k, 8, n*8, fp);
        fclose(fp);
    }
}

uint64_t load_state_seq(const char* f, uint64_t* k, int n, uint64_t* baseKey) {
    struct stat st;
    if (stat(f, &st)) return 0;
    FILE* fp = fopen(f, "rb");
    if (!fp) return 0;
    uint64_t t = 0;
    if (fread(&t, 8, 1, fp) != 1) { fclose(fp); return 0; }
    if (fread(baseKey, 8, 4, fp) != 4) { fclose(fp); return 0; }
    if (fread(k, 8, n*8, fp) != (size_t)(n*8)) { fclose(fp); return 0; }
    fclose(fp);
    return t;
}

// Legacy state format (random mode)
void save_state(const char* f, uint64_t* k, int n, uint64_t t) {
    FILE* fp = fopen(f, "wb");
    if (fp) { fwrite(&t, 8, 1, fp); fwrite(k, 8, n*8, fp); fclose(fp); }
}

uint64_t load_state(const char* f, uint64_t* k, int n) {
    struct stat st;
    if (stat(f, &st)) return 0;
    FILE* fp = fopen(f, "rb");
    if (!fp) return 0;
    uint64_t t = 0;
    if (fread(&t, 8, 1, fp) != 1) { fclose(fp); return 0; }
    if (fread(k, 8, n*8, fp) != (size_t)(n*8)) { fclose(fp); return 0; }
    fclose(fp);
    return t;
}

// Initialize keys sequentially from a starting point
// Optimized: compute baseKey*G once, then add G repeatedly for sequential keys
// =====================================================================================
// FAST KEY INITIALIZATION using Montgomery batch inversion + precomputed G table
// =====================================================================================

// Montgomery batch inversion: given [a0, a1, ..., an-1], compute [a0^-1, a1^-1, ..., an-1^-1]
// Uses (3n-3) multiplications + 1 inversion instead of n inversions
static void batch_mod_inv(uint64_t* results, uint64_t* inputs, int n) {
    if (n == 0) return;
    if (n == 1) {
        mod_inv(results, inputs);
        return;
    }
    
    uint64_t* partials = (uint64_t*)malloc(n * 32);
    
    memcpy(&partials[0], &inputs[0], 32);
    for (int i = 1; i < n; i++) {
        mod_mul(&partials[i * 4], &partials[(i-1) * 4], &inputs[i * 4]);
    }
    
    uint64_t inv_total[4];
    mod_inv(inv_total, &partials[(n-1) * 4]);
    
    uint64_t running_inv[4];
    memcpy(running_inv, inv_total, 32);
    
    for (int i = n - 1; i > 0; i--) {
        mod_mul(&results[i * 4], running_inv, &partials[(i-1) * 4]);
        uint64_t tmp[4];
        mod_mul(tmp, running_inv, &inputs[i * 4]);
        memcpy(running_inv, tmp, 32);
    }
    memcpy(&results[0], running_inv, 32);
    
    free(partials);
}

// Get i*G using precomputed table
static void get_iG(uint64_t* rx, uint64_t* ry, uint64_t i) {
    if (i == 0) {
        memset(rx, 0, 32);
        memset(ry, 0, 32);
        return;
    }
    if (i <= CPU_GRP_SIZE) {
        memcpy(rx, Gx_cpu[i-1], 32);
        memcpy(ry, Gy_cpu[i-1], 32);
        return;
    }
    uint64_t k[4] = {i, 0, 0, 0};
    scalar_mult_G(rx, ry, k);
}

void init_keys_from_start(uint64_t* h_keys, int nbThread, const char* startStr, bool isHex) {
    printf("Initializing %d threads for SEQUENTIAL range search...\n", nbThread);

    if (isHex) hex_to_256bit(startStr, g_baseKey);
    else decimal_to_256bit(startStr, g_baseKey);

    char hexStr[65];
    format_256bit_hex(g_baseKey, hexStr);
    printf("  Start: 0x%s\n", hexStr);

    // PROPER SEQUENTIAL RANGE SEARCH:
    // - Space threads STEP_SIZE (1024) apart for non-overlapping coverage
    // - Thread 0: keys [0, 1024), [nbThread*1024, nbThread*1024+1024), ...
    // - Thread 1: keys [1024, 2048), [nbThread*1024+1024, ...], ...
    // - Per iteration: keys [iter*nbThread*STEP_SIZE, (iter+1)*nbThread*STEP_SIZE)
    //
    // The kernel internally advances each thread by STEP_SIZE.
    // We add an ADDITIONAL delta of (nbThread-1)*STEP_SIZE*G after each iteration
    // to make total advancement = nbThread * STEP_SIZE per thread.

    uint64_t p0x[4], p0y[4];
    printf("  Computing base point...\n"); fflush(stdout);
    scalar_mult_G(p0x, p0y, g_baseKey);

    // Store thread 0's starting point (key = baseKey)
    {
        int block = 0;
        int tidInBlock = 0;
        int blockBase = block * NB_THREAD_PER_GROUP * 8;
        int xBase = blockBase + tidInBlock;
        int yBase = blockBase + 4 * NB_THREAD_PER_GROUP + tidInBlock;
        for (int j = 0; j < 4; j++) {
            h_keys[xBase + j * NB_THREAD_PER_GROUP] = p0x[j];
            h_keys[yBase + j * NB_THREAD_PER_GROUP] = p0y[j];
        }
    }

    if (nbThread == 1) {
        printf("  Done (single thread)\n");
        g_sequentialMode = true;
        g_nbThread = nbThread;
        return;
    }

    const int BATCH_SIZE = 8192;
    int remaining = nbThread - 1;
    int processed = 1;

    uint64_t* dx_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint64_t* inv_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint64_t* iGx_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint64_t* iGy_batch = (uint64_t*)malloc(BATCH_SIZE * 32);

    time_t start_time = time(NULL);

    while (remaining > 0) {
        int batch = (remaining < BATCH_SIZE) ? remaining : BATCH_SIZE;

        for (int i = 0; i < batch; i++) {
            // Thread t at key baseKey + t*STEP_SIZE (spaced by STEP_SIZE for non-overlapping)
            uint64_t offset = (uint64_t)(processed + i) * STEP_SIZE;
            get_iG(&iGx_batch[i * 4], &iGy_batch[i * 4], offset);
            mod_sub(&dx_batch[i * 4], &iGx_batch[i * 4], p0x);
        }

        batch_mod_inv(inv_batch, dx_batch, batch);

        for (int i = 0; i < batch; i++) {
            int t = processed + i;

            uint64_t *iGx = &iGx_batch[i * 4];
            uint64_t *iGy = &iGy_batch[i * 4];
            uint64_t *inv_dx = &inv_batch[i * 4];

            uint64_t dy[4], s[4], s2[4], rx[4], ry[4], tmp[4];
            mod_sub(dy, iGy, p0y);
            mod_mul(s, dy, inv_dx);
            mod_mul(s2, s, s);
            mod_sub(rx, s2, p0x);
            mod_sub(rx, rx, iGx);
            mod_sub(tmp, p0x, rx);
            mod_mul(ry, s, tmp);
            mod_sub(ry, ry, p0y);

            // Store using GPU's strided memory layout
            int block = t / NB_THREAD_PER_GROUP;
            int tidInBlock = t % NB_THREAD_PER_GROUP;
            int blockBase = block * NB_THREAD_PER_GROUP * 8;
            int xBase = blockBase + tidInBlock;
            int yBase = blockBase + 4 * NB_THREAD_PER_GROUP + tidInBlock;

            for (int j = 0; j < 4; j++) {
                h_keys[xBase + j * NB_THREAD_PER_GROUP] = rx[j];
                h_keys[yBase + j * NB_THREAD_PER_GROUP] = ry[j];
            }
        }

        processed += batch;
        remaining -= batch;

        printf("\r  Generated %d/%d thread starting points...", processed, nbThread);
        fflush(stdout);
    }

    free(dx_batch);
    free(inv_batch);
    free(iGx_batch);
    free(iGy_batch);

    double elapsed = difftime(time(NULL), start_time);
    if (elapsed < 1) elapsed = 1;
    printf("\n  Done! %d threads in %.1fs (%.0f threads/sec)\n", nbThread, elapsed, nbThread / elapsed);

    // Compute the sequential delta: (nbThread - 1) * STEP_SIZE * G
    // The kernel already advances by STEP_SIZE * G internally,
    // so we need the ADDITIONAL delta to reach total advancement of nbThread * STEP_SIZE * G
    printf("  Computing sequential delta point...\n");

    // delta_scalar = (nbThread - 1) * STEP_SIZE
    uint64_t delta_scalar[4] = {0, 0, 0, 0};
    uint64_t delta_val = (uint64_t)(nbThread - 1) * STEP_SIZE;
    delta_scalar[0] = delta_val;

    // Compute delta_point = delta_scalar * G
    uint64_t seqDeltaX[4], seqDeltaY[4];
    scalar_mult_G(seqDeltaX, seqDeltaY, delta_scalar);

    // Copy to device constants
    cudaError_t err;
    err = cudaMemcpyToSymbol(d_seqDeltaX, seqDeltaX, 32);
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying seqDeltaX: %s\n", cudaGetErrorString(err));
    }
    err = cudaMemcpyToSymbol(d_seqDeltaY, seqDeltaY, 32);
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying seqDeltaY: %s\n", cudaGetErrorString(err));
    }
    int useSeq = 1;
    err = cudaMemcpyToSymbol(d_useSeqDelta, &useSeq, sizeof(int));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying useSeqDelta: %s\n", cudaGetErrorString(err));
    }

    uint64_t totalDelta = (uint64_t)nbThread * STEP_SIZE;
    printf("  Sequential mode: each iteration advances all threads by %lu keys\n", totalDelta);
    printf("  Keys covered after N iterations: N * %lu\n", totalDelta);
    printf("  Example: iter 1 covers first %lu keys\n", totalDelta);

    g_sequentialMode = true;
    g_nbThread = nbThread;
}

// Reconstruct private key from match info
// parity: 0=even compressed, 1=odd compressed, 2=uncompressed
void reconstruct_privkey(uint64_t* privkey, uint32_t tid, int32_t incr, uint64_t iter, uint8_t parity) {
    // SEQUENTIAL MODE with proper thread spacing:
    // - Thread tid starts at key baseKey + tid * STEP_SIZE
    // - Each iteration covers STEP_SIZE keys, then advances by nbThread * STEP_SIZE
    // - After iter iterations: thread is at key baseKey + tid*STEP_SIZE + iter*nbThread*STEP_SIZE
    //
    // The GPU checks compressed (02+X and 03+X) and uncompressed (04+X+Y) forms.
    // parity indicates which form matched: 0=even, 1=odd, 2=uncompressed

    // For odd reported parity (compressed), the kernel stored -incr, so flip it back
    // For uncompressed (parity=2), incr is not negated
    int32_t actualIncr = (parity == 1) ? -incr : incr;

    // The kernel passes incr such that:
    //   actualIncr = GRP_SIZE/2 means offset 0 from starting point
    //   actualIncr = GRP_SIZE/2 + k means offset +k from starting point
    int32_t keyOffset = actualIncr - 512;  // 512 = GRP_SIZE/2

    // Formula: basePrivkey = baseKey + tid*STEP_SIZE + iter*nbThread*STEP_SIZE + keyOffset
    uint64_t basePrivkey[4] = {0, 0, 0, 0};

    // Add thread's starting offset: tid * STEP_SIZE
    uint64_t threadOffset = (uint64_t)tid * STEP_SIZE;
    add256_scalar(basePrivkey, g_baseKey, threadOffset);

    // Add iteration offset: iter * nbThread * STEP_SIZE
    // This is a 256-bit multiplication since it can be large
    uint64_t keysPerIter = (uint64_t)g_nbThread * STEP_SIZE;
    // For iter up to ~2^32 and keysPerIter = 67M, product fits in 64 bits... actually no.
    // iter * 67M can overflow 64-bit for large iter. Need to handle this carefully.
    // For now, iter is usually small (< 2^32), and keysPerIter is ~67M, so product is ~2^56
    // But for safety, let's do proper 128-bit arithmetic
    __uint128_t iterOffset128 = (__uint128_t)iter * keysPerIter;
    uint64_t iterOffsetLo = (uint64_t)iterOffset128;
    uint64_t iterOffsetHi = (uint64_t)(iterOffset128 >> 64);
    uint64_t iterOffsetArr[4] = {iterOffsetLo, iterOffsetHi, 0, 0};
    add256(basePrivkey, basePrivkey, iterOffsetArr);

    // Add keyOffset (can be negative)
    if (keyOffset >= 0) {
        add256_scalar(basePrivkey, basePrivkey, (uint64_t)keyOffset);
    } else {
        uint64_t negOffset = (uint64_t)(-keyOffset);
        uint64_t tmp[4] = {negOffset, 0, 0, 0};
        sub256(basePrivkey, basePrivkey, tmp);
    }

    // For uncompressed addresses, we use the key directly (no parity adjustment needed)
    if (parity == 2) {
        memcpy(privkey, basePrivkey, 32);
        return;
    }

    // For compressed: Compute Y parity of basePrivkey * G
    uint64_t px[4], py[4];
    scalar_mult_G(px, py, basePrivkey);
    bool actualYOdd = (py[0] & 1) != 0;
    bool reportedOdd = (parity == 1);

    // If actual Y parity matches reported parity, use basePrivkey
    // Otherwise, use N - basePrivkey
    if (actualYOdd == reportedOdd) {
        memcpy(privkey, basePrivkey, 32);
    } else {
        // Negate mod N (the curve order): privkey = N - basePrivkey
        sub256(privkey, SECP_N, basePrivkey);
    }
}

// Base58 encoding for WIF
static const char b58_alphabet[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// Host-side SHA256 for checksum calculation (must be defined before functions that use it)
static void sha256_host(const uint8_t* data, size_t len, uint8_t* hash) {
    uint32_t h[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    static const uint32_t k[64] = {
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
        0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
        0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
        0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
        0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
        0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
        0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
        0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
        0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    };

    // Pad message
    uint8_t padded[128];
    memset(padded, 0, 128);
    memcpy(padded, data, len);
    padded[len] = 0x80;

    size_t padded_len = ((len + 9 + 63) / 64) * 64;
    uint64_t bit_len = len * 8;
    padded[padded_len - 8] = (bit_len >> 56) & 0xFF;
    padded[padded_len - 7] = (bit_len >> 48) & 0xFF;
    padded[padded_len - 6] = (bit_len >> 40) & 0xFF;
    padded[padded_len - 5] = (bit_len >> 32) & 0xFF;
    padded[padded_len - 4] = (bit_len >> 24) & 0xFF;
    padded[padded_len - 3] = (bit_len >> 16) & 0xFF;
    padded[padded_len - 2] = (bit_len >> 8) & 0xFF;
    padded[padded_len - 1] = bit_len & 0xFF;

    // Process blocks
    for (size_t block = 0; block < padded_len; block += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; i++) {
            w[i] = ((uint32_t)padded[block + i*4] << 24) |
                   ((uint32_t)padded[block + i*4 + 1] << 16) |
                   ((uint32_t)padded[block + i*4 + 2] << 8) |
                   ((uint32_t)padded[block + i*4 + 3]);
        }

        for (int i = 16; i < 64; i++) {
            uint32_t s0 = ((w[i-15] >> 7) | (w[i-15] << 25)) ^ ((w[i-15] >> 18) | (w[i-15] << 14)) ^ (w[i-15] >> 3);
            uint32_t s1 = ((w[i-2] >> 17) | (w[i-2] << 15)) ^ ((w[i-2] >> 19) | (w[i-2] << 13)) ^ (w[i-2] >> 10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }

        uint32_t a = h[0], b = h[1], c = h[2], d = h[3];
        uint32_t e = h[4], f = h[5], g = h[6], hh = h[7];

        for (int i = 0; i < 64; i++) {
            uint32_t S1 = ((e >> 6) | (e << 26)) ^ ((e >> 11) | (e << 21)) ^ ((e >> 25) | (e << 7));
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t temp1 = hh + S1 + ch + k[i] + w[i];
            uint32_t S0 = ((a >> 2) | (a << 30)) ^ ((a >> 13) | (a << 19)) ^ ((a >> 22) | (a << 10));
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t temp2 = S0 + maj;

            hh = g; g = f; f = e; e = d + temp1;
            d = c; c = b; b = a; a = temp1 + temp2;
        }

        h[0] += a; h[1] += b; h[2] += c; h[3] += d;
        h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }

    for (int i = 0; i < 8; i++) {
        hash[i*4] = (h[i] >> 24) & 0xFF;
        hash[i*4 + 1] = (h[i] >> 16) & 0xFF;
        hash[i*4 + 2] = (h[i] >> 8) & 0xFF;
        hash[i*4 + 3] = h[i] & 0xFF;
    }
}

void privkey_to_wif(const uint64_t* key, char* wif, bool compressed) {
    uint8_t data[38];
    data[0] = 0x80;  // Mainnet prefix

    // Copy key bytes (big-endian)
    for (int i = 0; i < 32; i++) {
        data[1 + i] = ((uint8_t*)key)[31 - i];
    }

    int dataLen = 33;
    if (compressed) {
        data[33] = 0x01;  // Compression flag
        dataLen = 34;
    }

    // Compute checksum: first 4 bytes of double SHA256
    uint8_t sha1[32], sha2[32];
    sha256_host(data, dataLen, sha1);
    sha256_host(sha1, 32, sha2);

    data[dataLen] = sha2[0];
    data[dataLen+1] = sha2[1];
    data[dataLen+2] = sha2[2];
    data[dataLen+3] = sha2[3];
    dataLen += 4;

    // Base58 encode
    int zeros = 0;
    while (zeros < dataLen && data[zeros] == 0) zeros++;

    uint8_t temp[64];
    int tempLen = 0;

    for (int i = 0; i < dataLen; i++) {
        int carry = data[i];
        for (int j = 0; j < tempLen; j++) {
            carry += 256 * temp[j];
            temp[j] = carry % 58;
            carry /= 58;
        }
        while (carry > 0) {
            temp[tempLen++] = carry % 58;
            carry /= 58;
        }
    }

    int idx = 0;
    for (int i = 0; i < zeros; i++) wif[idx++] = '1';
    for (int i = tempLen - 1; i >= 0; i--) wif[idx++] = b58_alphabet[temp[i]];
    wif[idx] = '\0';
}

// Host-side hash160 to address with CORRECT double-SHA256 checksum
void hash160_to_address_host(const uint8_t* hash160, char* addr) {
    uint8_t data[25];
    data[0] = 0x00;  // Mainnet P2PKH version byte
    memcpy(data + 1, hash160, 20);

    // Compute checksum: first 4 bytes of double SHA256
    uint8_t sha1[32], sha2[32];
    sha256_host(data, 21, sha1);
    sha256_host(sha1, 32, sha2);

    data[21] = sha2[0];
    data[22] = sha2[1];
    data[23] = sha2[2];
    data[24] = sha2[3];

    int zeros = 0;
    while (zeros < 25 && data[zeros] == 0) zeros++;

    uint8_t temp[35];
    int tempLen = 0;

    for (int i = 0; i < 25; i++) {
        int carry = data[i];
        for (int j = 0; j < tempLen; j++) {
            carry += 256 * temp[j];
            temp[j] = carry % 58;
            carry /= 58;
        }
        while (carry > 0) {
            temp[tempLen++] = carry % 58;
            carry /= 58;
        }
    }

    int idx = 0;
    for (int i = 0; i < zeros; i++) addr[idx++] = '1';
    for (int i = tempLen - 1; i >= 0; i--) addr[idx++] = b58_alphabet[temp[i]];
    addr[idx] = '\0';
}

// Load patterns
int load_patterns(const char* filename, char patterns[][36], int* lens, int max_patterns) {
    FILE* f = fopen(filename, "r");
    if (!f) {
        printf("Error: Cannot open patterns file: %s\n", filename);
        return 0;
    }

    int count = 0;
    char line[256];

    while (fgets(line, sizeof(line), f) && count < max_patterns) {
        int len = strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r')) {
            line[--len] = '\0';
        }

        if (len == 0 || line[0] == '#') continue;
        if (line[0] != '1') {
            printf("Warning: Skipping pattern (must start with '1'): %s\n", line);
            continue;
        }

        bool valid = true;
        for (int i = 0; i < len && valid; i++) {
            if (strchr("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", line[i]) == NULL) {
                printf("Warning: Invalid Base58 char in: %s\n", line);
                valid = false;
            }
        }
        if (!valid) continue;

        strncpy(patterns[count], line, 35);
        patterns[count][35] = '\0';
        lens[count] = len;

        printf("Pattern %d: %s (len=%d)\n", count, patterns[count], lens[count]);
        count++;
    }

    fclose(f);
    return count;
}

void print_usage(const char* prog) {
    printf("SearchK4 - GPU Vanity Address Search with Sequential Keyspace\n\n");
    printf("Usage: %s -patterns <file> -start <value> [options]\n", prog);
    printf("       %s -patterns <file> -startx <hex> [options]\n", prog);
    printf("       %s -patterns <file> -state <file> [options]\n\n", prog);
    printf("Required:\n");
    printf("  -patterns <file>   File with vanity prefixes (one per line)\n");
    printf("  -start <value>     Starting private key (decimal)  \\ One of these\n");
    printf("  -startx <value>    Starting private key (hex)       | is REQUIRED\n");
    printf("  -state <file>      Resume from state file          /\n\n");
    printf("Optional:\n");
    printf("  -gpu <id>          GPU device ID (default: 0)\n");
    printf("  -o <file>          Output file (default: found_k4.txt)\n");
    printf("  -h, --help         Show this help\n\n");
    printf("NOTE: Random mode is DISABLED. Sequential range search is required.\n\n");
    printf("Examples:\n");
    printf("  # Search from hex start (Puzzle #66 range):\n");
    printf("  %s -patterns patterns.txt -startx 0x20000000000000000\n\n", prog);
    printf("  # Search from decimal start:\n");
    printf("  %s -patterns patterns.txt -start 36893488147419103232\n\n", prog);
    printf("  # Resume from state file:\n");
    printf("  %s -patterns patterns.txt -state gpu0.state\n\n", prog);
    printf("  # Multiple GPUs (run separate instances):\n");
    printf("  %s -patterns p.txt -gpu 0 -startx 0x20000000000000000 -state g0.state\n", prog);
    printf("  %s -patterns p.txt -gpu 1 -startx 0x28000000000000000 -state g1.state\n", prog);
    printf("  %s -patterns p.txt -gpu 2 -startx 0x30000000000000000 -state g2.state\n", prog);
    printf("  %s -patterns p.txt -gpu 3 -startx 0x38000000000000000 -state g3.state\n\n", prog);
}

int main(int argc, char** argv) {
    char* patternsFile = NULL;
    char* stateFile = NULL;
    char* outputFile = (char*)"found_k4.txt";
    char* startDecimal = NULL;
    char* startHex = NULL;
    int gpuId = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-patterns") && i+1 < argc) patternsFile = argv[++i];
        else if (!strcmp(argv[i], "-gpu") && i+1 < argc) gpuId = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-state") && i+1 < argc) stateFile = argv[++i];
        else if (!strcmp(argv[i], "-o") && i+1 < argc) outputFile = argv[++i];
        else if (!strcmp(argv[i], "-start") && i+1 < argc) startDecimal = argv[++i];
        else if (!strcmp(argv[i], "-startx") && i+1 < argc) startHex = argv[++i];
        else if (!strcmp(argv[i], "-h") || !strcmp(argv[i], "--help")) {
            print_usage(argv[0]);
            return 0;
        }
    }

    if (!patternsFile) {
        print_usage(argv[0]);
        return 1;
    }

    // Load patterns
    char h_patterns[K4_MAX_PATTERNS][36];
    int h_lens[K4_MAX_PATTERNS];
    int numPatterns = load_patterns(patternsFile, h_patterns, h_lens, K4_MAX_PATTERNS);
    if (numPatterns == 0) {
        printf("Error: No valid patterns loaded\n");
        return 1;
    }
    printf("Loaded %d patterns\n\n", numPatterns);

    char defaultState[256];
    if (!stateFile) {
        snprintf(defaultState, 256, "gpu%d.state", gpuId);
        stateFile = defaultState;
    }

    signal(SIGINT, sighandler);
    signal(SIGTERM, sighandler);
    cudaSetDevice(gpuId);

    // Increase stack size limit for larger kernels with uncompressed address support
    cudaDeviceSetLimit(cudaLimitStackSize, 40 * 1024);  // 40KB per thread

    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, gpuId);
    printf("GPU %d: %s (SM %d.%d, %d MPs)\n", gpuId, prop.name, prop.major, prop.minor, prop.multiProcessorCount);

    // Copy patterns to GPU constant memory
    cudaError_t err;
    err = cudaMemcpyToSymbol(d_patterns, h_patterns, sizeof(h_patterns));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying patterns: %s\n", cudaGetErrorString(err));
        return 1;
    }
    err = cudaMemcpyToSymbol(d_pattern_lens, h_lens, sizeof(h_lens));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying pattern lengths: %s\n", cudaGetErrorString(err));
        return 1;
    }
    err = cudaMemcpyToSymbol(d_num_patterns, &numPatterns, sizeof(int));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying num_patterns: %s\n", cudaGetErrorString(err));
        return 1;
    }
    printf("Successfully copied %d patterns to GPU constant memory\n", numPatterns);

    int nbThread = 32768;  // Balanced for uncompressed + compressed address support
    g_nbThread = nbThread;
    uint64_t* d_keys;
    uint32_t* d_found;

    err = cudaMalloc(&d_keys, nbThread * 64);
    if (err != cudaSuccess) {
        printf("CUDA ERROR allocating d_keys: %s\n", cudaGetErrorString(err));
        return 1;
    }
    err = cudaMalloc(&d_found, (1 + MAX_FOUND * 8) * 4);
    if (err != cudaSuccess) {
        printf("CUDA ERROR allocating d_found: %s\n", cudaGetErrorString(err));
        return 1;
    }

    uint64_t* h_keys = (uint64_t*)malloc(nbThread * 64);
    uint64_t resumedKeys = 0;

    // Initialize keys - SEQUENTIAL MODE ONLY (random mode disabled)
    if (startDecimal || startHex) {
        // Sequential mode from command line
        if (startHex) {
            init_keys_from_start(h_keys, nbThread, startHex, true);
        } else {
            init_keys_from_start(h_keys, nbThread, startDecimal, false);
        }
    } else {
        // Try to load state file
        uint64_t loadedBase[4] = {0};
        resumedKeys = load_state_seq(stateFile, h_keys, nbThread, loadedBase);

        if (resumedKeys > 0 && (loadedBase[0] | loadedBase[1] | loadedBase[2] | loadedBase[3]) != 0) {
            // Resumed sequential mode
            memcpy(g_baseKey, loadedBase, sizeof(g_baseKey));
            g_sequentialMode = true;
            char hexStr[65];
            format_256bit_hex(g_baseKey, hexStr);
            printf("Resumed SEQUENTIAL from %.2fB keys\n", resumedKeys/1e9);
            printf("  Base key: 0x%s\n", hexStr);
        } else {
            // No valid sequential state and no start key provided
            // RANDOM MODE IS DISABLED - require explicit start key
            printf("\n");
            printf("ERROR: No starting key specified and no valid sequential state file found.\n");
            printf("\n");
            printf("Random mode is DISABLED. You must specify a starting key for sequential search:\n");
            printf("  -start <decimal>   Start from decimal private key value\n");
            printf("  -startx <hex>      Start from hex private key value (with or without 0x)\n");
            printf("\n");
            printf("Examples:\n");
            printf("  %s -patterns patterns.txt -startx 0x8000000000000000\n", argv[0]);
            printf("  %s -patterns patterns.txt -start 9223372036854775808\n", argv[0]);
            printf("\n");
            printf("Or resume from a valid sequential state file:\n");
            printf("  %s -patterns patterns.txt -state gpu0.state\n", argv[0]);
            printf("\n");
            free(h_keys);
            cudaFree(d_keys);
            cudaFree(d_found);
            return 1;
        }
    }

    cudaMemcpy(d_keys, h_keys, nbThread * 64, cudaMemcpyHostToDevice);

    uint32_t* h_found;
    cudaMallocHost(&h_found, (1 + MAX_FOUND * 8) * 4);

    printf("\nMode: SEQUENTIAL (range search)\n");
    printf("Running: %d threads, %d patterns\n", nbThread, numPatterns);
    printf("Output: %s\n\n", outputFile);

    time_t start = time(NULL);
    uint64_t total = resumedKeys, iter = 0;

    while (running) {
        cudaMemset(d_found, 0, 4);
        searchK4_kernel<<<nbThread/NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP>>>(
            0, d_keys, MAX_FOUND, d_found);
        cudaDeviceSynchronize();

        cudaError_t err = cudaGetLastError();
        if (err != cudaSuccess) {
            printf("\nCUDA Error: %s\n", cudaGetErrorString(err));
            break;
        }

        cudaMemcpy(h_found, d_found, 4, cudaMemcpyDeviceToHost);
        if (h_found[0] > 0) {
            uint32_t nFound = h_found[0];
            if (nFound > MAX_FOUND) nFound = MAX_FOUND;

            cudaMemcpy(h_found, d_found, (1 + nFound * 8) * 4, cudaMemcpyDeviceToHost);

            FILE* mf = fopen(outputFile, "a");
            time_t now = time(NULL);
            char* timestr = ctime(&now);
            timestr[strlen(timestr)-1] = '\0';

            printf("\n[!] Found %u matches!\n", nFound);

            for (uint32_t i = 0; i < nFound; i++) {
                uint32_t* entry = h_found + 1 + i*8;
                uint32_t tid = entry[0];
                int32_t incr = (int32_t)entry[1];
                int pattern_idx = (entry[2] >> 8) & 0xFF;
                uint8_t isOdd = entry[2] & 0xFF;
                uint32_t* hash = entry + 3;

                uint8_t hash160[20];
                for (int w = 0; w < 5; w++) {
                    uint32_t v = hash[w];
                    hash160[w*4 + 0] = (v >> 0) & 0xFF;
                    hash160[w*4 + 1] = (v >> 8) & 0xFF;
                    hash160[w*4 + 2] = (v >> 16) & 0xFF;
                    hash160[w*4 + 3] = (v >> 24) & 0xFF;
                }

                char addr[40];
                hash160_to_address_host(hash160, addr);

                const char* pattern = (pattern_idx >= 0 && pattern_idx < numPatterns) ?
                                       h_patterns[pattern_idx] : "?";

                // Reconstruct and display private key (sequential mode)
                uint64_t privkey[4];
                reconstruct_privkey(privkey, tid, incr, iter, isOdd);

                char hexKey[65], wifKey[60];
                format_256bit_hex(privkey, hexKey);
                bool isCompressed = (isOdd != 2);  // parity 0,1 = compressed, 2 = uncompressed
                privkey_to_wif(privkey, wifKey, isCompressed);

                const char* addrType = isCompressed ? "compressed" : "uncompressed";
                fprintf(mf, "[%s] Pattern='%s' Address=%s (%s)\n", timestr, pattern, addr, addrType);
                fprintf(mf, "  PrivKey (HEX): 0x%s\n", hexKey);
                fprintf(mf, "  PrivKey (WIF): %s\n", wifKey);
                fprintf(mf, "  Hash160: ");
                for (int b = 0; b < 20; b++) fprintf(mf, "%02x", hash160[b]);
                fprintf(mf, "\n  tid=%u incr=%d parity=%d iter=%lu\n\n", tid, incr, isOdd, iter);

                printf("  %s -> Pattern: %s\n", addr, pattern);
                printf("    PrivKey: 0x%s\n", hexKey);
            }
            fclose(mf);
        }

        // Sequential mode: each iteration covers nbThread * STEP_SIZE unique keys
        // After iter iterations: covered range [0, iter * nbThread * STEP_SIZE)
        uint64_t keysPerIter = (uint64_t)nbThread * STEP_SIZE;
        total += keysPerIter;
        iter++;

        if (iter % 500 == 0) {
            cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
            save_state_seq(stateFile, h_keys, nbThread, total, g_baseKey);
        }

        if (iter % 10 == 0) {  // More frequent updates since each iter covers 67M keys
            double t = difftime(time(NULL), start);
            if (t < 1) t = 1;
            double rate = total / t / 1e9;
            printf("\r[%5.0fs] Covered: %.3fB keys | %.2f GKey/s | iter=%lu     ",
                   t, total/1e9, rate, iter);
            fflush(stdout);
        }
    }

    printf("\n\nSaving state...\n");
    cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
    save_state_seq(stateFile, h_keys, nbThread, total, g_baseKey);
    printf("Total: %.2fB keys\n", total/1e9);

    cudaFree(d_keys);
    cudaFree(d_found);
    cudaFreeHost(h_found);
    free(h_keys);

    return 0;
}
