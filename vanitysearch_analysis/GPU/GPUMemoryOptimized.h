/*
 * GPU Memory Access Optimization for VanitySearch
 *
 * Key optimizations:
 * 1. Coalesced memory access - threads in a warp access consecutive memory
 * 2. Structure of Arrays (SoA) instead of Array of Structures (AoS)
 * 3. Proper alignment for 128-bit loads
 * 4. Use of texture memory for read-only lookup tables
 * 5. Shared memory tiling for frequently accessed data
 */

#ifndef GPU_MEMORY_OPTIMIZED_H
#define GPU_MEMORY_OPTIMIZED_H

#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>

//------------------------------------------------------------------------------
// Memory layout transformation: AoS -> SoA
//------------------------------------------------------------------------------

/*
 * Original layout (Array of Structures):
 *   keys[i] = { x[0], x[1], x[2], x[3], y[0], y[1], y[2], y[3] }
 *
 * When thread i accesses keys[i], adjacent threads access non-contiguous memory
 * leading to uncoalesced memory access.
 *
 * Optimized layout (Structure of Arrays):
 *   x0[i], x1[i], x2[i], x3[i], y0[i], y1[i], y2[i], y3[i]
 *
 * Now adjacent threads access adjacent memory addresses -> coalesced!
 */

// SoA layout for public keys
typedef struct {
    uint64_t *x0;  // x coordinate, limb 0, for all points
    uint64_t *x1;  // x coordinate, limb 1, for all points
    uint64_t *x2;  // x coordinate, limb 2, for all points
    uint64_t *x3;  // x coordinate, limb 3, for all points
    uint64_t *y0;  // y coordinate, limb 0, for all points
    uint64_t *y1;  // y coordinate, limb 1, for all points
    uint64_t *y2;  // y coordinate, limb 2, for all points
    uint64_t *y3;  // y coordinate, limb 3, for all points
} KeysSoA;

// Convert AoS to SoA on host before upload
void convertAoStoSoA(uint64_t *keysAoS, KeysSoA *keysSoA, int numKeys) {
    for (int i = 0; i < numKeys; i++) {
        int srcIdx = i * 8;
        keysSoA->x0[i] = keysAoS[srcIdx + 0];
        keysSoA->x1[i] = keysAoS[srcIdx + 1];
        keysSoA->x2[i] = keysAoS[srcIdx + 2];
        keysSoA->x3[i] = keysAoS[srcIdx + 3];
        keysSoA->y0[i] = keysAoS[srcIdx + 4];
        keysSoA->y1[i] = keysAoS[srcIdx + 5];
        keysSoA->y2[i] = keysAoS[srcIdx + 6];
        keysSoA->y3[i] = keysAoS[srcIdx + 7];
    }
}

//------------------------------------------------------------------------------
// Texture memory for prefix lookup table
//------------------------------------------------------------------------------

/*
 * The prefix lookup table is read-only and accessed with spatial locality.
 * Texture memory provides:
 * 1. Hardware caching optimized for 2D spatial access patterns
 * 2. Free address clamping and interpolation (not needed here, but no overhead)
 * 3. Separate cache from L1, reducing pressure
 */

// Declare texture reference (CUDA < 12.0 style, compatible with older GPUs)
texture<uint16_t, 1, cudaReadModeElementType> tex_prefix;

// For CUDA 12.0+, use bindless textures:
// cudaTextureObject_t tex_prefix_obj;

// Bind prefix table to texture
cudaError_t bindPrefixTexture(uint16_t *d_prefix, size_t size) {
    cudaChannelFormatDesc channelDesc = cudaCreateChannelDesc<uint16_t>();
    return cudaBindTexture(NULL, tex_prefix, d_prefix, channelDesc, size);
}

// Read from texture in kernel
__device__ __forceinline__ uint16_t readPrefixTexture(int idx) {
    return tex1Dfetch(tex_prefix, idx);
}

//------------------------------------------------------------------------------
// Shared memory tiling for generator table
//------------------------------------------------------------------------------

