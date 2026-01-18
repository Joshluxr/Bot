/*
 * GPU Bloom Filter Bitcoin Address Search
 * Wraps VanitySearch GPU compute with bitmap prefix filter
 */

#include <cuda.h>
#include <cuda_runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <atomic>
#include <chrono>
#include <vector>
#include <time.h>

// Include VanitySearch GPU code
#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

#define STEP_SIZE 1024
#define ITEM_SIZE32 8
#define MAX_FOUND 65536

#define CUDA_CHECK(call) { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        fprintf(stderr, "CUDA error at %s:%d: %s\n", __FILE__, __LINE__, cudaGetErrorString(err)); \
        exit(1); \
    } \
}

// ============================================================================
// GPU Bitmap Check - Check hash160 prefix against bitmap
// ============================================================================

__device__ void CheckBitmapPrefix(
    uint8_t *prefixBitmap,
    uint64_t *px,
    uint8_t isOdd,
    int32_t incr,
    uint32_t maxFound,
    uint32_t *out
) {
    uint32_t h[5];
    
    // Get hash160 of compressed pubkey
    _GetHash160Comp(px, isOdd, (uint8_t *)h);
    
    // Extract 32-bit prefix (big-endian)
    uint32_t prefix32 = __byte_perm(h[0], 0, 0x0123);
    uint32_t byteIdx = prefix32 >> 3;
    uint32_t bitIdx = prefix32 & 7;
    
    uint8_t byte = __ldg(&prefixBitmap[byteIdx]);
    if (byte & (1 << bitIdx)) {
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
            out[pos * ITEM_SIZE32 + 1] = tid;
            out[pos * ITEM_SIZE32 + 2] = incr;
            out[pos * ITEM_SIZE32 + 3] = h[0];
            out[pos * ITEM_SIZE32 + 4] = h[1];
            out[pos * ITEM_SIZE32 + 5] = h[2];
            out[pos * ITEM_SIZE32 + 6] = h[3];
            out[pos * ITEM_SIZE32 + 7] = h[4];
        }
    }
    
    // Check endomorphism 1 (beta * x)
    uint64_t pex[4];
    _ModMult(pex, px, _beta);
    _GetHash160Comp(pex, isOdd, (uint8_t *)h);
    prefix32 = __byte_perm(h[0], 0, 0x0123);
    byteIdx = prefix32 >> 3;
    bitIdx = prefix32 & 7;
    byte = __ldg(&prefixBitmap[byteIdx]);
    if (byte & (1 << bitIdx)) {
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
            out[pos * ITEM_SIZE32 + 1] = tid;
            out[pos * ITEM_SIZE32 + 2] = incr | 0x10000;
            out[pos * ITEM_SIZE32 + 3] = h[0];
            out[pos * ITEM_SIZE32 + 4] = h[1];
            out[pos * ITEM_SIZE32 + 5] = h[2];
            out[pos * ITEM_SIZE32 + 6] = h[3];
            out[pos * ITEM_SIZE32 + 7] = h[4];
        }
    }
    
    // Check endomorphism 2 (beta^2 * x)
    _ModMult(pex, px, _beta2);
    _GetHash160Comp(pex, isOdd, (uint8_t *)h);
    prefix32 = __byte_perm(h[0], 0, 0x0123);
    byteIdx = prefix32 >> 3;
    bitIdx = prefix32 & 7;
    byte = __ldg(&prefixBitmap[byteIdx]);
    if (byte & (1 << bitIdx)) {
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
            out[pos * ITEM_SIZE32 + 1] = tid;
            out[pos * ITEM_SIZE32 + 2] = incr | 0x20000;
            out[pos * ITEM_SIZE32 + 3] = h[0];
            out[pos * ITEM_SIZE32 + 4] = h[1];
            out[pos * ITEM_SIZE32 + 5] = h[2];
            out[pos * ITEM_SIZE32 + 6] = h[3];
            out[pos * ITEM_SIZE32 + 7] = h[4];
        }
    }
}

