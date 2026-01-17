/*
 * GPUComputeBloom.h - GPU kernel for bloom filter-based address matching
 *
 * This is a modified version of VanitySearch's GPUCompute.h that:
 * 1. Uses bloom filter instead of prefix matching
 * 2. Checks both compressed and uncompressed keys
 * 3. Uses batch-optimized memory access patterns
 *
 * Key optimizations:
 * - Bloom filter in global memory with L2 cache hints
 * - Coalesced hash160 computation
 * - Warp-level bloom filter checking
 * - Reduced memory traffic with early exit
 */

#ifndef GPU_COMPUTE_BLOOM_H
#define GPU_COMPUTE_BLOOM_H

#include <cuda.h>
#include <cuda_runtime.h>
#include "GPUBloom.h"
#include "../hash/sha256.h"
#include "../hash/ripemd160.h"

// ============================================================================
// CONFIGURATION
// ============================================================================

#define GRP_SIZE 1024
#define STEP_SIZE 1024
#define HSIZE (GRP_SIZE / 2 - 1)

// Item size in output buffer (8 uint32_t per match)
#define ITEM_SIZE32 8

// ============================================================================
// BLOOM FILTER GLOBAL MEMORY
// ============================================================================

// These are set by the host before kernel launch
__device__ __constant__ uint64_t d_bloomBits;
__device__ __constant__ uint32_t d_bloomHashes;
__device__ __constant__ uint32_t d_bloomSeeds[24];

// Bloom filter data pointer (in global memory)
__device__ uint8_t* d_bloomFilter;

// ============================================================================
// HASH160 COMPUTATION (SHA256 + RIPEMD160)
// ============================================================================

// Compute hash160 of a public key
__device__ void ComputeHash160(
    uint64_t* px,      // Public key X (4 x uint64_t)
    uint64_t* py,      // Public key Y (4 x uint64_t)
    bool compressed,
    uint32_t* hash160  // Output: 5 x uint32_t = 20 bytes
) {
    uint8_t pubKey[65];
    uint8_t sha[32];

    if (compressed) {
        // Compressed: 0x02/0x03 + X (33 bytes)
        pubKey[0] = (py[0] & 1) ? 0x03 : 0x02;
        for (int i = 0; i < 4; i++) {
            uint64_t v = px[3 - i];
            pubKey[1 + i * 8 + 0] = (v >> 56) & 0xFF;
            pubKey[1 + i * 8 + 1] = (v >> 48) & 0xFF;
            pubKey[1 + i * 8 + 2] = (v >> 40) & 0xFF;
            pubKey[1 + i * 8 + 3] = (v >> 32) & 0xFF;
            pubKey[1 + i * 8 + 4] = (v >> 24) & 0xFF;
            pubKey[1 + i * 8 + 5] = (v >> 16) & 0xFF;
            pubKey[1 + i * 8 + 6] = (v >> 8) & 0xFF;
            pubKey[1 + i * 8 + 7] = v & 0xFF;
        }
        _SHA256(pubKey, 33, sha);
    } else {
        // Uncompressed: 0x04 + X + Y (65 bytes)
        pubKey[0] = 0x04;
        for (int i = 0; i < 4; i++) {
            uint64_t vx = px[3 - i];
            uint64_t vy = py[3 - i];
            pubKey[1 + i * 8 + 0] = (vx >> 56) & 0xFF;
            pubKey[1 + i * 8 + 1] = (vx >> 48) & 0xFF;
            pubKey[1 + i * 8 + 2] = (vx >> 40) & 0xFF;
            pubKey[1 + i * 8 + 3] = (vx >> 32) & 0xFF;
            pubKey[1 + i * 8 + 4] = (vx >> 24) & 0xFF;
            pubKey[1 + i * 8 + 5] = (vx >> 16) & 0xFF;
            pubKey[1 + i * 8 + 6] = (vx >> 8) & 0xFF;
            pubKey[1 + i * 8 + 7] = vx & 0xFF;
            pubKey[33 + i * 8 + 0] = (vy >> 56) & 0xFF;
            pubKey[33 + i * 8 + 1] = (vy >> 48) & 0xFF;
            pubKey[33 + i * 8 + 2] = (vy >> 40) & 0xFF;
            pubKey[33 + i * 8 + 3] = (vy >> 32) & 0xFF;
            pubKey[33 + i * 8 + 4] = (vy >> 24) & 0xFF;
            pubKey[33 + i * 8 + 5] = (vy >> 16) & 0xFF;
            pubKey[33 + i * 8 + 6] = (vy >> 8) & 0xFF;
            pubKey[33 + i * 8 + 7] = vy & 0xFF;
        }
        _SHA256(pubKey, 65, sha);
    }

    _RIPEMD160(sha, 32, (uint8_t*)hash160);
}