/*
 * The generator table (GTable) is accessed frequently during point addition.
 * Loading tiles into shared memory reduces global memory bandwidth.
 */

#define TILE_SIZE 32  // Points per tile
#define LIMBS_PER_POINT 8  // 4 for x, 4 for y

__shared__ uint64_t s_gtable_tile[TILE_SIZE * LIMBS_PER_POINT];

// Load a tile of the generator table into shared memory
__device__ void loadGTableTile(
    const uint64_t *g_gtable,  // Global generator table
    int tileIdx                 // Which tile to load
) {
    int tid = threadIdx.x;
    int numLoads = (TILE_SIZE * LIMBS_PER_POINT + blockDim.x - 1) / blockDim.x;

    for (int i = 0; i < numLoads; i++) {
        int loadIdx = tid + i * blockDim.x;
        if (loadIdx < TILE_SIZE * LIMBS_PER_POINT) {
            int globalIdx = tileIdx * TILE_SIZE * LIMBS_PER_POINT + loadIdx;
            s_gtable_tile[loadIdx] = g_gtable[globalIdx];
        }
    }
    __syncthreads();
}

// Read a point from the shared memory tile
__device__ void readPointFromTile(
    int localIdx,       // Index within tile
    uint64_t *px,       // Output x (4 limbs)
    uint64_t *py        // Output y (4 limbs)
) {
    int baseIdx = localIdx * LIMBS_PER_POINT;
    px[0] = s_gtable_tile[baseIdx + 0];
    px[1] = s_gtable_tile[baseIdx + 1];
    px[2] = s_gtable_tile[baseIdx + 2];
    px[3] = s_gtable_tile[baseIdx + 3];
    py[0] = s_gtable_tile[baseIdx + 4];
    py[1] = s_gtable_tile[baseIdx + 5];
    py[2] = s_gtable_tile[baseIdx + 6];
    py[3] = s_gtable_tile[baseIdx + 7];
}

//------------------------------------------------------------------------------
// 128-bit aligned loads using vector types
//------------------------------------------------------------------------------

/*
 * NVIDIA GPUs can load 128 bits (16 bytes) in a single transaction.
 * Using uint4 or int4 types enables this optimization.
 */

// Load 256 bits (4 x uint64_t) as two 128-bit loads
__device__ __forceinline__ void load256Aligned(
    const uint64_t *src,
    uint64_t *dst
) {
    // Cast to uint4 for 128-bit loads
    uint4 *src4 = (uint4 *)src;
    uint4 *dst4 = (uint4 *)dst;

    dst4[0] = src4[0];  // Loads src[0] and src[1]
    dst4[1] = src4[1];  // Loads src[2] and src[3]
}

// Store 256 bits as two 128-bit stores
__device__ __forceinline__ void store256Aligned(
    const uint64_t *src,
    uint64_t *dst
) {
    uint4 *src4 = (uint4 *)src;
    uint4 *dst4 = (uint4 *)dst;

    dst4[0] = src4[0];
    dst4[1] = src4[1];
}

//------------------------------------------------------------------------------
// Warp-level primitives for reduction
//------------------------------------------------------------------------------

/*
 * When searching for prefix matches, we need to determine if any thread
 * in the warp found a match. Warp-level voting is faster than shared memory.
 */

// Check if any thread in warp found a match
__device__ __forceinline__ int warpAnyMatch(int hasMatch) {
    return __any_sync(0xFFFFFFFF, hasMatch);
}

// Get the index of the first matching thread in warp
__device__ __forceinline__ int warpFirstMatch(int hasMatch) {
    unsigned mask = __ballot_sync(0xFFFFFFFF, hasMatch);
    return __ffs(mask) - 1;  // Returns -1 if no match
}

// Broadcast a value from one thread to all threads in warp
__device__ __forceinline__ uint64_t warpBroadcast(uint64_t value, int srcLane) {
    return __shfl_sync(0xFFFFFFFF, value, srcLane);
}

//------------------------------------------------------------------------------
// Optimized kernel with all memory optimizations
//------------------------------------------------------------------------------

