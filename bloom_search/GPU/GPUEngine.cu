/*
 * GPUEngine.cu - CUDA implementation for bloom filter-based address search
 *
 * This file integrates with VanitySearch's GPU infrastructure but replaces
 * the prefix matching with bloom filter checking.
 */

#include <cuda.h>
#include <cuda_runtime.h>
#include <device_launch_parameters.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "GPUBloom.h"

// ============================================================================
// CUDA ERROR CHECKING
// ============================================================================

#define CUDA_CHECK(call) { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, \
                cudaGetErrorString(err)); \
        exit(1); \
    } \
}

// ============================================================================
// SECP256K1 CONSTANTS
// ============================================================================

// Prime field P = 2^256 - 2^32 - 977
__device__ __constant__ uint64_t _P[4] = {
    0xFFFFFFFEFFFFFC2FULL,
    0xFFFFFFFFFFFFFFFFULL,
    0xFFFFFFFFFFFFFFFFULL,
    0xFFFFFFFFFFFFFFFFULL
};

// Order N
__device__ __constant__ uint64_t _N[4] = {
    0xBFD25E8CD0364141ULL,
    0xBAAEDCE6AF48A03BULL,
    0xFFFFFFFFFFFFFFFEULL,
    0xFFFFFFFFFFFFFFFFULL
};

// Generator G point
__device__ __constant__ uint64_t _Gx[4] = {
    0x59F2815B16F81798ULL,
    0x029BFCDB2DCE28D9ULL,
    0x55A06295CE870B07ULL,
    0x79BE667EF9DCBBACULL
};

__device__ __constant__ uint64_t _Gy[4] = {
    0x9C47D08FFB10D4B8ULL,
    0xFD17B448A6855419ULL,
    0x5DA4FBFC0E1108A8ULL,
    0x483ADA7726A3C465ULL
};

// ============================================================================
// BLOOM FILTER DEVICE MEMORY
// ============================================================================

__device__ uint8_t* g_bloomFilter = nullptr;
__device__ __constant__ uint64_t g_bloomBits;
__device__ __constant__ uint32_t g_bloomHashes;
__device__ __constant__ uint32_t g_bloomSeeds[24];

// ============================================================================
// MODULAR ARITHMETIC (64-bit limbs)
// ============================================================================

// Montgomery reduction constants
__device__ __constant__ uint64_t _R2[4] = {
    0x0000000000000001ULL,
    0x0000000100000000ULL,
    0x0000000000000000ULL,
    0x0000000000000000ULL
};

// Add two 256-bit numbers modulo P
__device__ void _ModAdd(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t c = 0;
    for (int i = 0; i < 4; i++) {
        uint64_t t = a[i] + b[i] + c;
        c = (t < a[i]) || (c && t == a[i]) ? 1 : 0;
        r[i] = t;
    }

    // Reduce if >= P
    if (c || (r[3] > _P[3]) ||
        (r[3] == _P[3] && r[2] > _P[2]) ||
        (r[3] == _P[3] && r[2] == _P[2] && r[1] > _P[1]) ||
        (r[3] == _P[3] && r[2] == _P[2] && r[1] == _P[1] && r[0] >= _P[0])) {
        c = 0;
        for (int i = 0; i < 4; i++) {
            uint64_t t = r[i] - _P[i] - c;
            c = (t > r[i]) || (c && t == r[i]) ? 1 : 0;
            r[i] = t;
        }
    }
}

// Subtract two 256-bit numbers modulo P
__device__ void _ModSub(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    uint64_t c = 0;
    for (int i = 0; i < 4; i++) {
        uint64_t t = a[i] - b[i] - c;
        c = (t > a[i]) || (c && t == a[i]) ? 1 : 0;
        r[i] = t;
    }

    // Add P if negative
    if (c) {
        c = 0;
        for (int i = 0; i < 4; i++) {
            uint64_t t = r[i] + _P[i] + c;
            c = (t < r[i]) || (c && t == r[i]) ? 1 : 0;
            r[i] = t;
        }
    }
}

// Negate modulo P
__device__ void _ModNeg(uint64_t* r, const uint64_t* a) {
    uint64_t zero[4] = {0, 0, 0, 0};
    _ModSub(r, zero, a);
}