// ============================================================================
// CHECK POINT WITH BLOOM FILTER
// ============================================================================

__device__ __noinline__ void CheckHashBloom(
    uint32_t* hash160,   // 5 x uint32_t
    int32_t incr,
    int32_t endo,
    int32_t mode,        // 0=uncompressed, 1=compressed
    uint32_t maxFound,
    uint32_t* out
) {
    // Check bloom filter
    if (bloom_check_single(
            (uint8_t*)hash160,
            d_bloomFilter,
            d_bloomBits,
            d_bloomSeeds,
            d_bloomHashes)) {
        // Potential match - add to output for CPU verification
        uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            out[pos * ITEM_SIZE32 + 1] = tid;
            out[pos * ITEM_SIZE32 + 2] = (uint32_t)(incr << 16) | (uint32_t)(mode << 15) | (uint32_t)(endo);
            out[pos * ITEM_SIZE32 + 3] = hash160[0];
            out[pos * ITEM_SIZE32 + 4] = hash160[1];
            out[pos * ITEM_SIZE32 + 5] = hash160[2];
            out[pos * ITEM_SIZE32 + 6] = hash160[3];
            out[pos * ITEM_SIZE32 + 7] = hash160[4];
        }
    }
}

// ============================================================================
// MODULAR ARITHMETIC (from VanitySearch GPUMath.h)
// ============================================================================

// Include the modular arithmetic functions
// These are the same as VanitySearch
#include "GPUMath.h"
#include "GPUGroup.h"

// ============================================================================
// MAIN KERNEL - BLOOM FILTER VERSION
// ============================================================================