#define CHECK_BITMAP(incr) { \
    CheckBitmapPrefix(prefixBitmap, px, (uint8_t)(py[0] & 1), j*GRP_SIZE + (incr), maxFound, out); \
    CheckBitmapPrefix(prefixBitmap, px, (uint8_t)((py[0] & 1) ^ 1), j*GRP_SIZE - (incr), maxFound, out); \
}

// Main kernel - simplified version that checks each thread starting point
__global__ void bloom_search_kernel(
    uint64_t *startKeys,
    uint8_t *prefixBitmap,
    uint32_t maxFound,
    uint32_t *out
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int xOff = tid * 4;
    int yOff = xOff + (gridDim.x * blockDim.x) * 4;
    
    uint64_t px[4], py[4];
    
    // Load starting point
    Load256A(px, startKeys + xOff);
    Load256A(py, startKeys + yOff);
    
    // Check this point with bitmap (6 checks: 3 endo * 2 symmetric)
    for (int j = 0; j < 1; j++) {
        CHECK_BITMAP(GRP_SIZE / 2);
    }
}

// ============================================================================
// CPU Bloom Filter
// ============================================================================

class BloomFilter {
public:
    uint8_t *bits;
    uint64_t size;
    uint32_t numHashes;
    uint32_t count;
    
    uint32_t murmurhash3(const uint8_t *data, int len, uint32_t seed) {
        uint32_t h = seed;
        for (int i = 0; i < len; i += 4) {
            uint32_t k = 0;
            for (int j = 0; j < 4 && i + j < len; j++) {
                k |= ((uint32_t)data[i + j]) << (j * 8);
            }
            k *= 0xcc9e2d51;
            k = (k << 15) | (k >> 17);
            k *= 0x1b873593;
            h ^= k;
            h = (h << 13) | (h >> 19);
            h = h * 5 + 0xe6546b64;
        }
        h ^= len;
        h ^= h >> 16;
        h *= 0x85ebca6b;
        h ^= h >> 13;
        h *= 0xc2b2ae35;
        h ^= h >> 16;
        return h;
    }
    
    bool load(const char *filename) {
        FILE *f = fopen(filename, "rb");
        if (!f) return false;
        
        // Read header: magic (4) + size (8) + num_hashes (4) + count (4)
        char magic[4];
        if (fread(magic, 1, 4, f) != 4) { fclose(f); return false; }
        if (memcmp(magic, "BLM1", 4) != 0) { 
            printf("Invalid bloom filter magic\n"); 
            fclose(f); 
            return false; 
        }
        
        if (fread(&size, sizeof(size), 1, f) != 1) { fclose(f); return false; }
        if (fread(&numHashes, sizeof(numHashes), 1, f) != 1) { fclose(f); return false; }
        if (fread(&count, sizeof(count), 1, f) != 1) { fclose(f); return false; }
        
        uint64_t byteSize = (size + 7) / 8;
        bits = (uint8_t *)malloc(byteSize);
        if (!bits) { fclose(f); return false; }
        if (fread(bits, 1, byteSize, f) != byteSize) { fclose(f); free(bits); return false; }
        fclose(f);
        return true;
    }
    
    bool contains(const uint8_t *hash160) {
        for (uint32_t i = 0; i < numHashes; i++) {
            uint32_t h = murmurhash3(hash160, 20, i);
            uint64_t idx = h % size;
            if (!(bits[idx / 8] & (1 << (idx % 8)))) return false;
        }
        return true;
    }
};

// ============================================================================
// Main
// ============================================================================

