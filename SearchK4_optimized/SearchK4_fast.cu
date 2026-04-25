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
#include <ctype.h>


#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"
#include "CPUGroup.h"
#include "ripemd160.h"    // host-side post-match verification (external drop-in)

// Host-side comparator for sorting hash160 arrays before binary-search upload
static int cmp_h160_host(const void *a, const void *b) {
    const uint32_t *x = (const uint32_t*)a;
    const uint32_t *y = (const uint32_t*)b;
    for (int i = 0; i < 5; i++) {
        if (x[i] < y[i]) return -1;
        if (x[i] > y[i]) return  1;
    }
    return 0;
}

#define NB_THREAD_PER_GROUP 64
#define MAX_FOUND 65536
#define STEP_SIZE 1024
#define K4_MAX_PATTERNS 256
#define K4_MAX_TARGETS 8192
#define K4_PATTERN_MAX_LEN 35
#define P2PKH 0
#define K4_STATE_VERSION 2U

// Bloom filter for fast hash160 target pre-screening.
// 64 KB filter in global memory (hot in L2 cache) with 3 hash functions.
// At 5000 targets: fill ~2.9%, false positive rate ~0.002%.
#define BLOOM_SIZE_BITS  (512 * 1024)  // 512Kbit = 64KB
#define BLOOM_SIZE_U32   (BLOOM_SIZE_BITS / 32)
#define BLOOM_NUM_HASHES 3