__global__ void bloom_search_kernel(
    uint64_t* __restrict__ keys,     // Starting public keys (x, y for each thread)
    uint32_t maxFound,
    uint32_t* __restrict__ out,
    bool searchCompressed,
    bool searchUncompressed
) {
    int tid = (blockIdx.x * blockDim.x) + threadIdx.x;

    // Load starting point for this thread
    uint64_t sx[4], sy[4];
    for (int i = 0; i < 4; i++) {
        sx[i] = keys[tid * 8 + i];
        sy[i] = keys[tid * 8 + 4 + i];
    }

    // Delta-x for batch inversion
    uint64_t dx[HSIZE + 2][4];

    // Compute all delta-x values
    for (int i = 0; i < HSIZE; i++) {
        // dx[i] = Gx[i] - sx
        _ModSub(dx[i], _Gx + i * 4, sx);
    }
    _ModSub(dx[HSIZE], _Gx + HSIZE * 4, sx);
    _ModSub(dx[HSIZE + 1], _2Gx, sx);

    // Batch modular inversion
    _ModInvGrouped(dx, HSIZE + 2);

    // Temporary variables
    uint64_t px[4], py[4];
    uint64_t npx[4], npy[4];
    uint64_t dy[4], _s[4], _p[4];
    uint32_t hash160[5];

    // Center point
    if (searchCompressed) {
        ComputeHash160(sx, sy, true, hash160);
        CheckHashBloom(hash160, 0, 0, 1, maxFound, out);
    }
    if (searchUncompressed) {
        ComputeHash160(sx, sy, false, hash160);
        CheckHashBloom(hash160, 0, 0, 0, maxFound, out);
    }

    // Compute points in both directions from center
    for (int i = 0; i < HSIZE; i++) {
        // P = startP + (i+1)*G
        // dy = Gy[i] - sy
        _ModSub(dy, _Gy + i * 4, sy);

        // s = dy * dx[i]^-1
        _ModMult(s, dy, dx[i]);

        // p = s^2
        _ModSquare(_p, _s);

        // px = p - sx - Gx[i]
        _ModSub(px, _p, sx);
        _ModSub(px, px, _Gx + i * 4);

        // py = s * (Gx[i] - px) - Gy[i]
        _ModSub(py, _Gx + i * 4, px);
        _ModMult(py, _s, py);
        _ModSub(py, py, _Gy + i * 4);

        // N = startP - (i+1)*G (negate Gy)
        // dy = -Gy[i] - sy
        _ModNeg(dy, _Gy + i * 4);
        _ModSub(dy, dy, sy);

        _ModMult(_s, dy, dx[i]);
        _ModSquare(_p, _s);

        _ModSub(npx, _p, sx);
        _ModSub(npx, npx, _Gx + i * 4);

        _ModSub(npy, _Gx + i * 4, npx);
        _ModMult(npy, _s, npy);
        _ModAdd(npy, npy, _Gy + i * 4);  // Note: add because we negated Gy

        // Check both points
        if (searchCompressed) {
            ComputeHash160(px, py, true, hash160);
            CheckHashBloom(hash160, i + 1, 0, 1, maxFound, out);

            ComputeHash160(npx, npy, true, hash160);
            CheckHashBloom(hash160, -(i + 1), 0, 1, maxFound, out);
        }
        if (searchUncompressed) {
            ComputeHash160(px, py, false, hash160);
            CheckHashBloom(hash160, i + 1, 0, 0, maxFound, out);

            ComputeHash160(npx, npy, false, hash160);
            CheckHashBloom(hash160, -(i + 1), 0, 0, maxFound, out);
        }

        // GLV Endomorphism check (3x more addresses per point)
        // TODO: Add endomorphism support if needed
    }

    // First point (startP - (GRP_SIZE/2)*G)
    int i = HSIZE;
    _ModNeg(dy, _Gy + i * 4);
    _ModSub(dy, dy, sy);

    _ModMult(_s, dy, dx[i]);
    _ModSquare(_p, _s);

    _ModSub(npx, _p, sx);
    _ModSub(npx, npx, _Gx + i * 4);

    _ModSub(npy, _Gx + i * 4, npx);
    _ModMult(npy, _s, npy);
    _ModAdd(npy, npy, _Gy + i * 4);

    if (searchCompressed) {
        ComputeHash160(npx, npy, true, hash160);
        CheckHashBloom(hash160, -(HSIZE + 1), 0, 1, maxFound, out);
    }
    if (searchUncompressed) {
        ComputeHash160(npx, npy, false, hash160);
        CheckHashBloom(hash160, -(HSIZE + 1), 0, 0, maxFound, out);
    }

    // Update starting point for next iteration
    // newStart = startP + GRP_SIZE*G = startP + 2*(GRP_SIZE/2)*G
    i = HSIZE + 1;
    _ModSub(dy, _2Gy, sy);
    _ModMult(_s, dy, dx[i]);
    _ModSquare(_p, _s);

    _ModSub(px, _p, sx);
    _ModSub(px, px, _2Gx);

    _ModSub(py, _2Gx, px);
    _ModMult(py, _s, py);
    _ModSub(py, py, _2Gy);

    // Store updated starting point
    for (int j = 0; j < 4; j++) {
        keys[tid * 8 + j] = px[j];
        keys[tid * 8 + 4 + j] = py[j];
    }
}

// ============================================================================
// KERNEL LAUNCHER
// ============================================================================

void LaunchBloomSearchKernel(
    uint64_t* d_keys,
    int numThreads,
    int blockSize,
    uint32_t maxFound,
    uint32_t* d_output,
    bool searchCompressed,
    bool searchUncompressed,
    cudaStream_t stream = 0
) {
    int numBlocks = (numThreads + blockSize - 1) / blockSize;

    bloom_search_kernel<<<numBlocks, blockSize, 0, stream>>>(
        d_keys,
        maxFound,
        d_output,
        searchCompressed,
        searchUncompressed
    );
}

#endif // GPU_COMPUTE_BLOOM_H