int main(int argc, char **argv) {
    if (argc < 3) {
        printf("GPU Bloom Filter Bitcoin Address Search\n");
        printf("=========================================\n\n");
        printf("Usage: %s <prefix_bitmap> <bloom_filter> [-g gpuids] [-t seconds]\n", argv[0]);
        return 1;
    }
    
    const char *bitmapFile = argv[1];
    const char *bloomFile = argv[2];
    std::vector<int> gpuIds = {0};
    int runTime = 30;
    
    for (int i = 3; i < argc; i++) {
        if (strcmp(argv[i], "-g") == 0 && i+1 < argc) {
            gpuIds.clear();
            char *token = strtok(argv[++i], ",");
            while (token) {
                gpuIds.push_back(atoi(token));
                token = strtok(NULL, ",");
            }
        } else if (strcmp(argv[i], "-t") == 0 && i+1 < argc) {
            runTime = atoi(argv[++i]);
        }
    }
    
    printf("GPU Bloom Filter Bitcoin Address Search\n");
    printf("=========================================\n\n");
    printf("GPUs: ");
    for (int id : gpuIds) printf("%d ", id);
    printf("\nRun time: %d seconds\n\n", runTime);
    
    // Load prefix bitmap
    printf("Loading prefix bitmap...\n");
    uint8_t *h_prefixBitmap = NULL;
    uint32_t addrCount = 0;
    FILE *f = fopen(bitmapFile, "rb");
    if (!f) { printf("Failed to open bitmap file\n"); return 1; }
    
    // Read header: magic (4) + count (4)
    char magic[4];
    if (fread(magic, 1, 4, f) != 4) { printf("Failed to read bitmap magic\n"); fclose(f); return 1; }
    if (memcmp(magic, "PFX1", 4) != 0) { printf("Invalid bitmap magic\n"); fclose(f); return 1; }
    if (fread(&addrCount, sizeof(addrCount), 1, f) != 1) { printf("Failed to read count\n"); fclose(f); return 1; }
    
    h_prefixBitmap = (uint8_t *)malloc(512 * 1024 * 1024);
    if (!h_prefixBitmap) { printf("Failed to allocate bitmap memory\n"); fclose(f); return 1; }
    size_t r = fread(h_prefixBitmap, 1, 512 * 1024 * 1024, f);
    fclose(f);
    printf("  Loaded bitmap for %u addresses (%zu bytes read)\n", addrCount, r);
    
    // Load bloom filter
    BloomFilter bloomFilter;
    printf("Loading bloom filter...\n");
    if (!bloomFilter.load(bloomFile)) { printf("Failed to load bloom filter\n"); return 1; }
    printf("  %lu bits, %u hashes, %u addresses\n\n", bloomFilter.size, bloomFilter.numHashes, bloomFilter.count);
    
    // Initialize GPUs
    int gridSize = 512;
    int blockSize = 128;
    int nbThread = gridSize * blockSize;
    
    std::vector<uint64_t *> d_keys(gpuIds.size());
    std::vector<uint8_t *> d_bitmap(gpuIds.size());
    std::vector<uint32_t *> d_found(gpuIds.size());
    std::vector<uint32_t *> h_found(gpuIds.size());
    
    for (size_t i = 0; i < gpuIds.size(); i++) {
        int id = gpuIds[i];
        CUDA_CHECK(cudaSetDevice(id));
        
        cudaDeviceProp prop;
        cudaGetDeviceProperties(&prop, id);
        printf("GPU #%d: %s (%d MPs)\n", id, prop.name, prop.multiProcessorCount);
        
        // Keys: each thread needs 4 uint64 for x and 4 for y = 8 per thread
        CUDA_CHECK(cudaMalloc(&d_keys[i], nbThread * 8 * sizeof(uint64_t)));
        CUDA_CHECK(cudaMalloc(&d_bitmap[i], 512 * 1024 * 1024));
        CUDA_CHECK(cudaMalloc(&d_found[i], (1 + MAX_FOUND * ITEM_SIZE32) * sizeof(uint32_t)));
        
        CUDA_CHECK(cudaMemcpy(d_bitmap[i], h_prefixBitmap, 512 * 1024 * 1024, cudaMemcpyHostToDevice));
        
        h_found[i] = (uint32_t *)malloc((1 + MAX_FOUND * ITEM_SIZE32) * sizeof(uint32_t));
        
        // Initialize random starting keys
        uint64_t *h_keys = (uint64_t *)malloc(nbThread * 8 * sizeof(uint64_t));
        srand(time(NULL) + id);
        for (int j = 0; j < nbThread * 8; j++) {
            h_keys[j] = ((uint64_t)rand() << 32) | rand();
        }
        CUDA_CHECK(cudaMemcpy(d_keys[i], h_keys, nbThread * 8 * sizeof(uint64_t), cudaMemcpyHostToDevice));
        free(h_keys);
    }
    
    printf("\nSearching...\n\n");
    
    std::atomic<uint64_t> totalKeys(0);
    std::atomic<uint64_t> prefixCandidates(0);
    std::atomic<uint64_t> bloomPasses(0);
    
    auto startTime = std::chrono::high_resolution_clock::now();
    
    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - startTime).count();
        if (elapsed >= runTime) break;
        
        // Launch kernels
        for (size_t i = 0; i < gpuIds.size(); i++) {
            CUDA_CHECK(cudaSetDevice(gpuIds[i]));
            CUDA_CHECK(cudaMemset(d_found[i], 0, sizeof(uint32_t)));
            bloom_search_kernel<<<gridSize, blockSize>>>(d_keys[i], d_bitmap[i], MAX_FOUND, d_found[i]);
        }
        
        // Collect results
        for (size_t i = 0; i < gpuIds.size(); i++) {
            CUDA_CHECK(cudaSetDevice(gpuIds[i]));
            cudaError_t err = cudaDeviceSynchronize();
            if (err != cudaSuccess) {
                printf("Kernel error on GPU %d: %s\n", gpuIds[i], cudaGetErrorString(err));
                continue;
            }
            
            CUDA_CHECK(cudaMemcpy(h_found[i], d_found[i], sizeof(uint32_t), cudaMemcpyDeviceToHost));
            uint32_t numFound = h_found[i][0];
            
            if (numFound > 0) {
                if (numFound > MAX_FOUND) numFound = MAX_FOUND;
                size_t copySize = (1 + numFound * ITEM_SIZE32) * sizeof(uint32_t);
                CUDA_CHECK(cudaMemcpy(h_found[i], d_found[i], copySize, cudaMemcpyDeviceToHost));
                prefixCandidates += numFound;
                
                // Check candidates against bloom filter
                for (uint32_t j = 0; j < numFound; j++) {
                    uint8_t hash160[20];
                    uint32_t *item = &h_found[i][j * ITEM_SIZE32 + 1];
                    for (int k = 0; k < 5; k++) {
                        uint32_t h = item[2 + k];
                        hash160[k*4+0] = (h >> 24) & 0xff;
                        hash160[k*4+1] = (h >> 16) & 0xff;
                        hash160[k*4+2] = (h >> 8) & 0xff;
                        hash160[k*4+3] = h & 0xff;
                    }
                    if (bloomFilter.contains(hash160)) {
                        bloomPasses++;
                    }
                }
            }
            
            // Each thread checks 6 addresses (3 endo * 2 symmetric)
            totalKeys += (uint64_t)nbThread * 6;
        }
        
        double rate = totalKeys.load() / ((double)elapsed + 0.001) / 1e9;
        printf("\r[%3lds] %.2f GKey/s | Prefix: %lu | Bloom: %lu", 
               elapsed, rate, prefixCandidates.load(), bloomPasses.load());
        fflush(stdout);
    }
    
    printf("\n\n");
    printf("=========================================\n");
    printf("Final Results:\n");
    printf("  Total keys checked: %lu\n", totalKeys.load());
    printf("  Prefix bitmap hits: %lu\n", prefixCandidates.load());
    printf("  Bloom filter passes: %lu\n", bloomPasses.load());
    printf("  Average rate: %.2f GKey/s\n", totalKeys.load() / (double)runTime / 1e9);
    printf("=========================================\n");
    
    // Cleanup
    for (size_t i = 0; i < gpuIds.size(); i++) {
        CUDA_CHECK(cudaSetDevice(gpuIds[i]));
        CUDA_CHECK(cudaFree(d_keys[i]));
        CUDA_CHECK(cudaFree(d_bitmap[i]));
        CUDA_CHECK(cudaFree(d_found[i]));
        free(h_found[i]);
    }
    free(h_prefixBitmap);
    
    return 0;
}
