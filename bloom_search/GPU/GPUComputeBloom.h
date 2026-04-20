/*
 * GPUComputeBloom.h - Modified VanitySearch GPU kernel with Bloom Filter support
 *
 * This replaces the prefix lookup table with a bloom filter check.
 * The bloom filter is stored in GPU global memory (~200MB).
 *
 * Integration: Include this instead of GPUCompute.h and define USE_BLOOM_FILTER
 */

#ifndef GPU_COMPUTE_BLOOM_H
#define GPU_COMPUTE_BLOOM_H

// ============================================================================
// BLOOM FILTER CONFIGURATION
// ============================================================================

#define BLOOM_MAX_HASHES 24

// Bloom filter data in global memory (set by host)
__device__ uint8_t* d_bloomData;
__device__ uint64_t d_bloomBits;
__device__ uint32_t d_bloomHashes;
__device__ uint32_t d_bloomSeeds[BLOOM_MAX_HASHES];

// ============================================================================
// MURMUR3 HASH (GPU VERSION - matches Python builder)
// ============================================================================

__device__ __forceinline__ uint32_t rotl32_bloom(uint32_t x, int8_t r) {
    return (x << r) | (x >> (32 - r));
}

__device__ __forceinline__ uint32_t murmur3_32(const uint8_t* key, int len, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;

    uint32_t h1 = seed;
    const int nblocks = len / 4;

    // Body
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

    // Tail
    const uint8_t* tail = key + nblocks * 4;
    uint32_t k1 = 0;

    switch (len & 3) {
    case 3: k1 ^= tail[2] << 16;
    case 2: k1 ^= tail[1] << 8;
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
// ============================================================================

__device__ __forceinline__ bool bloom_check(const uint8_t* hash160) {
    // Early exit optimization: check first hash before loop
    uint32_t h = murmur3_32(hash160, 20, d_bloomSeeds[0]);
    uint64_t bitPos = h % d_bloomBits;
    uint64_t bytePos = bitPos >> 3;
    uint8_t bitMask = 1 << (bitPos & 7);

    if (!(d_bloomData[bytePos] & bitMask)) {
        return false;
    }

    // Check remaining hashes
    for (uint32_t i = 1; i < d_bloomHashes; i++) {
        h = murmur3_32(hash160, 20, d_bloomSeeds[i]);
        bitPos = h % d_bloomBits;
        bytePos = bitPos >> 3;
        bitMask = 1 << (bitPos & 7);

        if (!(d_bloomData[bytePos] & bitMask)) {
            return false;
        }
    }

    return true;  // Probably in set (needs CPU verification)
}

// ============================================================================
// BLOOM FILTER CHECK POINT (replaces prefix CHECK_POINT)
// ============================================================================

__device__ __noinline__ void CheckPointBloom(
    uint32_t* _h,
    int32_t incr,
    int32_t endo,
    int32_t mode,
    uint32_t maxFound,
    uint32_t* out
) {
    // Check bloom filter
    if (bloom_check((uint8_t*)_h)) {
        // Potential match - add to output for CPU verification
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

#define CHECK_BLOOM(h, incr, endo, mode) CheckPointBloom(h, incr, endo, mode, maxFound, out)

// ============================================================================
// HASH COMPUTATION WITH BLOOM CHECK (Compressed)
// ============================================================================

__device__ __noinline__ void CheckHashCompBloom(uint64_t *px, uint8_t isOdd, int32_t incr,
                                                 uint32_t maxFound, uint32_t *out) {
    uint32_t h[5];
    _GetHash160Comp(px, isOdd, (uint8_t *)h);
    CHECK_BLOOM(h, incr, 0, 1);

    // Endomorphism #1
    uint64_t pe1x[4];
    ModMult(pe1x, px, _beta);
    _GetHash160Comp(pe1x, isOdd, (uint8_t *)h);
    CHECK_BLOOM(h, incr, 1, 1);

    // Endomorphism #2
    uint64_t pe2x[4];
    ModMult(pe2x, px, _beta2);
    _GetHash160Comp(pe2x, isOdd, (uint8_t *)h);
    CHECK_BLOOM(h, incr, 2, 1);

    // Symmetric points (negate Y)
    isOdd = IsOdd(isOdd);
    _GetHash160Comp(px, isOdd, (uint8_t *)h);
    CHECK_BLOOM(h, -incr, 0, 1);

    _GetHash160Comp(pe1x, isOdd, (uint8_t *)h);
    CHECK_BLOOM(h, -incr, 1, 1);

    _GetHash160Comp(pe2x, isOdd, (uint8_t *)h);
    CHECK_BLOOM(h, -incr, 2, 1);
}

// ============================================================================
// HASH COMPUTATION WITH BLOOM CHECK (Uncompressed)
// ============================================================================

__device__ __noinline__ void CheckHashUncompBloom(uint64_t *px, uint64_t *py, int32_t incr,
                                                   uint32_t maxFound, uint32_t *out) {
    uint32_t h[5];
    _GetHash160(px, py, (uint8_t *)h);
    CHECK_BLOOM(h, incr, 0, 0);

    // Endomorphism #1
    uint64_t pe1x[4];
    ModMult(pe1x, px, _beta);
    _GetHash160(pe1x, py, (uint8_t *)h);
    CHECK_BLOOM(h, incr, 1, 0);

    // Endomorphism #2
    uint64_t pe2x[4];
    ModMult(pe2x, px, _beta2);
    _GetHash160(pe2x, py, (uint8_t *)h);
    CHECK_BLOOM(h, incr, 2, 0);

    // Symmetric points (negate Y)
    uint64_t pyn[4];
    ModNeg256(pyn, py);

    _GetHash160(px, pyn, (uint8_t *)h);
    CHECK_BLOOM(h, -incr, 0, 0);

    _GetHash160(pe1x, pyn, (uint8_t *)h);
    CHECK_BLOOM(h, -incr, 1, 0);

    _GetHash160(pe2x, pyn, (uint8_t *)h);
    CHECK_BLOOM(h, -incr, 2, 0);
}

// ============================================================================
// MAIN CHECK FUNCTION DISPATCHER
// ============================================================================

__device__ __noinline__ void CheckHashBloom(uint32_t mode, uint64_t *px, uint64_t *py, int32_t incr,
                                            uint32_t maxFound, uint32_t *out) {
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

#define CHECK_BLOOM_PREFIX(incr) CheckHashBloom(mode, px, py, j*GRP_SIZE + (incr), maxFound, out)

// ============================================================================
// COMPUTE KEYS WITH BLOOM FILTER (replaces ComputeKeys)
// ============================================================================

__device__ void ComputeKeysBloom(uint32_t mode, uint64_t *startx, uint64_t *starty,
                                  uint32_t maxFound, uint32_t *out) {

    uint64_t dx[GRP_SIZE/2+1][4];
    uint64_t px[4];
    uint64_t py[4];
    uint64_t pyn[4];
    uint64_t sx[4];
    uint64_t sy[4];
    uint64_t dy[4];
    uint64_t _s[4];
    uint64_t _p2[4];

    // Load starting key
    __syncthreads();
    Load256A(sx, startx);
    Load256A(sy, starty);
    Load256(px, sx);
    Load256(py, sy);

    for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {

        // Fill group with delta x
        uint32_t i;
        for (i = 0; i < HSIZE; i++)
            ModSub256(dx[i], Gx[i], sx);
        ModSub256(dx[i], Gx[i], sx);   // For the first point
        ModSub256(dx[i+1], _2Gnx, sx); // For the next center point

        // Compute modular inverse
        _ModInvGrouped(dx);

        // Check starting point
        CHECK_BLOOM_PREFIX(GRP_SIZE / 2);

        ModNeg256(pyn, py);

        for (i = 0; i < HSIZE; i++) {

            // P = StartPoint + i*G
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

            CHECK_BLOOM_PREFIX(GRP_SIZE / 2 + (i + 1));

            // P = StartPoint - i*G
            Load256(px, sx);
            ModSub256(dy, pyn, Gy[i]);

            _ModMult(_s, dy, dx[i]);
            _ModSqr(_p2, _s);

            ModSub256(px, _p2, px);
            ModSub256(px, Gx[i]);

            ModSub256(py, px, Gx[i]);
            _ModMult(py, _s);
            ModSub256(py, Gy[i], py);

            CHECK_BLOOM_PREFIX(GRP_SIZE / 2 - (i + 1));
        }

        // First point (startP - (GRP_SIZE/2)*G)
        Load256(px, sx);
        Load256(py, sy);
        ModNeg256(dy, Gy[i]);
        ModSub256(dy, py);

        _ModMult(_s, dy, dx[i]);
        _ModSqr(_p2, _s);

        ModSub256(px, _p2, px);
        ModSub256(px, Gx[i]);

        ModSub256(py, px, Gx[i]);
        _ModMult(py, _s);
        ModSub256(py, Gy[i], py);

        CHECK_BLOOM_PREFIX(0);

        i++;

        // Next start point (startP + GRP_SIZE*G)
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

        // Update for next iteration
        Load256(sx, px);
        Load256(sy, py);
    }

    // Update starting point
    __syncthreads();
    Store256A(startx, px);
    Store256A(starty, py);
}

#endif // GPU_COMPUTE_BLOOM_H
