/*
 * GPUBloom.h - Optimized GPU Bloom Filter for hash160 matching
 * Reduced to 8 hashes for better GPU throughput
 */
#ifndef GPU_BLOOM_H
#define GPU_BLOOM_H

__device__ __forceinline__ uint32_t murmur3_gpu(const uint8_t* key, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;
    uint32_t h1 = seed;
    const uint32_t* blocks = (const uint32_t*)key;
    
    // Unrolled for 20 bytes (5 x 4-byte blocks)
    uint32_t k1;
    
    k1 = blocks[0]; k1 *= c1; k1 = (k1 << 15) | (k1 >> 17); k1 *= c2;
    h1 ^= k1; h1 = (h1 << 13) | (h1 >> 19); h1 = h1 * 5 + 0xe6546b64;
    
    k1 = blocks[1]; k1 *= c1; k1 = (k1 << 15) | (k1 >> 17); k1 *= c2;
    h1 ^= k1; h1 = (h1 << 13) | (h1 >> 19); h1 = h1 * 5 + 0xe6546b64;
    
    k1 = blocks[2]; k1 *= c1; k1 = (k1 << 15) | (k1 >> 17); k1 *= c2;
    h1 ^= k1; h1 = (h1 << 13) | (h1 >> 19); h1 = h1 * 5 + 0xe6546b64;
    
    k1 = blocks[3]; k1 *= c1; k1 = (k1 << 15) | (k1 >> 17); k1 *= c2;
    h1 ^= k1; h1 = (h1 << 13) | (h1 >> 19); h1 = h1 * 5 + 0xe6546b64;
    
    k1 = blocks[4]; k1 *= c1; k1 = (k1 << 15) | (k1 >> 17); k1 *= c2;
    h1 ^= k1; h1 = (h1 << 13) | (h1 >> 19); h1 = h1 * 5 + 0xe6546b64;
    
    h1 ^= 20;
    h1 ^= h1 >> 16; h1 *= 0x85ebca6b;
    h1 ^= h1 >> 13; h1 *= 0xc2b2ae35;
    h1 ^= h1 >> 16;
    return h1;
}

__device__ __forceinline__ bool bloom_check(
    const uint8_t* hash160,
    const uint8_t* filter,
    uint64_t numBits,
    const uint32_t* seeds,
    int numHashes
) {
    // Check all hashes - early exit on first miss
    for (int i = 0; i < numHashes; i++) {
        uint32_t h = murmur3_gpu(hash160, seeds[i]);
        uint64_t bitPos = (uint64_t)h % numBits;
        if (!(filter[bitPos >> 3] & (1 << (bitPos & 7)))) {
            return false;
        }
    }
    return true;
}

__device__ __noinline__ void CheckPointBloom(
    uint32_t* _h,
    int32_t incr,
    int32_t endo,
    int32_t mode,
    const uint8_t* bloomFilter,
    uint64_t bloomBits,
    const uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound,
    uint32_t* out,
    int type
) {
    if (!bloom_check((uint8_t*)_h, bloomFilter, bloomBits, bloomSeeds, bloomHashes)) {
        return;
    }
    uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
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

#endif
