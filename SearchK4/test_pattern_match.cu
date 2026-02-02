// Test pattern matching in kernel
#include <stdio.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>
#include <string.h>

#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

#define NB_THREAD_PER_GROUP 64
#define K4_MAX_PATTERNS 256
#define P2PKH 0
#define MAX_FOUND 65536

__device__ __constant__ char pszBase58[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
__device__ __constant__ char d_patterns[K4_MAX_PATTERNS][36];
__device__ __constant__ int d_pattern_lens[K4_MAX_PATTERNS];
__device__ __constant__ int d_num_patterns;

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
        b58Add[retPos++] = 0x31;  // ASCII '1'
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
        entry[0] = tid;
        entry[1] = (uint32_t)incr;
        entry[2] = (pattern_idx << 8) | isOdd;
        entry[3] = h[0];
        entry[4] = h[1];
        entry[5] = h[2];
        entry[6] = h[3];
        entry[7] = h[4];
    }
}

__global__ void test_pattern_kernel(uint64_t* keys, uint32_t maxFound, uint32_t* found, uint32_t* debug) {
    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (tid != 0) return;
    
    // Read patterns info from constant memory
    debug[0] = d_num_patterns;
    
    // Copy first pattern for debug
    for (int i = 0; i < 20 && i < d_pattern_lens[0]; i++) {
        ((char*)&debug[1])[i] = d_patterns[0][i];
    }
    debug[6] = d_pattern_lens[0];
    
    // Copy second pattern for debug
    for (int i = 0; i < 20 && i < d_pattern_lens[1]; i++) {
        ((char*)&debug[7])[i] = d_patterns[1][i];
    }
    debug[12] = d_pattern_lens[1];
    
    // Load starting point
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    
    uint64_t px[4], py[4];
    Load256A(px, keys + xPtr);
    Load256A(py, keys + yPtr);
    
    // Compute hashes
    uint32_t h1[5], h2[5];
    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);
    
    // Check patterns
    char addr[40];
    int matched_idx;
    
    bool match1 = CheckVanityPatternsK4(h1, &matched_idx, addr);
    debug[13] = match1 ? 1 : 0;
    debug[14] = matched_idx;
    
    // Copy generated address
    for (int i = 0; i < 35; i++) {
        ((char*)&debug[15])[i] = addr[i];
    }
    
    bool match2 = CheckVanityPatternsK4(h2, &matched_idx, addr);
    debug[24] = match2 ? 1 : 0;
    debug[25] = matched_idx;
    
    // If there's a match, output it
    if (match1) {
        OutputMatchK4(found, tid, 512, h1, matched_idx, 0);
    }
    if (match2) {
        OutputMatchK4(found, tid, 512, h2, matched_idx, 1);
    }
}

// secp256k1 constants
static const uint64_t SECP_GX[4] = {
    0x59F2815B16F81798ULL, 0x029BFCDB2DCE28D9ULL,
    0x55A06295CE870B07ULL, 0x79BE667EF9DCBBACULL
};

static const uint64_t SECP_GY[4] = {
    0x9C47D08FFB10D4B8ULL, 0xFD17B448A6855419ULL,
    0x5DA4FBFC0E1108A8ULL, 0x483ADA7726A3C465ULL
};

