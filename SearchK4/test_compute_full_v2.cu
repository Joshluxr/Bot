// Test full ComputeKeysK4 function with better stack handling
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
#define STEP_SIZE 1024

__device__ __constant__ char pszBase58[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
__device__ __constant__ char d_patterns[K4_MAX_PATTERNS][36];
__device__ __constant__ int d_pattern_lens[K4_MAX_PATTERNS];
__device__ __constant__ int d_num_patterns;
__device__ __constant__ uint64_t d_seqDeltaX[4];
__device__ __constant__ uint64_t d_seqDeltaY[4];
__device__ __constant__ int d_useSeqDelta;

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
    
    while (addPtr[0] == 0) { b58Add[retPos++] = 0x31; addPtr++; }
    int length = 25 - retPos;
    int digitslen = 1; digits[0] = 0;
    for (int i = 0; i < length; i++) {
        uint32_t carry = addPtr[i];
        for (int j = 0; j < digitslen; j++) {
            carry += (uint32_t)(digits[j]) << 8;
            digits[j] = (unsigned char)(carry % 58);
            carry /= 58;
        }
        while (carry > 0) { digits[digitslen++] = (unsigned char)(carry % 58); carry /= 58; }
    }
    for (int i = 0; i < digitslen; i++) b58Add[retPos++] = pszBase58[digits[digitslen - 1 - i]];
    b58Add[retPos] = 0;
}

__device__ __noinline__ bool _MatchPrefix(const char *addr, const char *pattern, int patLen) {
    for (int i = 0; i < patLen; i++) { if (addr[i] != pattern[i]) return false; }
    return true;
}

__device__ bool CheckVanityPatternsK4(uint32_t *h, int *matched_idx, char *gen_addr) {
    _GetAddress(P2PKH, h, gen_addr);
    for (int i = 0; i < d_num_patterns; i++) {
        if (_MatchPrefix(gen_addr, d_patterns[i], d_pattern_lens[i])) { *matched_idx = i; return true; }
    }
    *matched_idx = -1;
    return false;
}

__device__ void OutputMatchK4(uint32_t* out, uint32_t tid, int32_t incr, uint32_t* h, int pattern_idx, uint8_t isOdd) {
    uint32_t pos = atomicAdd(out, 1);
    if (pos < MAX_FOUND) {
        uint32_t* entry = out + 1 + pos * 8;
        entry[0] = tid; entry[1] = (uint32_t)incr; entry[2] = (pattern_idx << 8) | isOdd;
        entry[3] = h[0]; entry[4] = h[1]; entry[5] = h[2]; entry[6] = h[3]; entry[7] = h[4];
    }
}

__device__ __noinline__ void CheckHashCompSymK4(uint64_t* px, uint64_t* py, uint32_t tid, int32_t incr, uint32_t maxFound, uint32_t* out, bool yNegated = false) {
    uint32_t h1[5], h2[5], h3[5];
    char addr[40];
    int matched_idx;
    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);
    if (CheckVanityPatternsK4(h1, &matched_idx, addr)) { OutputMatchK4(out, tid, incr, h1, matched_idx, 0); }
    if (CheckVanityPatternsK4(h2, &matched_idx, addr)) { OutputMatchK4(out, tid, -incr, h2, matched_idx, 1); }
    uint64_t realY[4];
    if (yNegated) { ModNeg256(realY, py); } else { Load256(realY, py); }
    _GetHash160(px, realY, (uint8_t*)h3);
    if (CheckVanityPatternsK4(h3, &matched_idx, addr)) {
        int32_t actualIncr = yNegated ? -incr : incr;
        OutputMatchK4(out, tid, actualIncr, h3, matched_idx, 2);
    }
}

// Full ComputeKeysK4 (same as main program)
__device__ void ComputeKeysK4(uint32_t mode, uint64_t* startx, uint64_t* starty, uint32_t maxFound, uint32_t* out) {
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

        CheckHashCompSymK4(px, py, tid, j*GRP_SIZE + GRP_SIZE/2, maxFound, out, false);

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

            CheckHashCompSymK4(px, py, tid, j*GRP_SIZE + GRP_SIZE/2 + (i+1), maxFound, out, false);

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

            CheckHashCompSymK4(px, py, tid, j*GRP_SIZE + GRP_SIZE/2 - (i+1), maxFound, out, true);
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
        CheckHashCompSymK4(px, py, tid, j*GRP_SIZE, maxFound, out, true);

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

    __syncthreads();
    Store256A(startx, px);
    Store256A(starty, py);
}