// Multiply using secp256k1's special form: P = 2^256 - 2^32 - 977
__device__ void _ModMult(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    // 512-bit product
    uint64_t t[8];
    uint64_t c;

    // Full multiplication (8x8 = 16 64-bit words, but we only need 8)
    // Using Karatsuba would be faster but more complex

    // Simple schoolbook for now
    unsigned __int128 acc;
    t[0] = t[1] = t[2] = t[3] = t[4] = t[5] = t[6] = t[7] = 0;

    for (int i = 0; i < 4; i++) {
        c = 0;
        for (int j = 0; j < 4; j++) {
            acc = (unsigned __int128)a[i] * b[j] + t[i+j] + c;
            t[i+j] = (uint64_t)acc;
            c = (uint64_t)(acc >> 64);
        }
        t[i+4] = c;
    }

    // Reduce modulo P using secp256k1's special structure
    // P = 2^256 - c where c = 2^32 + 977
    // t mod P = t_low + t_high * 2^256 = t_low + t_high * c (mod P)

    uint64_t h[4] = {t[4], t[5], t[6], t[7]};

    // Multiply high part by c = 2^32 + 977
    uint64_t hc[5] = {0, 0, 0, 0, 0};
    c = 0;
    for (int i = 0; i < 4; i++) {
        acc = (unsigned __int128)h[i] * 0x100000977ULL + c;
        hc[i] = (uint64_t)acc;
        c = (uint64_t)(acc >> 64);
    }
    hc[4] = c;

    // Add to low part
    c = 0;
    for (int i = 0; i < 4; i++) {
        uint64_t sum = t[i] + hc[i] + c;
        c = (sum < t[i]) || (c && sum == t[i]) ? 1 : 0;
        r[i] = sum;
    }

    // Handle remaining carry and hc[4]
    if (c || hc[4]) {
        uint64_t extra = c + hc[4];
        // Multiply extra by c and add
        acc = (unsigned __int128)extra * 0x100000977ULL;
        uint64_t lo = (uint64_t)acc;
        uint64_t hi = (uint64_t)(acc >> 64);

        c = 0;
        r[0] += lo;
        c = (r[0] < lo) ? 1 : 0;
        r[1] += hi + c;
        c = (r[1] < hi + c) || (c && r[1] == hi) ? 1 : 0;

        if (c) {
            r[2] += 1;
            c = (r[2] == 0) ? 1 : 0;
            if (c) r[3] += 1;
        }
    }

    // Final reduction if >= P
    if (r[3] > _P[3] ||
        (r[3] == _P[3] && r[2] > _P[2]) ||
        (r[3] == _P[3] && r[2] == _P[2] && r[1] > _P[1]) ||
        (r[3] == _P[3] && r[2] == _P[2] && r[1] == _P[1] && r[0] >= _P[0])) {
        _ModSub(r, r, _P);
    }
}

// Square modulo P
__device__ void _ModSquare(uint64_t* r, const uint64_t* a) {
    _ModMult(r, a, a);
}

// ============================================================================
// SHA256 (Device implementation)
// ============================================================================

