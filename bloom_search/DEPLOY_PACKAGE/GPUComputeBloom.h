/*
 * GPUComputeBloom.h - Bloom filter support for VanitySearch GPU kernel
 *
 * This file adds bloom filter checking capability to VanitySearch.
 * Include this file in GPUEngine.cu and call the bloom filter functions.
 *
 * Usage:
 *   1. Load bloom filter data to GPU with cudaMalloc/cudaMemcpy
 *   2. Set d_bloomData, d_bloomBits, d_bloomHashes, d_bloomSeeds
 *   3. Use bloom_check() instead of prefix lookup
 */

#ifndef GPU_COMPUTE_BLOOM_H
#define GPU_COMPUTE_BLOOM_H

// ============================================================================
// BLOOM FILTER DEVICE VARIABLES
// Set these from host before launching kernel
// ============================================================================

__device__ uint8_t* d_bloomData;      // Bloom filter bit array
__device__ uint64_t d_bloomBits;       // Number of bits in filter
__device__ uint32_t d_bloomHashes;     // Number of hash functions
__device__ uint32_t d_bloomSeeds[24];  // Seeds for hash functions

// ============================================================================
// MURMUR3 HASH (32-bit, matches Python builder)
// ============================================================================

__device__ __forceinline__ uint32_t rotl32_bloom(uint32_t x, int8_t r) {
    return (x << r) | (x >> (32 - r));
}