__global__ void test_full_kernel(uint64_t* keys, uint32_t maxFound, uint32_t* found) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    ComputeKeysK4(0, keys + xPtr, keys + yPtr, maxFound, found);
}

static const uint64_t SECP_GX[4] = {0x59F2815B16F81798ULL, 0x029BFCDB2DCE28D9ULL, 0x55A06295CE870B07ULL, 0x79BE667EF9DCBBACULL};
static const uint64_t SECP_GY[4] = {0x9C47D08FFB10D4B8ULL, 0xFD17B448A6855419ULL, 0x5DA4FBFC0E1108A8ULL, 0x483ADA7726A3C465ULL};

int main() {
    printf("=== ComputeKeysK4 Full Test v2 ===\n\n");
    
    // Set device and stack FIRST, before any other CUDA calls
    cudaSetDevice(0);
    
    cudaError_t err = cudaDeviceSetLimit(cudaLimitStackSize, 128 * 1024);  // 128KB
    printf("cudaDeviceSetLimit(128KB): %s\n", cudaGetErrorString(err));
    
    size_t stackSize;
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("Actual stack size: %zu bytes (%.1f KB)\n\n", stackSize, stackSize / 1024.0);
    
    char h_patterns[K4_MAX_PATTERNS][36];
    int h_lens[K4_MAX_PATTERNS];
    int numPatterns = 2;
    strcpy(h_patterns[0], "1BgGZ9tcN");
    h_lens[0] = 9;
    strcpy(h_patterns[1], "1EHNa6Q4J");
    h_lens[1] = 9;
    
    printf("Patterns: '%s', '%s'\n", h_patterns[0], h_patterns[1]);
    
    cudaMemcpyToSymbol(d_patterns, h_patterns, sizeof(h_patterns));
    cudaMemcpyToSymbol(d_pattern_lens, h_lens, sizeof(h_lens));
    cudaMemcpyToSymbol(d_num_patterns, &numPatterns, sizeof(int));
    int useSeq = 0;
    cudaMemcpyToSymbol(d_useSeqDelta, &useSeq, sizeof(int));
    
    uint64_t* h_keys = (uint64_t*)malloc(NB_THREAD_PER_GROUP * 64);
    memset(h_keys, 0, NB_THREAD_PER_GROUP * 64);
    
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
    
    printf("Thread 0 key = G point (private key 1)\n\n");
    
    uint64_t* d_keys;
    cudaMalloc(&d_keys, NB_THREAD_PER_GROUP * 64);
    cudaMemcpy(d_keys, h_keys, NB_THREAD_PER_GROUP * 64, cudaMemcpyHostToDevice);
    
    uint32_t* d_found;
    cudaMalloc(&d_found, (1 + MAX_FOUND * 8) * 4);
    cudaMemset(d_found, 0, 4);
    
    printf("Launching kernel (1 block, 64 threads)...\n"); fflush(stdout);
    test_full_kernel<<<1, NB_THREAD_PER_GROUP>>>(d_keys, MAX_FOUND, d_found);
    
    printf("Waiting for kernel...\n"); fflush(stdout);
    cudaDeviceSynchronize();
    
    err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("CUDA Error: %s\n", cudaGetErrorString(err));
        return 1;
    }
    
    printf("Kernel complete!\n\n");
    
    uint32_t h_found[1 + 8*10];
    cudaMemcpy(h_found, d_found, 4, cudaMemcpyDeviceToHost);
    printf("Found count: %u\n", h_found[0]);
    
    if (h_found[0] > 0) {
        uint32_t n = h_found[0] > 10 ? 10 : h_found[0];
        cudaMemcpy(h_found, d_found, (1 + n * 8) * 4, cudaMemcpyDeviceToHost);
        for (uint32_t i = 0; i < n; i++) {
            uint32_t* entry = h_found + 1 + i * 8;
            printf("Match %d: tid=%u incr=%d pattern=%d parity=%d\n",
                   i, entry[0], (int32_t)entry[1], (entry[2] >> 8) & 0xFF, entry[2] & 0xFF);
        }
    }
    
    cudaFree(d_keys);
    cudaFree(d_found);
    free(h_keys);
    
    return 0;
}