__device__ __constant__ uint32_t K256[64] = {
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

__device__ uint32_t ROTR32(uint32_t x, int n) {
    return (x >> n) | (x << (32 - n));
}

__device__ void sha256_transform(uint32_t* state, const uint8_t* block) {
    uint32_t W[64];
    uint32_t a, b, c, d, e, f, g, h;

    // Initialize W
    for (int i = 0; i < 16; i++) {
        W[i] = ((uint32_t)block[i*4] << 24) |
               ((uint32_t)block[i*4+1] << 16) |
               ((uint32_t)block[i*4+2] << 8) |
               ((uint32_t)block[i*4+3]);
    }

    for (int i = 16; i < 64; i++) {
        uint32_t s0 = ROTR32(W[i-15], 7) ^ ROTR32(W[i-15], 18) ^ (W[i-15] >> 3);
        uint32_t s1 = ROTR32(W[i-2], 17) ^ ROTR32(W[i-2], 19) ^ (W[i-2] >> 10);
        W[i] = W[i-16] + s0 + W[i-7] + s1;
    }

    a = state[0]; b = state[1]; c = state[2]; d = state[3];
    e = state[4]; f = state[5]; g = state[6]; h = state[7];

    for (int i = 0; i < 64; i++) {
        uint32_t S1 = ROTR32(e, 6) ^ ROTR32(e, 11) ^ ROTR32(e, 25);
        uint32_t ch = (e & f) ^ (~e & g);
        uint32_t temp1 = h + S1 + ch + K256[i] + W[i];
        uint32_t S0 = ROTR32(a, 2) ^ ROTR32(a, 13) ^ ROTR32(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t temp2 = S0 + maj;

        h = g; g = f; f = e; e = d + temp1;
        d = c; c = b; b = a; a = temp1 + temp2;
    }

    state[0] += a; state[1] += b; state[2] += c; state[3] += d;
    state[4] += e; state[5] += f; state[6] += g; state[7] += h;
}

__device__ void _SHA256(const uint8_t* data, int len, uint8_t* hash) {
    uint32_t state[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    uint8_t block[64];
    int i;

    // Process full blocks
    while (len >= 64) {
        sha256_transform(state, data);
        data += 64;
        len -= 64;
    }

    // Final block with padding
    for (i = 0; i < len; i++) block[i] = data[i];
    block[i++] = 0x80;

    if (i > 56) {
        while (i < 64) block[i++] = 0;
        sha256_transform(state, block);
        i = 0;
    }

    while (i < 56) block[i++] = 0;

    // Length in bits (big endian)
    uint64_t bits = (uint64_t)len * 8;
    block[56] = 0; block[57] = 0; block[58] = 0; block[59] = 0;
    block[60] = (bits >> 24) & 0xff;
    block[61] = (bits >> 16) & 0xff;
    block[62] = (bits >> 8) & 0xff;
    block[63] = bits & 0xff;

    sha256_transform(state, block);

    // Output
    for (i = 0; i < 8; i++) {
        hash[i*4] = (state[i] >> 24) & 0xff;
        hash[i*4+1] = (state[i] >> 16) & 0xff;
        hash[i*4+2] = (state[i] >> 8) & 0xff;
        hash[i*4+3] = state[i] & 0xff;
    }
}

// ============================================================================
// RIPEMD160 (Device implementation)
// ============================================================================

__device__ uint32_t ROL32(uint32_t x, int n) {
    return (x << n) | (x >> (32 - n));
}

__device__ void _RIPEMD160(const uint8_t* msg, int len, uint8_t* hash) {
    // Simplified RIPEMD160 for 32-byte input (SHA256 output)
    // Full implementation would be longer

    uint32_t h0 = 0x67452301;
    uint32_t h1 = 0xEFCDAB89;
    uint32_t h2 = 0x98BADCFE;
    uint32_t h3 = 0x10325476;
    uint32_t h4 = 0xC3D2E1F0;

    // For 32-byte message, we have one block with padding
    uint32_t X[16];
    for (int i = 0; i < 8; i++) {
        X[i] = ((uint32_t)msg[i*4]) |
               ((uint32_t)msg[i*4+1] << 8) |
               ((uint32_t)msg[i*4+2] << 16) |
               ((uint32_t)msg[i*4+3] << 24);
    }
    X[8] = 0x80;  // Padding
    X[9] = X[10] = X[11] = X[12] = X[13] = 0;
    X[14] = 256;  // Length in bits
    X[15] = 0;

    // RIPEMD160 compression function
    // (Abbreviated - full implementation has 80 rounds)
    // This is a placeholder - actual RIPEMD160 is complex

    uint32_t a = h0, b = h1, c = h2, d = h3, e = h4;
    uint32_t aa = h0, bb = h1, cc = h2, dd = h3, ee = h4;

    // Left rounds (simplified)
    #define F(x, y, z) ((x) ^ (y) ^ (z))
    #define G(x, y, z) (((x) & (y)) | (~(x) & (z)))
    #define H(x, y, z) (((x) | ~(y)) ^ (z))
    #define I(x, y, z) (((x) & (z)) | ((y) & ~(z)))
    #define J(x, y, z) ((x) ^ ((y) | ~(z)))

    // Round 1
    for (int j = 0; j < 16; j++) {
        uint32_t t = ROL32(a + F(b,c,d) + X[j], 11) + e;
        a = e; e = d; d = ROL32(c, 10); c = b; b = t;
    }

    // Simplified final
    uint32_t t = h1 + c + dd;
    h1 = h2 + d + ee;
    h2 = h3 + e + aa;
    h3 = h4 + a + bb;
    h4 = h0 + b + cc;
    h0 = t;

    // Output
    hash[0] = h0 & 0xff; hash[1] = (h0 >> 8) & 0xff;
    hash[2] = (h0 >> 16) & 0xff; hash[3] = (h0 >> 24) & 0xff;
    hash[4] = h1 & 0xff; hash[5] = (h1 >> 8) & 0xff;
    hash[6] = (h1 >> 16) & 0xff; hash[7] = (h1 >> 24) & 0xff;
    hash[8] = h2 & 0xff; hash[9] = (h2 >> 8) & 0xff;
    hash[10] = (h2 >> 16) & 0xff; hash[11] = (h2 >> 24) & 0xff;
    hash[12] = h3 & 0xff; hash[13] = (h3 >> 8) & 0xff;
    hash[14] = (h3 >> 16) & 0xff; hash[15] = (h3 >> 24) & 0xff;
    hash[16] = h4 & 0xff; hash[17] = (h4 >> 8) & 0xff;
    hash[18] = (h4 >> 16) & 0xff; hash[19] = (h4 >> 24) & 0xff;
}

// ============================================================================
// MAIN BLOOM SEARCH KERNEL
// ============================================================================

#define GRP_SIZE 1024
#define ITEM_SIZE 8

__global__ void bloomSearchKernel(
    uint64_t* keys,           // Starting points (8 uint64 per thread: 4 for x, 4 for y)
    uint32_t* output,         // Output buffer for matches
    uint32_t maxMatches,
    bool searchCompressed,
    bool searchUncompressed,
    uint8_t* bloomFilter,
    uint64_t bloomBits,
    uint32_t* bloomSeeds,
    uint32_t bloomHashes
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;

    // Load starting point
    uint64_t px[4], py[4];
    for (int i = 0; i < 4; i++) {
        px[i] = keys[tid * 8 + i];
        py[i] = keys[tid * 8 + 4 + i];
    }

    // Compute hash160
    uint8_t pubkey[65];
    uint8_t sha[32];
    uint8_t hash160[20];

    if (searchCompressed) {
        // Compressed public key: 0x02/0x03 + X
        pubkey[0] = (py[0] & 1) ? 0x03 : 0x02;
        for (int i = 0; i < 4; i++) {
            uint64_t v = px[3-i];
            for (int j = 0; j < 8; j++) {
                pubkey[1 + i*8 + j] = (v >> (56 - j*8)) & 0xFF;
            }
        }

        _SHA256(pubkey, 33, sha);
        _RIPEMD160(sha, 32, hash160);

        // Check bloom filter
        if (bloom_check_single(hash160, bloomFilter, bloomBits, bloomSeeds, bloomHashes)) {
            uint32_t pos = atomicAdd(output, 1);
            if (pos < maxMatches) {
                output[pos * ITEM_SIZE + 1] = tid;
                output[pos * ITEM_SIZE + 2] = 1;  // compressed
                for (int i = 0; i < 5; i++) {
                    output[pos * ITEM_SIZE + 3 + i] = ((uint32_t*)hash160)[i];
                }
            }
        }
    }

    if (searchUncompressed) {
        // Uncompressed public key: 0x04 + X + Y
        pubkey[0] = 0x04;
        for (int i = 0; i < 4; i++) {
            uint64_t vx = px[3-i];
            uint64_t vy = py[3-i];
            for (int j = 0; j < 8; j++) {
                pubkey[1 + i*8 + j] = (vx >> (56 - j*8)) & 0xFF;
                pubkey[33 + i*8 + j] = (vy >> (56 - j*8)) & 0xFF;
            }
        }

        _SHA256(pubkey, 65, sha);
        _RIPEMD160(sha, 32, hash160);

        // Check bloom filter
        if (bloom_check_single(hash160, bloomFilter, bloomBits, bloomSeeds, bloomHashes)) {
            uint32_t pos = atomicAdd(output, 1);
            if (pos < maxMatches) {
                output[pos * ITEM_SIZE + 1] = tid;
                output[pos * ITEM_SIZE + 2] = 0;  // uncompressed
                for (int i = 0; i < 5; i++) {
                    output[pos * ITEM_SIZE + 3 + i] = ((uint32_t*)hash160)[i];
                }
            }
        }
    }
}

// ============================================================================
// HOST FUNCTIONS
// ============================================================================

extern "C" {

void* createBloomSearchEngine(int deviceId) {
    cudaSetDevice(deviceId);

    // Get device properties
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, deviceId);

    printf("Using GPU %d: %s\n", deviceId, prop.name);
    printf("  - Compute capability: %d.%d\n", prop.major, prop.minor);
    printf("  - Global memory: %zu MB\n", prop.totalGlobalMem / 1024 / 1024);
    printf("  - Shared memory per block: %zu KB\n", prop.sharedMemPerBlock / 1024);
    printf("  - Max threads per block: %d\n", prop.maxThreadsPerBlock);

    return (void*)(intptr_t)deviceId;
}

int loadBloomFilterToGPU(
    void* engine,
    const uint8_t* filterData,
    uint64_t numBytes,
    uint64_t numBits,
    const uint32_t* seeds,
    uint32_t numHashes
) {
    int deviceId = (intptr_t)engine;
    cudaSetDevice(deviceId);

    // Allocate and copy bloom filter to GPU
    uint8_t* d_filter;
    CUDA_CHECK(cudaMalloc(&d_filter, numBytes));
    CUDA_CHECK(cudaMemcpy(d_filter, filterData, numBytes, cudaMemcpyHostToDevice));

    // Set constant memory
    CUDA_CHECK(cudaMemcpyToSymbol(g_bloomBits, &numBits, sizeof(uint64_t)));
    CUDA_CHECK(cudaMemcpyToSymbol(g_bloomHashes, &numHashes, sizeof(uint32_t)));
    CUDA_CHECK(cudaMemcpyToSymbol(g_bloomSeeds, seeds, numHashes * sizeof(uint32_t)));

    // Store pointer
    CUDA_CHECK(cudaMemcpyToSymbol(g_bloomFilter, &d_filter, sizeof(uint8_t*)));

    printf("Loaded bloom filter to GPU: %zu MB\n", numBytes / 1024 / 1024);

    return 0;
}

int launchBloomSearch(
    void* engine,
    uint64_t* hostKeys,
    int numKeys,
    uint32_t* hostOutput,
    uint32_t maxMatches,
    bool searchCompressed,
    bool searchUncompressed
) {
    int deviceId = (intptr_t)engine;
    cudaSetDevice(deviceId);

    // Allocate device memory
    uint64_t* d_keys;
    uint32_t* d_output;

    size_t keysSize = numKeys * 8 * sizeof(uint64_t);
    size_t outputSize = (maxMatches * ITEM_SIZE + 1) * sizeof(uint32_t);

    CUDA_CHECK(cudaMalloc(&d_keys, keysSize));
    CUDA_CHECK(cudaMalloc(&d_output, outputSize));

    // Copy keys to device
    CUDA_CHECK(cudaMemcpy(d_keys, hostKeys, keysSize, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemset(d_output, 0, outputSize));

    // Get bloom filter pointer from device
    uint8_t* d_bloomFilter;
    uint64_t bloomBits;
    uint32_t bloomHashes;
    uint32_t bloomSeeds[24];

    CUDA_CHECK(cudaMemcpyFromSymbol(&d_bloomFilter, g_bloomFilter, sizeof(uint8_t*)));
    CUDA_CHECK(cudaMemcpyFromSymbol(&bloomBits, g_bloomBits, sizeof(uint64_t)));
    CUDA_CHECK(cudaMemcpyFromSymbol(&bloomHashes, g_bloomHashes, sizeof(uint32_t)));
    CUDA_CHECK(cudaMemcpyFromSymbol(bloomSeeds, g_bloomSeeds, 24 * sizeof(uint32_t)));

    // Launch kernel
    int blockSize = 256;
    int numBlocks = (numKeys + blockSize - 1) / blockSize;

    bloomSearchKernel<<<numBlocks, blockSize>>>(
        d_keys,
        d_output,
        maxMatches,
        searchCompressed,
        searchUncompressed,
        d_bloomFilter,
        bloomBits,
        bloomSeeds,
        bloomHashes
    );

    CUDA_CHECK(cudaDeviceSynchronize());

    // Copy results back
    CUDA_CHECK(cudaMemcpy(hostOutput, d_output, outputSize, cudaMemcpyDeviceToHost));

    // Get number of matches
    int numMatches = hostOutput[0];

    // Update keys on host (for next iteration)
    CUDA_CHECK(cudaMemcpy(hostKeys, d_keys, keysSize, cudaMemcpyDeviceToHost));

    // Free device memory
    CUDA_CHECK(cudaFree(d_keys));
    CUDA_CHECK(cudaFree(d_output));

    return numMatches;
}

void destroyBloomSearchEngine(void* engine) {
    int deviceId = (intptr_t)engine;
    cudaSetDevice(deviceId);

    // Free bloom filter
    uint8_t* d_bloomFilter;
    cudaMemcpyFromSymbol(&d_bloomFilter, g_bloomFilter, sizeof(uint8_t*));
    if (d_bloomFilter) {
        cudaFree(d_bloomFilter);
    }

    cudaDeviceReset();
}

} // extern "C"
