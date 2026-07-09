/*
 * GPUBloom.h - GPU-optimized Bloom Filter for batch key matching
 *
 * This implementation is optimized for:
 * - Batch checking (check multiple hash160s at once)
 * - Coalesced memory access (threads in a warp access adjacent memory)
 * - Warp-level parallelism (32 threads cooperate on one check)
 * - Minimal divergence (all threads in warp take same path)
 *
 * At 23 billion keys/second:
 * - Each kernel launch processes ~1M keys
 * - Batch size of 2048 hash160s per warp-group
 * - Expected ~2.3 false positives/second at 0.00001% FP rate
 */

#ifndef GPU_BLOOM_H
#define GPU_BLOOM_H

#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>

// ============================================================================
// BLOOM FILTER CONFIGURATION
// ============================================================================

// These must match build_bloom_filter.py output
#define BLOOM_MAX_HASHES 24

// Batch sizes for GPU processing
// A warp (32 threads) cooperates to check one hash160
// Each thread checks ~1 hash function
#define BLOOM_BATCH_SIZE 2048       // Hash160s to check per block
#define BLOOM_THREADS_PER_BLOCK 256 // Must be multiple of 32

// ============================================================================
// BLOOM FILTER DATA STRUCTURE
// ============================================================================

struct BloomFilterGPU {
    uint64_t numBits;
    uint64_t numBytes;
    uint32_t numHashes;
    uint32_t itemCount;
    uint32_t seeds[BLOOM_MAX_HASHES];
    uint8_t* d_filter;  // Device pointer to bloom filter data
};

// ============================================================================
// MURMUR3 HASH (GPU VERSION)
// ============================================================================

__device__ __forceinline__ uint32_t rotl32(uint32_t x, int8_t r) {
    return (x << r) | (x >> (32 - r));
}

__device__ __forceinline__ uint32_t murmur3_32_gpu(const uint8_t* key, int len, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;

    uint32_t h1 = seed;
    const int nblocks = len / 4;

    // Body
    const uint32_t* blocks = (const uint32_t*)key;
    for (int i = 0; i < nblocks; i++) {
        uint32_t k1 = blocks[i];

        k1 *= c1;
        k1 = rotl32(k1, 15);
        k1 *= c2;

        h1 ^= k1;
        h1 = rotl32(h1, 13);
        h1 = h1 * 5 + 0xe6546b64;
    }

    // Tail
    const uint8_t* tail = key + nblocks * 4;
    uint32_t k1 = 0;

    switch (len & 3) {
    case 3: k1 ^= tail[2] << 16;  // fallthrough
    case 2: k1 ^= tail[1] << 8;   // fallthrough
    case 1: k1 ^= tail[0];
        k1 *= c1;
        k1 = rotl32(k1, 15);
        k1 *= c2;
        h1 ^= k1;
    }

    // Finalization
    h1 ^= len;
    h1 ^= h1 >> 16;
    h1 *= 0x85ebca6b;
    h1 ^= h1 >> 13;
    h1 *= 0xc2b2ae35;
    h1 ^= h1 >> 16;

    return h1;
}

// ============================================================================
// BLOOM FILTER CHECK - SINGLE HASH160
// ============================================================================

__device__ __forceinline__ bool bloom_check_single(
    const uint8_t* hash160,
    const uint8_t* filter,
    uint64_t numBits,
    const uint32_t* seeds,
    int numHashes
) {
    for (int i = 0; i < numHashes; i++) {
        uint32_t h = murmur3_32_gpu(hash160, 20, seeds[i]);
        uint64_t bitPos = h % numBits;
        uint64_t bytePos = bitPos / 8;
        uint8_t bitMask = 1 << (bitPos % 8);

        if (!(filter[bytePos] & bitMask)) {
            return false;  // Definitely not in set
        }
    }
    return true;  // Probably in set (needs CPU verification)
}

// ============================================================================
// BLOOM FILTER CHECK - WARP COOPERATIVE
// Entire warp cooperates to check one hash160 faster
// Each thread checks a subset of hash functions
// ============================================================================

__device__ __forceinline__ bool bloom_check_warp(
    const uint8_t* hash160,
    const uint8_t* filter,
    uint64_t numBits,
    const uint32_t* seeds,
    int numHashes
) {
    int laneId = threadIdx.x & 31;  // Thread index within warp

    // Each thread checks some hash functions
    int hashesPerThread = (numHashes + 31) / 32;
    bool found = true;

    for (int h = 0; h < hashesPerThread && found; h++) {
        int hashIdx = laneId + h * 32;
        if (hashIdx < numHashes) {
            uint32_t hash = murmur3_32_gpu(hash160, 20, seeds[hashIdx]);
            uint64_t bitPos = hash % numBits;
            uint64_t bytePos = bitPos / 8;
            uint8_t bitMask = 1 << (bitPos % 8);

            if (!(filter[bytePos] & bitMask)) {
                found = false;
            }
        }
    }

    // Warp vote: all threads must have found=true
    unsigned int vote = __ballot_sync(0xffffffff, found);
    return vote == 0xffffffff;
}

// ============================================================================
// BATCH BLOOM CHECK KERNEL
// Process multiple hash160s in parallel
// Returns indices of potential matches
// ============================================================================

__global__ void bloom_check_batch_kernel(
    const uint8_t* __restrict__ hash160s,      // Input: array of hash160s (20 bytes each)
    int numHash160s,                            // Number of hash160s to check
    const uint8_t* __restrict__ filter,         // Bloom filter data
    uint64_t numBits,
    const uint32_t* __restrict__ seeds,
    int numHashes,
    uint32_t* __restrict__ matchIndices,        // Output: indices of matches
    uint32_t* __restrict__ matchCount,          // Output: count of matches
    uint32_t maxMatches                         // Maximum matches to store
) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;

    if (idx < numHash160s) {
        const uint8_t* hash160 = hash160s + idx * 20;

        if (bloom_check_single(hash160, filter, numBits, seeds, numHashes)) {
            // Potential match - atomically add to output
            uint32_t pos = atomicAdd(matchCount, 1);
            if (pos < maxMatches) {
                matchIndices[pos] = idx;
            }
        }
    }
}

// ============================================================================
// INTEGRATED CHECK POINT WITH BLOOM FILTER
// This replaces the prefix table lookup in GPUCompute.h
// ============================================================================

__device__ __noinline__ void CheckPointBloom(
    uint32_t* _h,          // hash160 as 5x uint32_t
    int32_t incr,
    int32_t endo,
    int32_t mode,
    const uint8_t* bloomFilter,
    uint64_t bloomBits,
    const uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound,
    uint32_t* out
) {
    uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;

    // Check bloom filter
    if (bloom_check_single((uint8_t*)_h, bloomFilter, bloomBits, bloomSeeds, bloomHashes)) {
        // Potential match - send to CPU for verification
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            out[pos * 8 + 1] = tid;
            out[pos * 8 + 2] = (uint32_t)(incr << 16) | (uint32_t)(mode << 15) | (uint32_t)(endo);
            out[pos * 8 + 3] = _h[0];
            out[pos * 8 + 4] = _h[1];
            out[pos * 8 + 5] = _h[2];
            out[pos * 8 + 6] = _h[3];
            out[pos * 8 + 7] = _h[4];
        }
    }
}

// ============================================================================
// MACRO FOR EASY INTEGRATION
// ============================================================================

#define CHECK_BLOOM(_h, incr, endo, mode) \
    CheckPointBloom(_h, incr, endo, mode, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out)

#endif // GPU_BLOOM_H