__global__ void compute_keys_memory_optimized(
    // SoA layout for coalesced access
    uint64_t *keys_x0, uint64_t *keys_x1, uint64_t *keys_x2, uint64_t *keys_x3,
    uint64_t *keys_y0, uint64_t *keys_y1, uint64_t *keys_y2, uint64_t *keys_y3,
    // Generator table (will be tiled into shared memory)
    const uint64_t *g_gtable,
    // Prefix table (bound to texture)
    // Results
    uint32_t maxFound,
    uint32_t *found
) {
    int tid = threadIdx.x;
    int gid = blockIdx.x * blockDim.x + tid;

    // Load this thread's starting point using coalesced access
    uint64_t px[4], py[4];
    px[0] = keys_x0[gid];
    px[1] = keys_x1[gid];
    px[2] = keys_x2[gid];
    px[3] = keys_x3[gid];
    py[0] = keys_y0[gid];
    py[1] = keys_y1[gid];
    py[2] = keys_y2[gid];
    py[3] = keys_y3[gid];

    // Process keys
    for (int step = 0; step < 1024; step++) {
        // Load generator table tile if needed
        int tileIdx = step / TILE_SIZE;
        if (step % TILE_SIZE == 0) {
            loadGTableTile(g_gtable, tileIdx);
        }

        // Get the generator point for this step from shared memory
        uint64_t gx[4], gy[4];
        readPointFromTile(step % TILE_SIZE, gx, gy);

        // Point addition (using optimized field operations)
        // ... point addition code ...

        // Compute hash
        uint8_t hash[20];
        // ... hash computation ...

        // Check prefix using texture memory
        uint16_t prefix = *((uint16_t *)hash);
        uint16_t tableValue = readPrefixTexture(prefix);

        // Check if any thread in warp found a match
        int hasMatch = (tableValue != 0);
        if (warpAnyMatch(hasMatch)) {
            // At least one thread found something - handle it
            // Use atomic operations to record the find
            if (hasMatch) {
                uint32_t idx = atomicAdd(found, 1);
                if (idx < maxFound) {
                    // Store result...
                }
            }
        }
    }

    // Write back final points using coalesced access
    keys_x0[gid] = px[0];
    keys_x1[gid] = px[1];
    keys_x2[gid] = px[2];
    keys_x3[gid] = px[3];
    keys_y0[gid] = py[0];
    keys_y1[gid] = py[1];
    keys_y2[gid] = py[2];
    keys_y3[gid] = py[3];
}

//------------------------------------------------------------------------------
// Memory allocation helpers
//------------------------------------------------------------------------------

// Allocate SoA structure on device
cudaError_t allocateKeysSoA(KeysSoA *keys, int numKeys) {
    cudaError_t err;

    err = cudaMalloc(&keys->x0, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->x1, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->x2, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->x3, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->y0, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->y1, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->y2, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;
    err = cudaMalloc(&keys->y3, numKeys * sizeof(uint64_t));
    if (err != cudaSuccess) return err;

    return cudaSuccess;
}

// Free SoA structure
void freeKeysSoA(KeysSoA *keys) {
    cudaFree(keys->x0);
    cudaFree(keys->x1);
    cudaFree(keys->x2);
    cudaFree(keys->x3);
    cudaFree(keys->y0);
    cudaFree(keys->y1);
    cudaFree(keys->y2);
    cudaFree(keys->y3);
}

// Copy SoA from host to device
cudaError_t copyKeysSoAToDevice(KeysSoA *d_keys, KeysSoA *h_keys, int numKeys) {
    cudaError_t err;

    err = cudaMemcpy(d_keys->x0, h_keys->x0, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->x1, h_keys->x1, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->x2, h_keys->x2, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->x3, h_keys->x3, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->y0, h_keys->y0, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->y1, h_keys->y1, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->y2, h_keys->y2, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;
    err = cudaMemcpy(d_keys->y3, h_keys->y3, numKeys * sizeof(uint64_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) return err;

    return cudaSuccess;
}

#endif // GPU_MEMORY_OPTIMIZED_H
