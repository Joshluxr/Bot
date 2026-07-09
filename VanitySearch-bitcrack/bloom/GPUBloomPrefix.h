/*
 * GPUBloomPrefix.h - Two-stage bloom filter: 16-bit prefix + full bloom
 * Stage 1: 8KB prefix table (fits in L1 cache) - instant rejection
 * Stage 2: Full bloom filter check only if prefix matches
 */
#ifndef GPU_BLOOM_PREFIX_H
#define GPU_BLOOM_PREFIX_H

__device__ __forceinline__ uint32_t murmur3_pfx(const uint8_t* key, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51, c2 = 0x1b873593;
    uint32_t h1 = seed;
    const uint32_t* b = (const uint32_t*)key;
    uint32_t k1;
    k1 = b[0]; k1 *= c1; k1 = (k1<<15)|(k1>>17); k1 *= c2; h1 ^= k1; h1 = (h1<<13)|(h1>>19); h1 = h1*5+0xe6546b64;
    k1 = b[1]; k1 *= c1; k1 = (k1<<15)|(k1>>17); k1 *= c2; h1 ^= k1; h1 = (h1<<13)|(h1>>19); h1 = h1*5+0xe6546b64;
    k1 = b[2]; k1 *= c1; k1 = (k1<<15)|(k1>>17); k1 *= c2; h1 ^= k1; h1 = (h1<<13)|(h1>>19); h1 = h1*5+0xe6546b64;
    k1 = b[3]; k1 *= c1; k1 = (k1<<15)|(k1>>17); k1 *= c2; h1 ^= k1; h1 = (h1<<13)|(h1>>19); h1 = h1*5+0xe6546b64;
    k1 = b[4]; k1 *= c1; k1 = (k1<<15)|(k1>>17); k1 *= c2; h1 ^= k1; h1 = (h1<<13)|(h1>>19); h1 = h1*5+0xe6546b64;
    h1 ^= 20; h1 ^= h1>>16; h1 *= 0x85ebca6b; h1 ^= h1>>13; h1 *= 0xc2b2ae35; h1 ^= h1>>16;
    return h1;
}

__device__ __forceinline__ bool bloom_check_prefix(
    const uint8_t* h160,
    const uint8_t* __restrict__ prefixTable,  // 8KB prefix table
    const uint32_t* __restrict__ bloomFilter,
    uint64_t bloomBits,
    const uint32_t* __restrict__ seeds,
    int numHashes
) {
    // Stage 1: Check 16-bit prefix (8KB table, fits in L1)
    uint32_t prefix16 = (h160[0] << 8) | h160[1];
    uint32_t prefixByte = prefix16 >> 3;
    uint32_t prefixBit = prefix16 & 7;
    if (!(__ldg(&prefixTable[prefixByte]) & (1 << prefixBit))) {
        return false;  // Fast rejection - no address has this prefix
    }
    
    // Stage 2: Full bloom filter check (only ~0.15% of keys reach here)
    for (int i = 0; i < numHashes; i++) {
        uint32_t h = murmur3_pfx(h160, __ldg(&seeds[i]));
        uint64_t bitPos = (uint64_t)h % bloomBits;
        uint32_t word = __ldg(&bloomFilter[bitPos >> 5]);
        if (!(word & (1U << (bitPos & 31)))) {
            return false;
        }
    }
    return true;
}

__device__ __noinline__ void CheckPointBloomPrefix(
    uint32_t* _h,
    int32_t incr,
    int32_t endo,
    int32_t mode,
    const uint8_t* __restrict__ prefixTable,
    const uint32_t* __restrict__ bloomFilter,
    uint64_t bloomBits,
    const uint32_t* __restrict__ bloomSeeds,
    int bloomHashes,
    uint32_t maxFound,
    uint32_t* out,
    int type
) {
    if (!bloom_check_prefix((uint8_t*)_h, prefixTable, bloomFilter, bloomBits, bloomSeeds, bloomHashes)) {
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
