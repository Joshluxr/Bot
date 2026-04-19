// Minimal test to trace kernel execution
#include <stdio.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>

#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

#define NB_THREAD_PER_GROUP 64
#define GRP_SIZE 1024
#define HSIZE (GRP_SIZE/2)

// Base58 alphabet
__device__ __constant__ char pszBase58[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

__device__ __constant__ uint64_t d_targetH160[3]; // First 20 bytes of target hash160

__device__ __noinline__ void _GetAddress(int type, uint32_t *hash, char *b58Add) {
    uint32_t addBytes[16];
    uint32_t s[16];
    unsigned char A[25];
    unsigned char *addPtr = A;
    int retPos = 0;
    unsigned char digits[128];
    
    A[0] = (type == 0) ? 0x00 : 0x05;
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

__global__ void trace_kernel(uint64_t* keys, uint32_t* output) {
    uint32_t tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (tid != 0) return; // Only thread 0
    
    // Load starting point
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    
    uint64_t sx[4], sy[4], px[4], py[4];
    Load256A(sx, keys + xPtr);
    Load256A(sy, keys + yPtr);
    Load256(px, sx);
    Load256(py, sy);
    
    // Store the X coordinate for debugging
    output[0] = 0xDEAD;  // Magic marker
    output[1] = (uint32_t)px[0];
    output[2] = (uint32_t)(px[0] >> 32);
    output[3] = (uint32_t)px[1];
    output[4] = (uint32_t)(px[1] >> 32);
    output[5] = (uint32_t)px[2];
    output[6] = (uint32_t)(px[2] >> 32);
    output[7] = (uint32_t)px[3];
    output[8] = (uint32_t)(px[3] >> 32);
    
    // Now compute the hash160 (even parity - 02 prefix)
    uint32_t h1[5], h2[5];
    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);
    
    // Store both hashes
    output[9] = h1[0];
    output[10] = h1[1];
    output[11] = h1[2];
    output[12] = h1[3];
    output[13] = h1[4];
    
    output[14] = h2[0];
    output[15] = h2[1];
    output[16] = h2[2];
    output[17] = h2[3];
    output[18] = h2[4];
    
    // Get addresses
    char addr1[40], addr2[40];
    _GetAddress(0, h1, addr1);
    _GetAddress(0, h2, addr2);
    
    // Store first 20 chars of each address (as 5 uint32s)
    for (int i = 0; i < 20; i++) {
        ((char*)&output[19])[i] = addr1[i];
    }
    for (int i = 0; i < 20; i++) {
        ((char*)&output[24])[i] = addr2[i];
    }
    
    output[29] = 0xBEEF; // End marker
}

// secp256k1 constants
static const uint64_t SECP_P[4] = {
    0xFFFFFFFEFFFFFC2FULL, 0xFFFFFFFFFFFFFFFFULL,
    0xFFFFFFFFFFFFFFFFULL, 0xFFFFFFFFFFFFFFFFULL
};

static const uint64_t SECP_GX[4] = {
    0x59F2815B16F81798ULL, 0x029BFCDB2DCE28D9ULL,
    0x55A06295CE870B07ULL, 0x79BE667EF9DCBBACULL
};

static const uint64_t SECP_GY[4] = {
    0x9C47D08FFB10D4B8ULL, 0xFD17B448A6855419ULL,
    0x5DA4FBFC0E1108A8ULL, 0x483ADA7726A3C465ULL
};

int main() {
    printf("=== Kernel Trace Test ===\n");
    printf("Testing if kernel reads correct key for thread 0\n\n");
    
    // Set stack limit
    cudaDeviceSetLimit(cudaLimitStackSize, 36 * 1024);
    
    // Allocate host memory for 1 thread (64 bytes = 8 uint64s)
    uint64_t* h_keys = (uint64_t*)malloc(64);
    
    // Store G point (private key 1) using strided layout for block 0, thread 0
    // For thread 0: xBase = 0, yBase = 4*64 = 256
    // With stride = 64, positions are:
    // X[0] at index 0, X[1] at index 64, X[2] at index 128, X[3] at index 192
    // Y[0] at index 256, Y[1] at index 320, ...
    
    // But with just 1 thread and simplified storage, we need to match what the main program does
    // Let's store directly: X at [0-3], Y at [4-7]
    // Actually, for the trace we need proper strided layout
    
    // Actually, let's allocate for a full block of 64 threads
    free(h_keys);
    h_keys = (uint64_t*)malloc(NB_THREAD_PER_GROUP * 64);  // 64 threads * 64 bytes each
    memset(h_keys, 0, NB_THREAD_PER_GROUP * 64);
    
    // Store G point for thread 0 in strided format
    // blockBase = 0, tidInBlock = 0
    // xBase = 0, yBase = 4 * 64 = 256
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
    
    printf("Stored G point for thread 0:\n");
    printf("  GX = %016lx %016lx %016lx %016lx\n", SECP_GX[3], SECP_GX[2], SECP_GX[1], SECP_GX[0]);
    printf("  GY = %016lx %016lx %016lx %016lx\n", SECP_GY[3], SECP_GY[2], SECP_GY[1], SECP_GY[0]);
    printf("\n");
    
    // Copy to device
    uint64_t* d_keys;
    cudaMalloc(&d_keys, NB_THREAD_PER_GROUP * 64);
    cudaMemcpy(d_keys, h_keys, NB_THREAD_PER_GROUP * 64, cudaMemcpyHostToDevice);
    
    // Allocate output
    uint32_t* d_output;
    cudaMalloc(&d_output, 128);
    cudaMemset(d_output, 0, 128);
    
    // Launch kernel with 1 block of 64 threads
    trace_kernel<<<1, NB_THREAD_PER_GROUP>>>(d_keys, d_output);
    cudaDeviceSynchronize();
    
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("CUDA Error: %s\n", cudaGetErrorString(err));
        return 1;
    }
    
    // Copy output back
    uint32_t h_output[32];
    cudaMemcpy(h_output, d_output, 128, cudaMemcpyDeviceToHost);
    
    printf("Kernel output:\n");
    printf("  Magic marker: 0x%X (expected 0xDEAD)\n", h_output[0]);
    
    uint64_t readX[4];
    readX[0] = ((uint64_t)h_output[2] << 32) | h_output[1];
    readX[1] = ((uint64_t)h_output[4] << 32) | h_output[3];
    readX[2] = ((uint64_t)h_output[6] << 32) | h_output[5];
    readX[3] = ((uint64_t)h_output[8] << 32) | h_output[7];
    
    printf("  Read X  = %016lx %016lx %016lx %016lx\n", readX[3], readX[2], readX[1], readX[0]);
    printf("  Expect  = %016lx %016lx %016lx %016lx\n", SECP_GX[3], SECP_GX[2], SECP_GX[1], SECP_GX[0]);
    
    bool xMatch = (readX[0] == SECP_GX[0]) && (readX[1] == SECP_GX[1]) && 
                  (readX[2] == SECP_GX[2]) && (readX[3] == SECP_GX[3]);
    printf("  X coordinate match: %s\n\n", xMatch ? "YES" : "NO");
    
    printf("Hash160 (even parity - 02 prefix):\n");
    printf("  ");
    for (int i = 0; i < 5; i++) {
        uint32_t h = h_output[9 + i];
        printf("%02x%02x%02x%02x", h & 0xFF, (h >> 8) & 0xFF, (h >> 16) & 0xFF, (h >> 24) & 0xFF);
    }
    printf("\n");
    printf("  Expected: 751e76e8199196d454941c45d1b3a323f1433bd6\n\n");
    
    printf("Hash160 (odd parity - 03 prefix):\n");
    printf("  ");
    for (int i = 0; i < 5; i++) {
        uint32_t h = h_output[14 + i];
        printf("%02x%02x%02x%02x", h & 0xFF, (h >> 8) & 0xFF, (h >> 16) & 0xFF, (h >> 24) & 0xFF);
    }
    printf("\n\n");
    
    printf("Address (even parity): %.20s\n", (char*)&h_output[19]);
    printf("Expected:              1BgGZ9tcN4rm9KBzDn7K\n\n");
    
    printf("Address (odd parity):  %.20s\n", (char*)&h_output[24]);
    
    printf("End marker: 0x%X (expected 0xBEEF)\n", h_output[29]);
    
    cudaFree(d_keys);
    cudaFree(d_output);
    free(h_keys);
    
    return 0;
}
