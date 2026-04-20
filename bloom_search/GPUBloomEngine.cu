/*
 * GPU Bloom Filter Search Engine
 * Based on VanitySearch by Jean-Luc PONS
 */

#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

// Include VanitySearch GPU math headers
#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

// Our bloom compute header
#include "GPUBloomCompute.h"

// Kernel: Compute keys and check against prefix bitmap
__global__ void bloom_search_kernel(
    uint64_t *keys,         // Starting points [x0, x1, ..., y0, y1, ...]
    uint8_t *prefixBitmap,  // 512 MB prefix bitmap on GPU
    uint32_t maxFound,
    uint32_t *found
) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * blockDim.x;
    ComputeKeysBitmap(keys + xPtr, keys + yPtr, prefixBitmap, maxFound, found);
}

// Error checking macro
#define CUDA_CHECK(call) { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, cudaGetErrorString(err)); \
        exit(1); \
    } \
}

// GPU Engine class
class GPUBloomEngine {
public:
    int deviceId;
    uint64_t *d_keys;
    uint8_t *d_prefixBitmap;
    uint32_t *d_found;
    uint32_t *h_found;
    
    int gridSizeX;
    int blockSize;
    int nbThread;
    
    GPUBloomEngine(int device, int gridX, int blockSz, uint8_t *h_prefixBitmap) {
        deviceId = device;
        gridSizeX = gridX;
        blockSize = blockSz;
        nbThread = gridSizeX * blockSize;
        
        CUDA_CHECK(cudaSetDevice(deviceId));
        
        // Allocate keys buffer
        size_t keysSize = nbThread * 8 * sizeof(uint64_t); // 8 uint64 per thread (px, py)
        CUDA_CHECK(cudaMalloc(&d_keys, keysSize));
        
        // Allocate and copy prefix bitmap (512 MB)
        printf("GPU #%d: Allocating 512 MB prefix bitmap...\n", deviceId);
        CUDA_CHECK(cudaMalloc(&d_prefixBitmap, 512 * 1024 * 1024));
        CUDA_CHECK(cudaMemcpy(d_prefixBitmap, h_prefixBitmap, 512 * 1024 * 1024, cudaMemcpyHostToDevice));
        
        // Allocate found buffer (max 65536 candidates per launch)
        size_t foundSize = (1 + 65536 * BLOOM_ITEM_SIZE32) * sizeof(uint32_t);
        CUDA_CHECK(cudaMalloc(&d_found, foundSize));
        h_found = (uint32_t *)malloc(foundSize);
        
        printf("GPU #%d: Initialized with grid=%dx%d (%d threads)\n", 
               deviceId, gridSizeX, blockSize, nbThread);
    }
    
    ~GPUBloomEngine() {
        cudaSetDevice(deviceId);
        cudaFree(d_keys);
        cudaFree(d_prefixBitmap);
        cudaFree(d_found);
        free(h_found);
    }
    
    // Set starting keys
    void SetKeys(uint64_t *keys) {
        size_t keysSize = nbThread * 8 * sizeof(uint64_t);
        CUDA_CHECK(cudaMemcpy(d_keys, keys, keysSize, cudaMemcpyHostToDevice));
    }
    
    // Launch search kernel
    int Launch(uint32_t maxFound = 65536) {
        // Clear found counter
        CUDA_CHECK(cudaMemset(d_found, 0, sizeof(uint32_t)));
        
        // Launch kernel
        bloom_search_kernel<<<gridSizeX, blockSize>>>(d_keys, d_prefixBitmap, maxFound, d_found);
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaDeviceSynchronize());
        
        // Get results
        CUDA_CHECK(cudaMemcpy(h_found, d_found, sizeof(uint32_t), cudaMemcpyDeviceToHost));
        uint32_t numFound = h_found[0];
        
        if (numFound > 0) {
            size_t copySize = (1 + numFound * BLOOM_ITEM_SIZE32) * sizeof(uint32_t);
            CUDA_CHECK(cudaMemcpy(h_found, d_found, copySize, cudaMemcpyDeviceToHost));
        }
        
        return numFound;
    }
    
    // Get found candidates
    uint32_t *GetFoundBuffer() { return h_found; }
};