int main() {
    printf("=== Pattern Match Test ===\n\n");
    
    cudaDeviceSetLimit(cudaLimitStackSize, 36 * 1024);
    
    // Load patterns
    char h_patterns[K4_MAX_PATTERNS][36];
    int h_lens[K4_MAX_PATTERNS];
    int numPatterns = 2;
    
    strcpy(h_patterns[0], "1BgGZ9tcN");
    h_lens[0] = 9;
    
    strcpy(h_patterns[1], "1EHNa6Q4J");
    h_lens[1] = 9;
    
    printf("Loading %d patterns:\n", numPatterns);
    printf("  Pattern 0: '%s' (len=%d)\n", h_patterns[0], h_lens[0]);
    printf("  Pattern 1: '%s' (len=%d)\n", h_patterns[1], h_lens[1]);
    printf("\n");
    
    // Copy patterns to device constant memory
    cudaError_t err;
    err = cudaMemcpyToSymbol(d_patterns, h_patterns, sizeof(h_patterns));
    printf("Copy patterns: %s\n", cudaGetErrorString(err));
    
    err = cudaMemcpyToSymbol(d_pattern_lens, h_lens, sizeof(h_lens));
    printf("Copy lens: %s\n", cudaGetErrorString(err));
    
    err = cudaMemcpyToSymbol(d_num_patterns, &numPatterns, sizeof(int));
    printf("Copy num: %s\n", cudaGetErrorString(err));
    printf("\n");
    
    // Allocate keys
    uint64_t* h_keys = (uint64_t*)malloc(NB_THREAD_PER_GROUP * 64);
    memset(h_keys, 0, NB_THREAD_PER_GROUP * 64);
    
    // Store G point for thread 0
    int xBase = 0;
    int yBase = 4 * NB_THREAD_PER_GROUP;
    
    h_keys[xBase + 0 * NB_THREAD_PER_GROUP] = SECP_GX[0];
    h_keys[xBase + 1 * NB_THREAD_PER_GROUP] = SECP_GX[1];
    h_keys[xBase + 2 * NB_THREAD_PER_GROUP] = SECP_GX[2];
    h_keys[xBase + 3 * NB_THREAD_PER_GROUP] = SECP_GX[3];
    
    h_keys[yBase + 0 * NB_THREAD_PER_GROUP] = SECP_GY[0];
    h_keys[yBase + 1 * NB_THREAD_PER_GROUP] = SECP_GY[1];
    h_keys[yBase + 2 * NB_THREAD_PER_GROUP] = SECP_GY[2];
    h_keys[yBase + 3 * NB_THREAD_PER_GROUP] = SECP_GY[3];
    
    uint64_t* d_keys;
    cudaMalloc(&d_keys, NB_THREAD_PER_GROUP * 64);
    cudaMemcpy(d_keys, h_keys, NB_THREAD_PER_GROUP * 64, cudaMemcpyHostToDevice);
    
    // Allocate found buffer
    uint32_t* d_found;
    cudaMalloc(&d_found, (1 + MAX_FOUND * 8) * 4);
    cudaMemset(d_found, 0, 4);
    
    // Allocate debug buffer
    uint32_t* d_debug;
    cudaMalloc(&d_debug, 128 * 4);
    cudaMemset(d_debug, 0, 128 * 4);
    
    // Launch kernel
    test_pattern_kernel<<<1, NB_THREAD_PER_GROUP>>>(d_keys, MAX_FOUND, d_found, d_debug);
    cudaDeviceSynchronize();
    
    err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("CUDA Error: %s\n", cudaGetErrorString(err));
        return 1;
    }
    
    // Copy back results
    uint32_t h_debug[128];
    cudaMemcpy(h_debug, d_debug, 128 * 4, cudaMemcpyDeviceToHost);
    
    uint32_t h_found[1 + 8];
    cudaMemcpy(h_found, d_found, 4, cudaMemcpyDeviceToHost);
    
    printf("Debug output:\n");
    printf("  d_num_patterns read in kernel: %d\n", h_debug[0]);
    printf("  Pattern 0 in kernel: '%.20s' (len=%d)\n", (char*)&h_debug[1], h_debug[6]);
    printf("  Pattern 1 in kernel: '%.20s' (len=%d)\n", (char*)&h_debug[7], h_debug[12]);
    printf("\n");
    
    printf("Pattern check results:\n");
    printf("  Even parity (02) match: %s (idx=%d)\n", h_debug[13] ? "YES" : "NO", (int)h_debug[14]);
    printf("  Generated address: %.35s\n", (char*)&h_debug[15]);
    printf("  Odd parity (03) match: %s (idx=%d)\n", h_debug[24] ? "YES" : "NO", (int)h_debug[25]);
    printf("\n");
    
    printf("Found buffer count: %d\n", h_found[0]);
    
    if (h_found[0] > 0) {
        cudaMemcpy(h_found, d_found, (1 + h_found[0] * 8) * 4, cudaMemcpyDeviceToHost);
        printf("Match details:\n");
        for (uint32_t i = 0; i < h_found[0]; i++) {
            uint32_t* entry = h_found + 1 + i * 8;
            printf("  Entry %d: tid=%u incr=%d pattern=%d parity=%d\n",
                   i, entry[0], (int32_t)entry[1], (entry[2] >> 8) & 0xFF, entry[2] & 0xFF);
        }
    }
    
    cudaFree(d_keys);
    cudaFree(d_found);
    cudaFree(d_debug);
    free(h_keys);
    
    return 0;
}