// Base58 alphabet
__device__ __constant__ char pszBase58[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// Pattern storage - each pattern is null-terminated, max 35 chars
// Used in prefix-match mode (legacy vanity behaviour).
__device__ __constant__ char d_patterns[K4_MAX_PATTERNS][36];
__device__ __constant__ int d_pattern_lens[K4_MAX_PATTERNS];
__device__ __constant__ int d_num_patterns;

// Hash160 target storage (20 bytes = 5 uint32 per target). Used in
// -direct mode to skip Base58 entirely and do a raw 20-byte compare.
// Stored in global memory (not constant) to support large target lists.
__device__ uint32_t d_target_h160[K4_MAX_TARGETS][5];        // uncompressed targets (primary)
__device__ __constant__ int d_num_targets;
// 0 = legacy prefix-match mode (runs Base58, also checks uncompressed)
// 1 = hash160-direct mode: uncompressed hash160 only
__device__ __constant__ int d_direct_mode;

// Bloom filter in global memory for fast pre-screening of hash160 candidates.
__device__ uint32_t d_bloom_filter[BLOOM_SIZE_U32];

// Range end (for -endx clamping). If d_have_endx != 0, the host checks
// between iterations whether the covered range has passed end; not checked
// in the kernel to keep the hot path branch-free.
__device__ __constant__ uint64_t d_endKey[4];
__device__ __constant__ int d_have_endx;

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
static int g_nbThread = 16384;
static const char K4_STATE_MAGIC[8] = {'K', '4', 'S', 'E', 'Q', 'V', '2', '\0'};

#pragma pack(push, 1)
typedef struct {
    char magic[8];
    uint32_t version;
    uint32_t threadCount;
    uint64_t stepSize;
    uint64_t totalKeys;
    uint64_t iter;
    uint64_t keysPerIter;
    uint64_t baseKey[4];
    uint64_t keyWords;
    uint64_t checksum;
} K4StateHeaderV2;
#pragma pack(pop)

typedef struct {
    uint64_t totalKeys;
    uint64_t iter;
    uint64_t baseKey[4];
    uint32_t threadCount;
    uint64_t keysPerIter;
    bool legacyFormat;
} K4LoadedState;


// 256-bit comparison
static int cmp256(const uint64_t* a, const uint64_t* b) {
    for (int i = 3; i >= 0; i--) {
        if (a[i] > b[i]) return 1;
        if (a[i] < b[i]) return -1;
    }
    return 0;
}

static bool is_zero256_host(const uint64_t* a) {
    return (a[0] | a[1] | a[2] | a[3]) == 0;
}

static bool is_private_key_in_range(const uint64_t* key) {
    return !is_zero256_host(key) && cmp256(key, SECP_N) < 0;
}

static void set_one256_host(uint64_t* a) {
    a[0] = 1;
    a[1] = 0;
    a[2] = 0;
    a[3] = 0;
}

static bool is_separator_char(char c) {
    return c == '_' || c == ',';
}

static void trim_ascii_span(const char** begin, const char** end) {
    while (*begin < *end && isspace((unsigned char)**begin)) (*begin)++;
    while (*end > *begin && isspace((unsigned char)*((*end) - 1))) (*end)--;
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

static void normalize_mod_n(uint64_t* r) {
    while (cmp256(r, SECP_N) >= 0) {
        sub256(r, r, SECP_N);
    }
}

static void add_mod_n(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t carry = add256(r, a, b);
    if (carry || cmp256(r, SECP_N) >= 0) {
        sub256(r, r, SECP_N);
    }
}

static void add_mod_n_scalar(uint64_t* r, const uint64_t* a, uint64_t b) {
    uint64_t tmp[4] = {b, 0, 0, 0};
    add_mod_n(r, a, tmp);
}

static void sub_mod_n(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    if (sub256(r, a, b)) {
        add256(r, r, SECP_N);
    }
    normalize_mod_n(r);
}

static void mul_u64_u64_mod_n(uint64_t* r, uint64_t a, uint64_t b) {
    uint64_t acc[4] = {0, 0, 0, 0};
    uint64_t base[4] = {a, 0, 0, 0};

    while (b) {
        if (b & 1ULL) {
            add_mod_n(acc, acc, base);
        }
        b >>= 1;
        if (b) {
            add_mod_n(base, base, base);
        }
    }

    memcpy(r, acc, sizeof(acc));
}

static uint64_t fnv1a64_update(uint64_t hash, const void* data, size_t len) {
    const uint8_t* bytes = (const uint8_t*)data;
    for (size_t i = 0; i < len; i++) {
        hash ^= bytes[i];
        hash *= 1099511628211ULL;
    }
    return hash;
}

static uint64_t compute_state_checksum(const K4StateHeaderV2* header, const uint64_t* keys) {
    uint64_t hash = 1469598103934665603ULL;
    hash = fnv1a64_update(hash, header->magic, sizeof(header->magic));
    hash = fnv1a64_update(hash, &header->version, sizeof(header->version));
    hash = fnv1a64_update(hash, &header->threadCount, sizeof(header->threadCount));
    hash = fnv1a64_update(hash, &header->stepSize, sizeof(header->stepSize));
    hash = fnv1a64_update(hash, &header->totalKeys, sizeof(header->totalKeys));
    hash = fnv1a64_update(hash, &header->iter, sizeof(header->iter));
    hash = fnv1a64_update(hash, &header->keysPerIter, sizeof(header->keysPerIter));
    hash = fnv1a64_update(hash, header->baseKey, sizeof(header->baseKey));
    hash = fnv1a64_update(hash, &header->keyWords, sizeof(header->keyWords));
    hash = fnv1a64_update(hash, keys, header->keyWords * sizeof(uint64_t));
    return hash;
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

// Convert decimal string to a strict 256-bit integer
static bool decimal_to_256bit(const char* decimal, uint64_t* result, char* err, size_t errSize) {
    memset(result, 0, 32);
    if (!decimal) {
        snprintf(err, errSize, "missing decimal input");
        return false;
    }

    const char* begin = decimal;
    const char* end = decimal + strlen(decimal);
    trim_ascii_span(&begin, &end);
    if (begin == end) {
        snprintf(err, errSize, "decimal input is empty");
        return false;
    }

    bool sawDigit = false;
    for (const char* p = begin; p < end; ++p) {
        unsigned char c = (unsigned char)*p;
        if (c >= '0' && c <= '9') {
            sawDigit = true;

            __uint128_t carry = 0;
            for (int k = 0; k < 4; k++) {
                __uint128_t prod = (__uint128_t)result[k] * 10 + carry;
                result[k] = (uint64_t)prod;
                carry = prod >> 64;
            }
            if (carry) {
                snprintf(err, errSize, "decimal value exceeds 256 bits");
                return false;
            }

            carry = (uint64_t)(c - '0');
            for (int k = 0; k < 4 && carry; k++) {
                __uint128_t sum = (__uint128_t)result[k] + carry;
                result[k] = (uint64_t)sum;
                carry = sum >> 64;
            }
            if (carry) {
                snprintf(err, errSize, "decimal value exceeds 256 bits");
                return false;
            }
        } else if (is_separator_char((char)c)) {
            continue;
        } else {
            snprintf(err, errSize, "invalid decimal character '%c'", *p);
            return false;
        }
    }

    if (!sawDigit) {
        snprintf(err, errSize, "decimal input does not contain digits");
        return false;
    }

    return true;
}

// Convert hex string to a strict 256-bit integer
static bool hex_to_256bit(const char* hex, uint64_t* result, char* err, size_t errSize) {
    memset(result, 0, 32);
    if (!hex) {
        snprintf(err, errSize, "missing hexadecimal input");
        return false;
    }

    const char* begin = hex;
    const char* end = hex + strlen(hex);
    trim_ascii_span(&begin, &end);
    if (begin == end) {
        snprintf(err, errSize, "hex input is empty");
        return false;
    }

    if ((end - begin) >= 2 && begin[0] == '0' && (begin[1] == 'x' || begin[1] == 'X')) {
        begin += 2;
    }

    char clean[65];
    int cleanLen = 0;
    for (const char* p = begin; p < end; ++p) {
        unsigned char c = (unsigned char)*p;
        if (isxdigit(c)) {
            if (cleanLen >= 64) {
                snprintf(err, errSize, "hex value exceeds 64 hex digits");
                return false;
            }
            clean[cleanLen++] = (char)c;
        } else if (is_separator_char((char)c)) {
            continue;
        } else {
            snprintf(err, errSize, "invalid hex character '%c'", *p);
            return false;
        }
    }

    if (cleanLen == 0) {
        snprintf(err, errSize, "hex input does not contain digits");
        return false;
    }

    uint8_t* bytes = (uint8_t*)result;
    for (int i = 0; i < cleanLen; i++) {
        char c = clean[cleanLen - 1 - i];
        int val;
        if (c >= '0' && c <= '9') val = c - '0';
        else if (c >= 'a' && c <= 'f') val = c - 'a' + 10;
        else val = c - 'A' + 10;

        int byteIdx = i / 2;
        if ((i & 1) == 0) bytes[byteIdx] = (uint8_t)val;
        else bytes[byteIdx] |= (uint8_t)(val << 4);
    }

    return true;
}

static bool parse_start_key(const char* input, bool isHex, uint64_t* result, char* err, size_t errSize) {
    bool ok = isHex ? hex_to_256bit(input, result, err, errSize)
                    : decimal_to_256bit(input, result, err, errSize);
    if (!ok) return false;
    if (!is_private_key_in_range(result)) {
        snprintf(err, errSize, "private key must be in the range [1, secp256k1_n - 1]");
        return false;
    }
    return true;
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
        b58Add[retPos++] = 0x31;  // ASCII '1' - use explicit hex to avoid CUDA char literal issues
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

__device__ __forceinline__ bool IsZero256Dev(const uint64_t* a) {
    return (a[0] | a[1] | a[2] | a[3]) == 0ULL;
}

__device__ __forceinline__ void SetZero256Dev(uint64_t* a) {
    a[0] = 0ULL;
    a[1] = 0ULL;
    a[2] = 0ULL;
    a[3] = 0ULL;
}

__device__ __forceinline__ void SetOne256Dev(uint64_t* a) {
    a[0] = 1ULL;
    a[1] = 0ULL;
    a[2] = 0ULL;
    a[3] = 0ULL;
}

__device__ __forceinline__ void ModAdd256Dev(uint64_t* r, uint64_t* a, uint64_t* b) {
    uint64_t negB[4];
    Load256(negB, b);
    ModNeg256(negB);
    ModSub256(r, a, negB);
}

__device__ __noinline__ bool PointAddAffineDev(
    uint64_t* rx, uint64_t* ry,
    const uint64_t* pxIn, const uint64_t* pyIn,
    const uint64_t* qxIn, const uint64_t* qyIn
) {
    uint64_t px[4], py[4], qx[4], qy[4];
    uint64_t dx[4], dy[4], s[4], s2[4], tmp[4];

    Load256(px, pxIn);
    Load256(py, pyIn);
    Load256(qx, qxIn);
    Load256(qy, qyIn);

    if (IsZero256Dev(px) && IsZero256Dev(py)) {
        Load256(rx, qx);
        Load256(ry, qy);
        return !IsZero256Dev(qx) || !IsZero256Dev(qy);
    }
    if (IsZero256Dev(qx) && IsZero256Dev(qy)) {
        Load256(rx, px);
        Load256(ry, py);
        return true;
    }

    ModSub256(dx, qx, px);
    if (IsZero256Dev(dx)) {
        ModSub256(dy, qy, py);
        if (!IsZero256Dev(dy)) {
            SetZero256Dev(rx);
            SetZero256Dev(ry);
            return false;
        }
        if (IsZero256Dev(py)) {
            SetZero256Dev(rx);
            SetZero256Dev(ry);
            return false;
        }

        _ModSqr(s, px);
        ModAdd256Dev(tmp, s, s);
        ModAdd256Dev(s, tmp, s);
        ModAdd256Dev(dy, py, py);

        uint64_t invDy[5];
        Load256(invDy, dy);
        invDy[4] = 0;
        _ModInv(invDy);
        _ModMult(s, s, invDy);
    } else {
        ModSub256(dy, qy, py);
        uint64_t invDx[5];
        Load256(invDx, dx);
        invDx[4] = 0;
        _ModInv(invDx);
        _ModMult(s, dy, invDx);
    }

    _ModSqr(s2, s);
    ModSub256(rx, s2, px);
    ModSub256(rx, qx);

    ModSub256(tmp, px, rx);
    _ModMult(ry, s, tmp);
    ModSub256(ry, py);
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

// Hash160-direct match: compare the 20 raw bytes from _GetHash160CompSym
// against the precomputed targets in constant memory. Much cheaper than
// Base58 + strcmp because Base58 long-division is skipped entirely.
// Compare two hash160 entries (sort key = first uint32 word)
__device__ __forceinline__ int _CmpH160(const uint32_t *a, const uint32_t *b) {
    for (int i = 0; i < 5; i++) {
        if (a[i] < b[i]) return -1;
        if (a[i] > b[i]) return  1;
    }
    return 0;
}

// Bloom filter probe: returns true if h *might* be in the target set.
// Reads from d_bloom_filter in global memory (stays hot in L2 cache).
__device__ __forceinline__ bool _BloomCheck(const uint32_t *h) {
    uint32_t h1 = h[0] ^ (h[1] * 2654435761u);
    uint32_t bit1 = h1 % BLOOM_SIZE_BITS;
    if (!(d_bloom_filter[bit1 >> 5] & (1u << (bit1 & 31)))) return false;

    uint32_t h2 = h[2] ^ (h[3] * 2246822519u);
    uint32_t bit2 = h2 % BLOOM_SIZE_BITS;
    if (!(d_bloom_filter[bit2 >> 5] & (1u << (bit2 & 31)))) return false;

    uint32_t h3 = h[4] ^ (h[0] * 3266489917u);
    uint32_t bit3 = h3 % BLOOM_SIZE_BITS;
    if (!(d_bloom_filter[bit3 >> 5] & (1u << (bit3 & 31)))) return false;

    return true;
}

// Bloom-filtered binary search: fast reject via bloom filter, then confirm.
__device__ __forceinline__ int _MatchHash160(const uint32_t *h) {
    if (!_BloomCheck(h)) return -1;
    int lo = 0, hi = d_num_targets - 1;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        int c = _CmpH160(h, d_target_h160[mid]);
        if (c == 0) return mid;
        if (c < 0) hi = mid - 1; else lo = mid + 1;
    }
    return -1;
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

// Check uncompressed addresses (both Y and -Y) using shared-memory bloom filter.
// In direct mode: compute hash160 of uncompressed pubkey, bloom-check via shared mem.
// In legacy prefix mode: falls through to Base58 + prefix match (no bloom).
__device__ __noinline__ void CheckHashCompSymK4(
    uint64_t* px, uint64_t* py, uint32_t tid, int32_t incr,
    uint32_t maxFound, uint32_t* out
) {
    int matched_idx;

    if (d_direct_mode) {
        // Hash160-direct mode: uncompressed only (Y and -Y).
        // Computes hash160 of the full 65-byte uncompressed pubkey (04||x||y).
        // Skips compressed hash entirely — saves one _GetHash160CompSym call.
        uint32_t h_uncomp1[5], h_uncomp2[5];
        _GetHash160(px, py, (uint8_t*)h_uncomp1);
        matched_idx = _MatchHash160(h_uncomp1);
        if (matched_idx >= 0) OutputMatchK4(out, tid, incr, h_uncomp1, matched_idx, 2);

        uint64_t negY[4];
        ModNeg256(negY, py);
        _GetHash160(px, negY, (uint8_t*)h_uncomp2);
        matched_idx = _MatchHash160(h_uncomp2);
        if (matched_idx >= 0) OutputMatchK4(out, tid, -incr, h_uncomp2, matched_idx, 3);
        return;
    }

    // Legacy prefix-match mode needs compressed hashes.
    uint32_t h1[5], h2[5];
    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);

    // Legacy prefix-match mode: Base58 + also check uncompressed variants.
    char addr[40];
    uint32_t h_uncomp1[5], h_uncomp2[5];

    if (CheckVanityPatternsK4(h1, &matched_idx, addr)) {
        OutputMatchK4(out, tid, incr, h1, matched_idx, 0);
    }

    if (CheckVanityPatternsK4(h2, &matched_idx, addr)) {
        OutputMatchK4(out, tid, -incr, h2, matched_idx, 1);
    }

    // Uncompressed Y and -Y.
    _GetHash160(px, py, (uint8_t*)h_uncomp1);
    if (CheckVanityPatternsK4(h_uncomp1, &matched_idx, addr)) {
        OutputMatchK4(out, tid, incr, h_uncomp1, matched_idx, 2);
    }

    uint64_t negY[4];
    ModNeg256(negY, py);
    _GetHash160(px, negY, (uint8_t*)h_uncomp2);
    if (CheckVanityPatternsK4(h_uncomp2, &matched_idx, addr)) {
        OutputMatchK4(out, tid, -incr, h_uncomp2, matched_idx, 3);
    }
}

__device__ void ComputeKeysK4(
    uint64_t* dx_global, uint64_t* subp_global,
    uint32_t mode, uint64_t* startx, uint64_t* starty,
    uint32_t maxFound, uint32_t* out
) {
    // Cast global memory to 2D array pointers for dx and subp
    // These are allocated per-thread in global memory to avoid stack overflow
    uint64_t (*dx)[4] = (uint64_t (*)[4])dx_global;
    uint64_t (*subp)[4] = (uint64_t (*)[4])subp_global;

    uint64_t px[4], py[4], pyn[4], sx[4], sy[4], dy[4], _s[4], _p2[4];
    uint64_t zeroMask[(GRP_SIZE / 2 + 1 + 63) / 64];

    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;

    __syncthreads();
    Load256A(sx, startx);
    Load256A(sy, starty);
    Load256(px, sx);
    Load256(py, sy);

    for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {
        for (uint32_t z = 0; z < (GRP_SIZE / 2 + 1 + 63) / 64; z++) zeroMask[z] = 0ULL;
        uint32_t i;
        for (i = 0; i < HSIZE; i++) {
            ModSub256(dx[i], Gx[i], sx);
            if (IsZero256Dev(dx[i])) {
                zeroMask[i >> 6] |= (1ULL << (i & 63));
                SetOne256Dev(dx[i]);
            }
        }
        ModSub256(dx[i], Gx[i], sx);
        if (IsZero256Dev(dx[i])) {
            zeroMask[i >> 6] |= (1ULL << (i & 63));
            SetOne256Dev(dx[i]);
        }
        ModSub256(dx[i + 1], _2Gnx, sx);
        if (IsZero256Dev(dx[i + 1])) {
            zeroMask[(i + 1) >> 6] |= (1ULL << ((i + 1) & 63));
            SetOne256Dev(dx[i + 1]);
        }

        _ModInvGrouped(dx, subp);

        CheckHashCompSymK4(px, py, tid, j * GRP_SIZE + GRP_SIZE / 2, maxFound, out);

        ModNeg256(pyn, py);

        for (i = 0; i < HSIZE; i++) {
            bool special = ((zeroMask[i >> 6] >> (i & 63)) & 1ULL) != 0ULL;

            if (special) {
                uint64_t qx[4], qy[4];
                Load256(qx, Gx[i]);
                Load256(qy, Gy[i]);
                if (PointAddAffineDev(px, py, sx, sy, qx, qy)) {
                    CheckHashCompSymK4(px, py, tid, j * GRP_SIZE + GRP_SIZE / 2 + (i + 1), maxFound, out);
                }
            } else {
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
                CheckHashCompSymK4(px, py, tid, j * GRP_SIZE + GRP_SIZE / 2 + (i + 1), maxFound, out);
            }

            if (special) {
                uint64_t qx[4], qy[4];
                Load256(qx, Gx[i]);
                Load256(qy, Gy[i]);
                ModNeg256(qy, qy);
                if (PointAddAffineDev(px, py, sx, sy, qx, qy)) {
                    CheckHashCompSymK4(px, py, tid, j * GRP_SIZE + GRP_SIZE / 2 - (i + 1), maxFound, out);
                }
            } else {
                Load256(px, sx);
                Load256(py, sy);
                ModSub256(dy, pyn, Gy[i]);
                _ModMult(_s, dy, dx[i]);
                _ModSqr(_p2, _s);
                ModSub256(px, _p2, px);
                ModSub256(px, Gx[i]);
                ModSub256(py, Gx[i], px);
                _ModMult(py, _s);
                // Correct formula: new_y = _s*(Gx[i]-new_px) + Gy[i]
                // (not minus Gy[i] + negate, which gives wrong sign)
                { uint64_t _neg_gy[4]; Load256(_neg_gy, Gy[i]); ModNeg256(_neg_gy, _neg_gy); ModSub256(py, _neg_gy); }
                CheckHashCompSymK4(px, py, tid, j * GRP_SIZE + GRP_SIZE / 2 - (i + 1), maxFound, out);
            }
        }

        bool specialNeg512 = ((zeroMask[i >> 6] >> (i & 63)) & 1ULL) != 0ULL;
        if (specialNeg512) {
            uint64_t qx[4], qy[4];
            Load256(qx, Gx[i]);
            Load256(qy, Gy[i]);
            ModNeg256(qy, qy);
            if (PointAddAffineDev(px, py, sx, sy, qx, qy)) {
                CheckHashCompSymK4(px, py, tid, j * GRP_SIZE, maxFound, out);
            }
        } else {
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
            CheckHashCompSymK4(px, py, tid, j * GRP_SIZE, maxFound, out);
        }

        i++;
        bool specialPos512 = ((zeroMask[i >> 6] >> (i & 63)) & 1ULL) != 0ULL;
        if (specialPos512) {
            if (!PointAddAffineDev(px, py, sx, sy, _2Gnx, _2Gny)) {
                SetZero256Dev(px);
                SetZero256Dev(py);
            }
        } else {
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
            // Also check sx + GRP_SIZE/2 * G (offset +512, previously unchecked)
            {
                uint64_t hpx[4], hpy[4];
                Load256(hpx, sx);
                Load256(hpy, sy);
                uint64_t _hs[4], _hp2[4], _hdy[4];
                ModSub256(_hdy, Gy[HSIZE], hpy);
                _ModMult(_hs, _hdy, dx[HSIZE]);
                _ModSqr(_hp2, _hs);
                ModSub256(hpx, _hp2, hpx);
                ModSub256(hpx, Gx[HSIZE]);
                ModSub256(hpy, Gx[HSIZE], hpx);
                _ModMult(hpy, _hs);
                ModSub256(hpy, Gy[HSIZE]);
                CheckHashCompSymK4(hpx, hpy, tid, j * GRP_SIZE + GRP_SIZE, maxFound, out);
            }
        }
    }

    // For sequential mode: advance by the additional delta to reach (nbThread * STEP_SIZE) * G
    if (d_useSeqDelta) {
        uint64_t rxSeq[4], rySeq[4];
        if (PointAddAffineDev(rxSeq, rySeq, px, py, d_seqDeltaX, d_seqDeltaY)) {
            Load256(px, rxSeq);
            Load256(py, rySeq);
        } else {
            SetZero256Dev(px);
            SetZero256Dev(py);
        }
    }

    __syncthreads();
    Store256A(startx, px);
    Store256A(starty, py);
}

__global__ void searchK4_kernel(
    uint64_t* dx_buffer, uint64_t* subp_buffer,
    uint32_t mode, uint64_t* keys,
    uint32_t maxFound, uint32_t* found
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;

    // Each thread gets its own slice of the global dx and subp buffers
    // Array size per thread: (GRP_SIZE/2+1) * 4 uint64_t values
    size_t arraySize = (GRP_SIZE / 2 + 1) * 4;
    uint64_t* my_dx = dx_buffer + tid * arraySize;
    uint64_t* my_subp = subp_buffer + tid * arraySize;

    ComputeKeysK4(my_dx, my_subp, mode, keys + xPtr, keys + yPtr, maxFound, found);
}

// =====================================================================================
// HOST UTILITY FUNCTIONS
// =====================================================================================

// State file format for sequential mode (v2):
// [packed header with magic/version/thread metadata/checksum] [keys data...]
static bool peek_state_seq_header(const char* f, K4StateHeaderV2* header) {
    FILE* fp = fopen(f, "rb");
    if (!fp) return false;
    bool ok = fread(header, sizeof(*header), 1, fp) == 1;
    fclose(fp);
    if (!ok) return false;
    return memcmp(header->magic, K4_STATE_MAGIC, sizeof(header->magic)) == 0 &&
           header->version == K4_STATE_VERSION;
}

void save_state_seq(const char* f, uint64_t* k, int n, uint64_t t, uint64_t iter, const uint64_t* baseKey) {
    FILE* fp = fopen(f, "wb");
    if (!fp) {
        printf("Warning: Could not write state file: %s\n", f);
        return;
    }

    K4StateHeaderV2 header;
    memset(&header, 0, sizeof(header));
    memcpy(header.magic, K4_STATE_MAGIC, sizeof(header.magic));
    header.version = K4_STATE_VERSION;
    header.threadCount = (uint32_t)n;
    header.stepSize = STEP_SIZE;
    header.totalKeys = t;
    header.iter = iter;
    header.keysPerIter = (uint64_t)n * STEP_SIZE;
    memcpy(header.baseKey, baseKey, sizeof(header.baseKey));
    header.keyWords = (uint64_t)n * 8ULL;
    header.checksum = compute_state_checksum(&header, k);

    fwrite(&header, sizeof(header), 1, fp);
    fwrite(k, sizeof(uint64_t), (size_t)header.keyWords, fp);
    fclose(fp);
}

static bool load_state_seq(const char* f, uint64_t* k, int n, K4LoadedState* loaded) {
    memset(loaded, 0, sizeof(*loaded));

    struct stat st;
    if (stat(f, &st)) return false;

    FILE* fp = fopen(f, "rb");
    if (!fp) return false;

    K4StateHeaderV2 header;
    bool newFormat = fread(&header, sizeof(header), 1, fp) == 1 &&
                     memcmp(header.magic, K4_STATE_MAGIC, sizeof(header.magic)) == 0;

    if (newFormat) {
        if (header.version != K4_STATE_VERSION) {
            printf("Error: Unsupported state version in %s\n", f);
            fclose(fp);
            return false;
        }
        if (header.stepSize != STEP_SIZE) {
            printf("Error: State step size mismatch in %s\n", f);
            fclose(fp);
            return false;
        }
        if (header.threadCount != (uint32_t)n) {
            printf("Error: State thread count mismatch in %s (state=%u, requested=%d)\n",
                   f, header.threadCount, n);
            fclose(fp);
            return false;
        }
        if (header.keysPerIter != (uint64_t)n * STEP_SIZE) {
            printf("Error: State progress stride mismatch in %s\n", f);
            fclose(fp);
            return false;
        }
        if (header.totalKeys != header.iter * header.keysPerIter) {
            printf("Error: State progress counters are inconsistent in %s\n", f);
            fclose(fp);
            return false;
        }
        if (header.keyWords != (uint64_t)n * 8ULL) {
            printf("Error: State key buffer size mismatch in %s\n", f);
            fclose(fp);
            return false;
        }
        off_t expectedSize = (off_t)sizeof(header) + (off_t)header.keyWords * (off_t)sizeof(uint64_t);
        if (st.st_size != expectedSize) {
            printf("Error: State file size mismatch in %s\n", f);
            fclose(fp);
            return false;
        }
        if (fread(k, sizeof(uint64_t), (size_t)header.keyWords, fp) != (size_t)header.keyWords) {
            fclose(fp);
            return false;
        }
        uint64_t expectedChecksum = compute_state_checksum(&header, k);
        if (expectedChecksum != header.checksum) {
            printf("Error: State checksum mismatch in %s\n", f);
            fclose(fp);
            return false;
        }
        if (!is_private_key_in_range(header.baseKey)) {
            printf("Error: Invalid base key in state file %s\n", f);
            fclose(fp);
            return false;
        }

        loaded->totalKeys = header.totalKeys;
        loaded->iter = header.iter;
        memcpy(loaded->baseKey, header.baseKey, sizeof(loaded->baseKey));
        loaded->threadCount = header.threadCount;
        loaded->keysPerIter = header.keysPerIter;
        loaded->legacyFormat = false;
        fclose(fp);
        return true;
    }

    rewind(fp);
    uint64_t totalKeys = 0;
    uint64_t baseKey[4] = {0};
    size_t keyWords = (size_t)n * 8U;
    off_t expectedLegacySize = (off_t)8 + (off_t)(4 * sizeof(uint64_t)) + (off_t)keyWords * (off_t)sizeof(uint64_t);
    if (st.st_size != expectedLegacySize) {
        fclose(fp);
        return false;
    }
    if (fread(&totalKeys, sizeof(totalKeys), 1, fp) != 1 ||
        fread(baseKey, sizeof(uint64_t), 4, fp) != 4 ||
        fread(k, sizeof(uint64_t), keyWords, fp) != keyWords) {
        fclose(fp);
        return false;
    }
    fclose(fp);

    if (!is_private_key_in_range(baseKey)) {
        printf("Error: Invalid base key in legacy state file %s\n", f);
        return false;
    }

    uint64_t keysPerIter = (uint64_t)n * STEP_SIZE;
    if (keysPerIter == 0 || (totalKeys % keysPerIter) != 0) {
        printf("Error: Legacy state %s has inconsistent progress metadata\n", f);
        return false;
    }

    loaded->totalKeys = totalKeys;
    loaded->iter = totalKeys / keysPerIter;
    memcpy(loaded->baseKey, baseKey, sizeof(loaded->baseKey));
    loaded->threadCount = (uint32_t)n;
    loaded->keysPerIter = keysPerIter;
    loaded->legacyFormat = true;
    return true;
}

// Initialize keys sequentially from a starting point
// Optimized: compute baseKey*G once, then add G repeatedly for sequential keys
// =====================================================================================
// FAST KEY INITIALIZATION using Montgomery batch inversion + precomputed G table
// =====================================================================================

// Montgomery batch inversion: given [a0, a1, ..., an-1], compute [a0^-1, a1^-1, ..., an-1^-1]
// Uses (3n-3) multiplications + 1 inversion instead of n inversions
// Zero inputs are tolerated and produce a zero output so callers can special-case them.
static void batch_mod_inv(uint64_t* results, uint64_t* inputs, int n) {
    if (n <= 0) return;

    memset(results, 0, (size_t)n * 32);

    int* nz = (int*)malloc((size_t)n * sizeof(int));
    uint64_t* partials = (uint64_t*)malloc((size_t)n * 32);
    if (!nz || !partials) {
        free(nz);
        free(partials);
        return;
    }

    int m = 0;
    for (int i = 0; i < n; i++) {
        if (!is_zero256_host(&inputs[i * 4])) nz[m++] = i;
    }

    if (m == 0) {
        free(nz);
        free(partials);
        return;
    }

    memcpy(&partials[0], &inputs[nz[0] * 4], 32);
    for (int i = 1; i < m; i++) {
        mod_mul(&partials[i * 4], &partials[(i - 1) * 4], &inputs[nz[i] * 4]);
    }

    uint64_t running_inv[4];
    mod_inv(running_inv, &partials[(m - 1) * 4]);

    for (int i = m - 1; i > 0; i--) {
        mod_mul(&results[nz[i] * 4], running_inv, &partials[(i - 1) * 4]);
        uint64_t tmp[4];
        mod_mul(tmp, running_inv, &inputs[nz[i] * 4]);
        memcpy(running_inv, tmp, 32);
    }
    memcpy(&results[nz[0] * 4], running_inv, 32);

    free(nz);
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

static bool configure_sequential_delta(int nbThread) {
    uint64_t seqDeltaX[4] = {0, 0, 0, 0};
    uint64_t seqDeltaY[4] = {0, 0, 0, 0};
    int useSeq = (nbThread > 1) ? 1 : 0;

    if (useSeq) {
        uint64_t delta_scalar[4] = {0, 0, 0, 0};
        delta_scalar[0] = (uint64_t)(nbThread - 1) * STEP_SIZE;
        scalar_mult_G(seqDeltaX, seqDeltaY, delta_scalar);
    }

    cudaError_t err = cudaMemcpyToSymbol(d_seqDeltaX, seqDeltaX, sizeof(seqDeltaX));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying seqDeltaX: %s\n", cudaGetErrorString(err));
        return false;
    }
    err = cudaMemcpyToSymbol(d_seqDeltaY, seqDeltaY, sizeof(seqDeltaY));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying seqDeltaY: %s\n", cudaGetErrorString(err));
        return false;
    }
    err = cudaMemcpyToSymbol(d_useSeqDelta, &useSeq, sizeof(useSeq));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying useSeqDelta: %s\n", cudaGetErrorString(err));
        return false;
    }
    return true;
}

bool init_keys_from_start(uint64_t* h_keys, int nbThread, const char* startStr, bool isHex) {
    printf("Initializing %d threads for SEQUENTIAL range search...\n", nbThread);

    char parseErr[128];
    if (!parse_start_key(startStr, isHex, g_baseKey, parseErr, sizeof(parseErr))) {
        printf("Error: Invalid start key: %s\n", parseErr);
        return false;
    }

    char hexStr[65];
    format_256bit_hex(g_baseKey, hexStr);
    printf("  Start: 0x%s\n", hexStr);

    uint64_t p0x[4], p0y[4];
    scalar_mult_G(p0x, p0y, g_baseKey);

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
        g_nbThread = nbThread;
        return true;
    }

    const int BATCH_SIZE = 8192;
    int remaining = nbThread - 1;
    int processed = 1;

    uint64_t* dx_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint64_t* inv_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint64_t* iGx_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint64_t* iGy_batch = (uint64_t*)malloc(BATCH_SIZE * 32);
    uint8_t* special_case = (uint8_t*)malloc(BATCH_SIZE);

    if (!dx_batch || !inv_batch || !iGx_batch || !iGy_batch || !special_case) {
        printf("Error: Failed to allocate initialization buffers\n");
        free(dx_batch);
        free(inv_batch);
        free(iGx_batch);
        free(iGy_batch);
        free(special_case);
        return false;
    }

    time_t start_time = time(NULL);

    while (remaining > 0) {
        int batch = (remaining < BATCH_SIZE) ? remaining : BATCH_SIZE;
        memset(special_case, 0, (size_t)batch);

        for (int i = 0; i < batch; i++) {
            uint64_t offset = (uint64_t)(processed + i) * STEP_SIZE;
            get_iG(&iGx_batch[i * 4], &iGy_batch[i * 4], offset);
            mod_sub(&dx_batch[i * 4], &iGx_batch[i * 4], p0x);
            if (is_zero256_host(&dx_batch[i * 4])) {
                special_case[i] = 1;
            }
        }

        batch_mod_inv(inv_batch, dx_batch, batch);

        for (int i = 0; i < batch; i++) {
            int t = processed + i;
            uint64_t offset = (uint64_t)t * STEP_SIZE;

            uint64_t *iGx = &iGx_batch[i * 4];
            uint64_t *iGy = &iGy_batch[i * 4];
            uint64_t rx[4], ry[4];

            if (special_case[i]) {
                uint64_t threadKey[4];
                add_mod_n_scalar(threadKey, g_baseKey, offset);
                if (is_zero256_host(threadKey)) {
                    printf("Error: Thread %d would start at invalid private key 0; choose a different start or thread count.\n", t);
                    free(dx_batch);
                    free(inv_batch);
                    free(iGx_batch);
                    free(iGy_batch);
                    free(special_case);
                    return false;
                }
                scalar_mult_G(rx, ry, threadKey);
            } else {
                uint64_t *inv_dx = &inv_batch[i * 4];
                uint64_t dy[4], s[4], s2[4], tmp[4];
                mod_sub(dy, iGy, p0y);
                mod_mul(s, dy, inv_dx);
                mod_mul(s2, s, s);
                mod_sub(rx, s2, p0x);
                mod_sub(rx, rx, iGx);
                mod_sub(tmp, p0x, rx);
                mod_mul(ry, s, tmp);
                mod_sub(ry, ry, p0y);
            }

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
    free(special_case);

    double elapsed = difftime(time(NULL), start_time);
    if (elapsed < 1) elapsed = 1;
    printf("\n  Done! %d threads in %.1fs (%.0f threads/sec)\n", nbThread, elapsed, nbThread / elapsed);

    g_nbThread = nbThread;
    return true;
}

// Reconstruct private key from match info
// parity: 0=even compressed, 1=odd compressed, 2=uncompressed, 3=uncompressed negated Y
bool reconstruct_privkey(uint64_t* privkey, uint32_t tid, int32_t incr, uint64_t iter, uint8_t parity) {
    int32_t actualIncr = (parity == 1 || parity == 3) ? -incr : incr;
    int32_t keyOffset = actualIncr - (GRP_SIZE / 2);

    uint64_t basePrivkey[4];
    memcpy(basePrivkey, g_baseKey, sizeof(basePrivkey));

    add_mod_n_scalar(basePrivkey, basePrivkey, (uint64_t)tid * STEP_SIZE);

    uint64_t iterOffset[4];
    mul_u64_u64_mod_n(iterOffset, (uint64_t)g_nbThread * STEP_SIZE, iter);
    add_mod_n(basePrivkey, basePrivkey, iterOffset);

    if (keyOffset >= 0) {
        add_mod_n_scalar(basePrivkey, basePrivkey, (uint64_t)keyOffset);
    } else {
        uint64_t tmp[4] = {(uint64_t)(-keyOffset), 0, 0, 0};
        sub_mod_n(basePrivkey, basePrivkey, tmp);
    }

    if (is_zero256_host(basePrivkey)) {
        return false;
    }

    if (parity == 2) {
        memcpy(privkey, basePrivkey, 32);
        return true;
    }

    if (parity == 3) {
        sub256(privkey, SECP_N, basePrivkey);
        return !is_zero256_host(privkey);
    }

    uint64_t px[4], py[4];
    scalar_mult_G(px, py, basePrivkey);
    bool actualYOdd = (py[0] & 1) != 0;
    bool reportedOdd = (parity == 1);

    if (actualYOdd == reportedOdd) {
        memcpy(privkey, basePrivkey, 32);
    } else {
        sub256(privkey, SECP_N, basePrivkey);
    }

    return !is_zero256_host(privkey) && cmp256(privkey, SECP_N) < 0;
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

// RIPEMD-160 provided by ripemd160.c / ripemd160.h (linked in via Makefile).
// The external drop-in is verified against the 9 published test vectors
// including the 1-million-"a" stress vector, and against the Puzzle #1
// end-to-end check. It uses calloc for the padded buffer, so it doesn't
// have the fixed-128-byte buffer trap that an inline version would.

static void pubkey_to_hash160_host(const uint64_t* px, const uint64_t* py, bool compressed, uint8_t* hash160) {
    uint8_t pubkey[65];
    size_t pubkeyLen = compressed ? 33 : 65;

    if (compressed) {
        pubkey[0] = (py[0] & 1ULL) ? 0x03 : 0x02;
        for (int i = 0; i < 32; i++) pubkey[1 + i] = ((const uint8_t*)px)[31 - i];
    } else {
        pubkey[0] = 0x04;
        for (int i = 0; i < 32; i++) {
            pubkey[1 + i] = ((const uint8_t*)px)[31 - i];
            pubkey[33 + i] = ((const uint8_t*)py)[31 - i];
        }
    }

    uint8_t sha[32];
    sha256_host(pubkey, pubkeyLen, sha);
    ripemd160(sha, sizeof(sha), hash160);
}

void hash160_to_address_host(const uint8_t* hash160, char* addr);

static bool derive_address_from_privkey(const uint64_t* privkey, bool compressed, uint8_t* hash160, char* addr) {
    if (!is_private_key_in_range(privkey)) return false;
    uint64_t px[4], py[4];
    scalar_mult_G(px, py, privkey);
    pubkey_to_hash160_host(px, py, compressed, hash160);
    hash160_to_address_host(hash160, addr);
    return true;
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

// Base58Check-decode a Bitcoin P2PKH address into its 20-byte hash160.
// Returns true on success, false if the address is malformed, version byte
// is not mainnet P2PKH (0x00), or the double-SHA256 checksum fails.
static bool address_to_hash160_host(const char* addr, uint8_t* out20) {
    static const int8_t b58map[128] = {
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,
        -1, 0, 1, 2, 3, 4, 5, 6, 7, 8,-1,-1,-1,-1,-1,-1,
        -1, 9,10,11,12,13,14,15,16,-1,17,18,19,20,21,-1,
        22,23,24,25,26,27,28,29,30,31,32,-1,-1,-1,-1,-1,
        -1,33,34,35,36,37,38,39,40,41,42,43,-1,44,45,46,
        47,48,49,50,51,52,53,54,55,56,57,-1,-1,-1,-1,-1
    };

    int addrLen = (int)strlen(addr);
    if (addrLen < 26 || addrLen > 35) return false;

    int zeros = 0;
    while (zeros < addrLen && addr[zeros] == '1') zeros++;

    uint8_t decoded[32] = {0};
    int decLen = 0;

    for (int i = zeros; i < addrLen; i++) {
        unsigned char c = (unsigned char)addr[i];
        if (c >= 128) return false;
        int8_t v = b58map[c];
        if (v < 0) return false;
        int carry = v;
        for (int j = 0; j < decLen; j++) {
            carry += (int)decoded[j] * 58;
            decoded[j] = carry & 0xFF;
            carry >>= 8;
        }
        while (carry) {
            if (decLen >= 32) return false;
            decoded[decLen++] = carry & 0xFF;
            carry >>= 8;
        }
    }

    uint8_t result[32] = {0};
    int rlen = zeros + decLen;
    if (rlen != 25) return false;  // P2PKH decodes to exactly 25 bytes
    for (int i = 0; i < decLen; i++) result[zeros + (decLen - 1 - i)] = decoded[i];

    if (result[0] != 0x00) return false;  // mainnet P2PKH version byte

    // Verify checksum (first 4 bytes of SHA256(SHA256(payload))).
    uint8_t sha1[32], sha2[32];
    sha256_host(result, 21, sha1);
    sha256_host(sha1, 32, sha2);
    if (memcmp(result + 21, sha2, 4) != 0) return false;

    memcpy(out20, result + 1, 20);
    return true;
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

        if (len > K4_PATTERN_MAX_LEN) {
            printf("Warning: Skipping pattern longer than %d chars: %s\n", K4_PATTERN_MAX_LEN, line);
            continue;
        }

        strncpy(patterns[count], line, K4_PATTERN_MAX_LEN);
        patterns[count][K4_PATTERN_MAX_LEN] = '\0';
        lens[count] = len;

        printf("Pattern %d: %s (len=%d)\n", count, patterns[count], lens[count]);
        count++;
    }

    fclose(f);
    return count;
}

void print_usage(const char* prog) {
    printf("SearchK4 - GPU sequential key search (vanity prefix OR hash160-direct puzzle mode)\n\n");
    printf("Usage: %s -patterns <file> (-start <dec> | -startx <hex> | -bits N | -state <file>) [options]\n\n", prog);
    printf("Required:\n");
    printf("  -patterns <file>   Pattern file (prefixes in legacy mode, full addresses in -direct mode)\n");
    printf("  -start  <decimal>  Starting private key (decimal)    \\\n");
    printf("  -startx <hex>      Starting private key (hex, 0x ok)  | One REQUIRED unless\n");
    printf("  -bits   <N>        Shortcut range [2^(N-1), 2^N - 1]  | resuming via -state.\n");
    printf("  -state  <file>     Resume from state file            /\n\n");
    printf("Mode:\n");
    printf("  -direct            Hash160-direct match. Requires full P2PKH addresses in\n");
    printf("                     -patterns. Skips Base58 + uncompressed checks. ~30-40%%\n");
    printf("                     faster than prefix mode. Recommended for puzzle solving.\n\n");
    printf("Range clamping (strongly recommended for puzzle work):\n");
    printf("  -endx <hex>        Last private key to search (inclusive). Scan ends cleanly\n");
    printf("                     when the range is exhausted.\n");
    printf("  -bits <N>          Convenience: expands to -startx 2^(N-1), -endx 2^N-1.\n");
    printf("                     E.g. -bits 71 targets Puzzle #71's exact range.\n\n");
    printf("Other:\n");
    printf("  -gpu <id>          GPU device ID (default: 0)\n");
    printf("  -threads <N>       Thread count. Must be >=64 and a multiple of 64.\n");
    printf("                     Defaults: 16384 in -direct mode, 1024 in prefix mode.\n");
    printf("                     If -state is given and -threads omitted, restored from state.\n");
    printf("  -o <file>          Output file (default: found_k4_gpu<id>.txt)\n");
    printf("  -verbose           Per-iteration progress logs\n");
    printf("  -h, --help         Show this help\n\n");
    printf("Correctness guarantees:\n");
    printf("  * State files are checksummed and versioned. Resume restores iter so that\n");
    printf("    reconstructed private keys are correct on the first post-resume match.\n");
    printf("  * Every match is re-verified on the host (scalar_mult_G + SHA-256 +\n");
    printf("    RIPEMD-160 + Base58) before being written. Mismatches log as UNVERIFIED.\n\n");
    printf("Examples:\n");
    printf("  # Smoke test: Puzzle #1 (key = 1, address 1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH)\n");
    printf("  %s -patterns puzzle1.txt -direct -bits 1 -threads 64\n\n", prog);
    printf("  # Puzzle #71, direct mode, single GPU:\n");
    printf("  %s -patterns patterns.txt -direct -bits 71 -gpu 0\n\n", prog);
    printf("  # Four-GPU split of Puzzle #71 by quarters:\n");
    printf("  %s -patterns p.txt -direct -gpu 0 -startx 0x400000000000000000 -endx 0x4FFFFFFFFFFFFFFFFF\n", prog);
    printf("  %s -patterns p.txt -direct -gpu 1 -startx 0x500000000000000000 -endx 0x5FFFFFFFFFFFFFFFFF\n", prog);
    printf("  %s -patterns p.txt -direct -gpu 2 -startx 0x600000000000000000 -endx 0x6FFFFFFFFFFFFFFFFF\n", prog);
    printf("  %s -patterns p.txt -direct -gpu 3 -startx 0x700000000000000000 -endx 0x7FFFFFFFFFFFFFFFFF\n\n", prog);
    printf("  # Resume after interruption (reads threads + iter from state file):\n");
    printf("  %s -patterns patterns.txt -direct -state gpu0.state -bits 71\n\n", prog);
}

int main(int argc, char** argv) {
    char* patternsFile = NULL;
    char* stateFile = NULL;
    char* outputFile = NULL;
    bool outputSpecified = false;
    char* startDecimal = NULL;
    char* startHex = NULL;
    char* endHex = NULL;
    int gpuId = 0;
    int threadCount = 0;  // 0 = use default or state metadata
    int directMode = 0;
    int bits = 0;
    int verbose = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-patterns") && i + 1 < argc) patternsFile = argv[++i];
        else if (!strcmp(argv[i], "-gpu") && i + 1 < argc) gpuId = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-state") && i + 1 < argc) stateFile = argv[++i];
        else if (!strcmp(argv[i], "-o") && i + 1 < argc) { outputFile = argv[++i]; outputSpecified = true; }
        else if (!strcmp(argv[i], "-start") && i + 1 < argc) startDecimal = argv[++i];
        else if (!strcmp(argv[i], "-startx") && i + 1 < argc) startHex = argv[++i];
        else if (!strcmp(argv[i], "-endx") && i + 1 < argc) endHex = argv[++i];
        else if (!strcmp(argv[i], "-bits") && i + 1 < argc) bits = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-threads") && i + 1 < argc) threadCount = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-direct")) directMode = 1;
        else if (!strcmp(argv[i], "-verbose")) verbose = 1;
        else if (!strcmp(argv[i], "-h") || !strcmp(argv[i], "--help")) {
            print_usage(argv[0]);
            return 0;
        } else {
            printf("Error: Unknown or incomplete option: %s\n\n", argv[i]);
            print_usage(argv[0]);
            return 1;
        }
    }

    if (!patternsFile) {
        print_usage(argv[0]);
        return 1;
    }
    if (startDecimal && startHex) {
        printf("Error: Use either -start or -startx, not both.\n");
        return 1;
    }

    // -bits N shortcut: range [2^(N-1), 2^N - 1]. Does not override explicit
    // -startx/-endx if the user passed them. Used as the canonical puzzle
    // configuration entry: -bits 71 selects Puzzle #71's exact range.
    static char bitsStart[80], bitsEnd[80];
    if (bits > 0) {
        if (bits > 256) {
            printf("Error: -bits must be in [1, 256] (got %d)\n", bits);
            return 1;
        }
        uint64_t bsk[4] = {0};
        uint64_t bek[4] = {0};
        int lowBit = bits - 1;
        bsk[lowBit / 64] = 1ULL << (lowBit % 64);
        for (int b = 0; b < bits; b++) bek[b / 64] |= 1ULL << (b % 64);
        snprintf(bitsStart, sizeof(bitsStart), "%016lx%016lx%016lx%016lx",
                 bsk[3], bsk[2], bsk[1], bsk[0]);
        snprintf(bitsEnd, sizeof(bitsEnd), "%016lx%016lx%016lx%016lx",
                 bek[3], bek[2], bek[1], bek[0]);
        if (!startHex && !startDecimal) startHex = bitsStart;
        if (!endHex) endHex = bitsEnd;
        printf("-bits %d: range [0x%s .. 0x%s]\n", bits, bitsStart, bitsEnd);
    } else if (bits < 0) {
        printf("Error: -bits must be in [1, 256] (got %d)\n", bits);
        return 1;
    }

    // Load patterns
    char h_patterns[K4_MAX_TARGETS][36];
    int h_lens[K4_MAX_TARGETS];
    memset(h_patterns, 0, sizeof(h_patterns));
    memset(h_lens, 0, sizeof(h_lens));
    int numPatterns = load_patterns(patternsFile, h_patterns, h_lens, K4_MAX_TARGETS);
    if (numPatterns == 0) {
        printf("Error: No valid patterns loaded\n");
        return 1;
    }
    printf("Loaded %d patterns\n\n", numPatterns);

    char defaultState[256];
    if (!stateFile) {
        snprintf(defaultState, sizeof(defaultState), "gpu%d.state", gpuId);
        stateFile = defaultState;
    }

    char defaultOutput[256];
    if (!outputSpecified) {
        snprintf(defaultOutput, sizeof(defaultOutput), "found_k4_gpu%d.txt", gpuId);
        outputFile = defaultOutput;
    }

    if (threadCount == 0 && !startDecimal && !startHex) {
        K4StateHeaderV2 header;
        if (peek_state_seq_header(stateFile, &header)) {
            threadCount = (int)header.threadCount;
            printf("Using thread count %d from state header\n", threadCount);
        }
    }

    // Default threads: 1024 in legacy prefix mode, 393216 in direct mode.
    // Higher thread count improves latency hiding and occupancy with the
    // reduced 2KB stack (was 36KB). Benchmarked optimal on RTX 5080.
    int defaultThreads = directMode ? 393216 : 1024;
    int nbThread = (threadCount > 0) ? threadCount : defaultThreads;
    if (nbThread < NB_THREAD_PER_GROUP || (nbThread % NB_THREAD_PER_GROUP) != 0) {
        printf("Error: -threads must be at least %d and a multiple of %d.\n",
               NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP);
        return 1;
    }
    g_nbThread = nbThread;

    signal(SIGINT, sighandler);
    signal(SIGTERM, sighandler);
    cudaSetDevice(gpuId);

    // Stack size: kernel uses ~1104 bytes (measured by nvcc). 2KB gives headroom.
    // Previous 36KB was set for combined compressed+uncompressed paths (now removed).
    cudaDeviceSetLimit(cudaLimitStackSize, 2 * 1024);

    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, gpuId);
    printf("GPU %d: %s (SM %d.%d, %d MPs)\n", gpuId, prop.name, prop.major, prop.minor, prop.multiProcessorCount);

    // Copy patterns to GPU constant memory (only in legacy prefix mode;
    // direct mode uses hash160 tables in global memory instead).
    cudaError_t err;
    if (!directMode) {
        int copyCount = (numPatterns <= K4_MAX_PATTERNS) ? numPatterns : K4_MAX_PATTERNS;
        err = cudaMemcpyToSymbol(d_patterns, h_patterns, copyCount * 36);
        if (err != cudaSuccess) {
            printf("CUDA ERROR copying patterns: %s\n", cudaGetErrorString(err));
            return 1;
        }
        err = cudaMemcpyToSymbol(d_pattern_lens, h_lens, copyCount * sizeof(int));
        if (err != cudaSuccess) {
            printf("CUDA ERROR copying pattern lengths: %s\n", cudaGetErrorString(err));
            return 1;
        }
        err = cudaMemcpyToSymbol(d_num_patterns, &copyCount, sizeof(int));
        if (err != cudaSuccess) {
            printf("CUDA ERROR copying num_patterns: %s\n", cudaGetErrorString(err));
            return 1;
        }
        printf("Successfully copied %d patterns to GPU constant memory\n", copyCount);
    } else {
        int zero = 0;
        cudaMemcpyToSymbol(d_num_patterns, &zero, sizeof(int));
        printf("Direct mode: skipping legacy pattern copy (%d patterns)\n", numPatterns);
    }

    // If -direct, decode each pattern as a full address into its hash160.
    // Any pattern that doesn't decode as a valid mainnet P2PKH address is
    // rejected with a warning. A file with only prefixes produces zero
    // targets and the program exits before any scan starts.
    int numTargets = 0;
    if (directMode) {
        uint32_t h_targets[K4_MAX_TARGETS][5];
        memset(h_targets, 0, sizeof(h_targets));
        for (int i = 0; i < numPatterns; i++) {
            uint8_t hash160[20];
            if (!address_to_hash160_host(h_patterns[i], hash160)) {
                printf("Warning: -direct mode skipping non-address pattern: %s\n", h_patterns[i]);
                continue;
            }
            for (int w = 0; w < 5; w++) {
                h_targets[numTargets][w] =
                    ((uint32_t)hash160[w * 4 + 0])       |
                    ((uint32_t)hash160[w * 4 + 1]) << 8  |
                    ((uint32_t)hash160[w * 4 + 2]) << 16 |
                    ((uint32_t)hash160[w * 4 + 3]) << 24;
            }
            numTargets++;
        }
        if (numTargets == 0) {
            printf("Error: -direct mode requires at least one full P2PKH address in -patterns\n");
            return 1;
        }
        // Sort for binary search in kernel
        qsort(h_targets, numTargets, 5 * sizeof(uint32_t), cmp_h160_host);
        void* d_ptr_h160 = nullptr;
        cudaGetSymbolAddress(&d_ptr_h160, d_target_h160);
        err = cudaMemcpy(d_ptr_h160, h_targets, numTargets * 5 * sizeof(uint32_t), cudaMemcpyHostToDevice);
        if (err != cudaSuccess) {
            printf("CUDA ERROR copying target hash160s: %s\n", cudaGetErrorString(err));
            return 1;
        }
        err = cudaMemcpyToSymbol(d_num_targets, &numTargets, sizeof(int));
        if (err != cudaSuccess) {
            printf("CUDA ERROR copying num_targets: %s\n", cudaGetErrorString(err));
            return 1;
        }
        printf("Direct mode: %d uncompressed hash160 targets uploaded\n", numTargets);

        // Build and upload bloom filter for fast pre-screening on the GPU.
        {
            static uint32_t h_bloom[BLOOM_SIZE_U32];
            memset(h_bloom, 0, sizeof(h_bloom));
            for (int i = 0; i < numTargets; i++) {
                uint32_t hv1 = h_targets[i][0] ^ (h_targets[i][1] * 2654435761u);
                uint32_t bit1 = hv1 % BLOOM_SIZE_BITS;
                h_bloom[bit1 >> 5] |= (1u << (bit1 & 31));

                uint32_t hv2 = h_targets[i][2] ^ (h_targets[i][3] * 2246822519u);
                uint32_t bit2 = hv2 % BLOOM_SIZE_BITS;
                h_bloom[bit2 >> 5] |= (1u << (bit2 & 31));

                uint32_t hv3 = h_targets[i][4] ^ (h_targets[i][0] * 3266489917u);
                uint32_t bit3 = hv3 % BLOOM_SIZE_BITS;
                h_bloom[bit3 >> 5] |= (1u << (bit3 & 31));
            }
            void* d_ptr_bloom = nullptr;
            cudaGetSymbolAddress(&d_ptr_bloom, d_bloom_filter);
            err = cudaMemcpy(d_ptr_bloom, h_bloom, sizeof(h_bloom), cudaMemcpyHostToDevice);
            if (err != cudaSuccess) {
                printf("CUDA ERROR copying bloom filter: %s\n", cudaGetErrorString(err));
                return 1;
            }
            int bitsSet = 0;
            for (int i = 0; i < BLOOM_SIZE_U32; i++) {
                bitsSet += __builtin_popcount(h_bloom[i]);
            }
            printf("Direct mode: bloom filter uploaded (%d/%d bits set, %.2f%% fill)\n",
                   bitsSet, BLOOM_SIZE_BITS, 100.0 * bitsSet / BLOOM_SIZE_BITS);
        }
    } else {
        int zero = 0;
        cudaMemcpyToSymbol(d_num_targets, &zero, sizeof(int));
    }
    err = cudaMemcpyToSymbol(d_direct_mode, &directMode, sizeof(int));
    if (err != cudaSuccess) {
        printf("CUDA ERROR copying direct_mode: %s\n", cudaGetErrorString(err));
        return 1;
    }

    // Range-end clamping. If -endx was supplied (directly or via -bits),
    // upload it to a device constant. The host checks between iterations
    // whether the covered range has passed it; the kernel is branch-free.
    uint64_t endKey[4] = {0};
    int haveEndx = 0;
    if (endHex) {
        char parseErr[160];
        if (!hex_to_256bit(endHex, endKey, parseErr, sizeof(parseErr))) {
            printf("Error: -endx parse failed: %s\n", parseErr);
            return 1;
        }
        if (is_zero256_host(endKey) || cmp256(endKey, SECP_N) >= 0) {
            printf("Error: -endx must be in [1, N-1]\n");
            return 1;
        }
        haveEndx = 1;
        char ehex[65];
        format_256bit_hex(endKey, ehex);
        printf("Range end: 0x%s (inclusive)\n", ehex);
    }
    cudaMemcpyToSymbol(d_endKey, endKey, 32);
    cudaMemcpyToSymbol(d_have_endx, &haveEndx, sizeof(int));

    printf("Using %d threads (mode: %s)\n", nbThread, directMode ? "direct" : "prefix");
    uint64_t* d_keys;
    uint32_t* d_found;
    uint64_t* d_dx;     // Global memory for dx arrays (avoids stack overflow)
    uint64_t* d_subp;   // Global memory for subp arrays (avoids stack overflow)

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

    // Allocate global memory for dx and subp arrays to avoid stack overflow
    // Each thread needs (GRP_SIZE/2+1) * 4 uint64_t values = 513 * 4 * 8 = 16416 bytes
    size_t dxSize = (size_t)nbThread * (GRP_SIZE / 2 + 1) * 4 * sizeof(uint64_t);
    printf("Allocating dx buffer: %zu bytes (%.2f MB)\n", dxSize, dxSize / 1048576.0);
    err = cudaMalloc(&d_dx, dxSize);
    if (err != cudaSuccess) {
        printf("CUDA ERROR allocating d_dx: %s\n", cudaGetErrorString(err));
        return 1;
    }
    err = cudaMalloc(&d_subp, dxSize);
    if (err != cudaSuccess) {
        printf("CUDA ERROR allocating d_subp: %s\n", cudaGetErrorString(err));
        return 1;
    }
    printf("Allocated global memory for dx and subp arrays\n");

    uint64_t* h_keys = (uint64_t*)malloc(nbThread * 64);
    K4LoadedState loadedState;
    memset(&loadedState, 0, sizeof(loadedState));

    if (!h_keys) {
        printf("Error: Failed to allocate host key buffer\n");
        cudaFree(d_keys);
        cudaFree(d_found);
        cudaFree(d_dx);
        cudaFree(d_subp);
        return 1;
    }

    // Initialize keys - SEQUENTIAL MODE ONLY (random mode disabled)
    if (startDecimal || startHex) {
        const char* startStr = startHex ? startHex : startDecimal;
        bool isHex = (startHex != NULL);
        if (!init_keys_from_start(h_keys, nbThread, startStr, isHex)) {
            free(h_keys);
            cudaFree(d_keys);
            cudaFree(d_found);
            cudaFree(d_dx);
            cudaFree(d_subp);
            return 1;
        }
    } else {
        if (load_state_seq(stateFile, h_keys, nbThread, &loadedState)) {
            memcpy(g_baseKey, loadedState.baseKey, sizeof(g_baseKey));
                g_nbThread = nbThread;
            char hexStr[65];
            format_256bit_hex(g_baseKey, hexStr);
            printf("Resumed SEQUENTIAL from %.2fB keys\n", loadedState.totalKeys / 1e9);
            printf("  Base key: 0x%s\n", hexStr);
            printf("  Iteration: %lu\n", loadedState.iter);
            if (loadedState.legacyFormat) {
                printf("  Loaded legacy state format; it will be upgraded on next save.\n");
            }
        } else {
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
            cudaFree(d_dx);
            cudaFree(d_subp);
            return 1;
        }
    }

    if (!configure_sequential_delta(nbThread)) {
        free(h_keys);
        cudaFree(d_keys);
        cudaFree(d_found);
        cudaFree(d_dx);
        cudaFree(d_subp);
        return 1;
    }

    printf("Copying keys to device...\n"); fflush(stdout);
    cudaMemcpy(d_keys, h_keys, nbThread * 64, cudaMemcpyHostToDevice);
    printf("Keys copied\n"); fflush(stdout);

    uint32_t* h_found;
    printf("Allocating h_found...\n"); fflush(stdout);
    cudaMallocHost(&h_found, (1 + MAX_FOUND * 8) * 4);
    printf("h_found allocated\n"); fflush(stdout);

    printf("\nMode: SEQUENTIAL (range search)\n"); fflush(stdout);
    printf("Running: %d threads, %d patterns\n", nbThread, numPatterns); fflush(stdout);
    printf("Output: %s\n\n", outputFile); fflush(stdout);

    time_t start = time(NULL);
    uint64_t total = loadedState.totalKeys;
    uint64_t iter = loadedState.iter;

    while (running) {
        cudaMemset(d_found, 0, 4);
        searchK4_kernel<<<nbThread / NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP>>>(
            d_dx, d_subp, 0, d_keys, MAX_FOUND, d_found);
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
            if (!mf) {
                printf("\nError: Could not open output file %s for append.\n", outputFile);
                continue;
            }
            time_t now = time(NULL);
            char* timestr = ctime(&now);
            timestr[strlen(timestr)-1] = '\0';
            uint32_t verifiedCount = 0;

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

                uint64_t privkey[4];
                bool isCompressed = (isOdd == 0 || isOdd == 1);  // parity 0,1 = compressed, 2,3 = uncompressed
                if (!reconstruct_privkey(privkey, tid, incr, iter, isOdd)) {
                    printf("  [warn] Skipping invalid reconstructed key for tid=%u incr=%d parity=%u iter=%lu\n",
                           tid, incr, isOdd, iter);
                    continue;
                }

                uint8_t verifiedHash160[20];
                char verifiedAddr[40];
                if (!derive_address_from_privkey(privkey, isCompressed, verifiedHash160, verifiedAddr) ||
                    memcmp(verifiedHash160, hash160, sizeof(verifiedHash160)) != 0 ||
                    strcmp(verifiedAddr, addr) != 0) {
                    printf("  [warn] Verification failed for tid=%u incr=%d parity=%u iter=%lu; skipping output.\n",
                           tid, incr, isOdd, iter);
                    continue;
                }

                char hexKey[65], wifKey[60];
                format_256bit_hex(privkey, hexKey);
                privkey_to_wif(privkey, wifKey, isCompressed);

                const char* addrType = isCompressed ? "compressed" : "uncompressed";
                fprintf(mf, "[%s] Pattern='%s' Address=%s (%s)\n", timestr, pattern, addr, addrType);
                fprintf(mf, "  PrivKey (HEX): 0x%s\n", hexKey);
                fprintf(mf, "  PrivKey (WIF): %s\n", wifKey);
                fprintf(mf, "  Hash160: ");
                for (int b = 0; b < 20; b++) fprintf(mf, "%02x", hash160[b]);
                fprintf(mf, "\n  VerifiedAddress: %s\n", verifiedAddr);
                fprintf(mf, "  tid=%u incr=%d parity=%d iter=%lu\n\n", tid, incr, isOdd, iter);

                verifiedCount++;
                printf("  %s -> Pattern: %s\n", addr, pattern);
                printf("    PrivKey: 0x%s\n", hexKey);
            }
            if (verifiedCount != nFound) {
                printf("  [info] %u/%u matches passed host-side verification.\n", verifiedCount, nFound);
            }
            fclose(mf);
        }

        // Sequential mode: each iteration covers nbThread * STEP_SIZE unique keys
        // After iter iterations: covered range [0, iter * nbThread * STEP_SIZE)
        uint64_t keysPerIter = (uint64_t)nbThread * STEP_SIZE;
        total += keysPerIter;
        iter++;

        // Range-end termination: stop once the covered range has passed endKey.
        // "Last key covered this iter" ~= g_baseKey + total - 1; we compare
        // against endKey and bail cleanly if we're past it. The scan may
        // overshoot by up to nbThread*STEP_SIZE keys within a single iteration,
        // which is immaterial for puzzle ranges much larger than one iter.
        if (haveEndx) {
            uint64_t covered[4] = {total, 0, 0, 0};
            uint64_t current[4];
            add256(current, g_baseKey, covered);
            if (cmp256(current, endKey) > 0) {
                char ehex[65]; format_256bit_hex(endKey, ehex);
                printf("\n\n[+] Range end reached (covered past 0x%s). Stopping.\n", ehex);
                running = false;
            }
        }

        if (iter % 500 == 0) {
            cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
            save_state_seq(stateFile, h_keys, nbThread, total, iter, g_baseKey);
        }

        if (iter % 10 == 0 || verbose) {  // More frequent updates since each iter covers 67M keys
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
    save_state_seq(stateFile, h_keys, nbThread, total, iter, g_baseKey);
    printf("Total: %.2fB keys\n", total/1e9);

    cudaFree(d_keys);
    cudaFree(d_found);
    cudaFree(d_dx);
    cudaFree(d_subp);
    cudaFreeHost(h_found);
    free(h_keys);

    return 0;
}