__device__ __forceinline__ uint32_t murmur3_32(const uint8_t* key, int len, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;

    uint32_t h1 = seed;
    const int nblocks = len / 4;

    // Process 4-byte blocks
    const uint32_t* blocks = (const uint32_t*)key;
    for (int i = 0; i < nblocks; i++) {
        uint32_t k1 = blocks[i];

        k1 *= c1;
        k1 = rotl32_bloom(k1, 15);
        k1 *= c2;

        h1 ^= k1;
        h1 = rotl32_bloom(h1, 13);
        h1 = h1 * 5 + 0xe6546b64;
    }

    // Process remaining bytes
    const uint8_t* tail = key + nblocks * 4;
    uint32_t k1 = 0;

    switch (len & 3) {
    case 3: k1 ^= tail[2] << 16; // fallthrough
    case 2: k1 ^= tail[1] << 8;  // fallthrough
    case 1: k1 ^= tail[0];
        k1 *= c1;
        k1 = rotl32_bloom(k1, 15);
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
// BLOOM FILTER CHECK
// Returns true if hash160 is probably in the set (may be false positive)
// Returns false if hash160 is definitely not in the set
// ============================================================================

__device__ __forceinline__ bool bloom_check(const uint8_t* hash160) {
    // Check each hash function
    for (uint32_t i = 0; i < d_bloomHashes; i++) {
        uint32_t h = murmur3_32(hash160, 20, d_bloomSeeds[i]);
        uint64_t bitPos = h % d_bloomBits;
        uint64_t bytePos = bitPos >> 3;
        uint8_t bitMask = 1 << (bitPos & 7);

        if (!(d_bloomData[bytePos] & bitMask)) {
            return false;  // Definitely not in set
        }
    }
    return true;  // Probably in set
}

// ============================================================================
// BLOOM CHECK POINT - Records potential match for CPU verification
// ============================================================================

__device__ __noinline__ void CheckPointBloom(
    uint32_t* _h,         // hash160 as 5 uint32_t
    int32_t incr,         // Key increment from starting point
    int32_t endo,         // Endomorphism index (0, 1, or 2)
    int32_t mode,         // 0=uncompressed, 1=compressed
    uint32_t maxFound,    // Max matches to record
    uint32_t* out         // Output buffer
) {
    if (bloom_check((uint8_t*)_h)) {
        // Record potential match
        uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
        uint32_t pos = atomicAdd(out, 1);

        if (pos < maxFound) {
            out[pos * ITEM_SIZE32 + 1] = tid;
            out[pos * ITEM_SIZE32 + 2] = (uint32_t)(incr << 16) | (uint32_t)(mode << 15) | (uint32_t)(endo);
            out[pos * ITEM_SIZE32 + 3] = _h[0];
            out[pos * ITEM_SIZE32 + 4] = _h[1];
            out[pos * ITEM_SIZE32 + 5] = _h[2];
            out[pos * ITEM_SIZE32 + 6] = _h[3];
            out[pos * ITEM_SIZE32 + 7] = _h[4];
        }
    }
}

// Macro for easy integration
#define CHECK_POINT_BLOOM(h, incr, endo, mode) \
    CheckPointBloom(h, incr, endo, mode, maxFound, out)

// ============================================================================
// HASH CHECK FUNCTIONS WITH BLOOM FILTER
// These replace the prefix-based check functions
// ============================================================================

// Check compressed public key against bloom filter
__device__ __noinline__ void CheckHashCompBloom(
    uint64_t *px,
    uint8_t isOdd,
    int32_t incr,
    uint32_t maxFound,
    uint32_t *out
) {
    uint32_t h[5];

    // Original point
    _GetHash160Comp(px, isOdd, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, incr, 0, 1);

    // Endomorphism #1: multiply x by beta
    uint64_t pe1x[4];
    ModMult(pe1x, px, _beta);
    _GetHash160Comp(pe1x, isOdd, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, incr, 1, 1);

    // Endomorphism #2: multiply x by beta^2
    uint64_t pe2x[4];
    ModMult(pe2x, px, _beta2);
    _GetHash160Comp(pe2x, isOdd, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, incr, 2, 1);

    // Symmetric point (negate y)
    isOdd = IsOdd(isOdd);

    _GetHash160Comp(px, isOdd, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, -incr, 0, 1);

    _GetHash160Comp(pe1x, isOdd, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, -incr, 1, 1);

    _GetHash160Comp(pe2x, isOdd, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, -incr, 2, 1);
}

// Check uncompressed public key against bloom filter
__device__ __noinline__ void CheckHashUncompBloom(
    uint64_t *px,
    uint64_t *py,
    int32_t incr,
    uint32_t maxFound,
    uint32_t *out
) {
    uint32_t h[5];
    uint64_t pe1x[4], pe2x[4], pyn[4];

    // Original point
    _GetHash160(px, py, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, incr, 0, 0);

    // Endomorphisms
    ModMult(pe1x, px, _beta);
    _GetHash160(pe1x, py, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, incr, 1, 0);

    ModMult(pe2x, px, _beta2);
    _GetHash160(pe2x, py, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, incr, 2, 0);

    // Symmetric points
    ModNeg256(pyn, py);

    _GetHash160(px, pyn, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, -incr, 0, 0);

    _GetHash160(pe1x, pyn, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, -incr, 1, 0);

    _GetHash160(pe2x, pyn, (uint8_t *)h);
    CHECK_POINT_BLOOM(h, -incr, 2, 0);
}

// Main dispatch function
__device__ __noinline__ void CheckHashBloom(
    uint32_t mode,
    uint64_t *px,
    uint64_t *py,
    int32_t incr,
    uint32_t maxFound,
    uint32_t *out
) {
    switch (mode) {
    case SEARCH_COMPRESSED:
        CheckHashCompBloom(px, (uint8_t)(py[0] & 1), incr, maxFound, out);
        break;
    case SEARCH_UNCOMPRESSED:
        CheckHashUncompBloom(px, py, incr, maxFound, out);
        break;
    case SEARCH_BOTH:
        CheckHashCompBloom(px, (uint8_t)(py[0] & 1), incr, maxFound, out);
        CheckHashUncompBloom(px, py, incr, maxFound, out);
        break;
    }
}

// Macro for use in ComputeKeys
#define CHECK_BLOOM_HASH(incr) \
    CheckHashBloom(mode, px, py, j*GRP_SIZE + (incr), maxFound, out)

#endif // GPU_COMPUTE_BLOOM_H
