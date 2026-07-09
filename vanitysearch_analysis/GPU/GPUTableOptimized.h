/*
 * GPUTableOptimized.h - Optimized generator point table for VanitySearch
 *
 * Optimizations:
 * 1. Interleaved x/y coordinates for better cache locality
 * 2. Aligned memory access for coalesced loads
 * 3. Precomputed odd multiples table
 * 4. Texture memory option for better caching
 *
 * Based on VanitySearch by Jean Luc PONS
 * Optimizations by Terragon Labs
 */

#ifndef GPU_TABLE_OPTIMIZED_H
#define GPU_TABLE_OPTIMIZED_H

#include <cuda_runtime.h>
#include <stdint.h>

// ============================================================================
// CONFIGURATION
// ============================================================================

// Table size options
#define TABLE_SIZE_SMALL 512    // 64KB table
#define TABLE_SIZE_MEDIUM 1024  // 128KB table (current)
#define TABLE_SIZE_LARGE 2048   // 256KB table

// Use texture memory for better L2 cache utilization
// Enabled by default for compute capability >= 3.5
#ifndef USE_TEXTURE_MEMORY
#define USE_TEXTURE_MEMORY 0  // Disable by default (constant memory is often faster)
#endif

// ============================================================================
// INTERLEAVED TABLE FORMAT
// ============================================================================

// Structure for interleaved point storage
// Packs x and y coordinates together for better memory access
struct InterleavedPoint {
    uint64_t x[4];
    uint64_t y[4];
};

// Aligned structure for 128-byte cache line optimization
struct __align__(128) AlignedPoint {
    uint64_t x[4];
    uint64_t y[4];
};

// ============================================================================
// OPTIMIZED TABLE ACCESS FUNCTIONS
// ============================================================================

// Load point with interleaved format (single memory transaction)
__device__ __forceinline__ void loadPointInterleaved(
    uint64_t px[4], uint64_t py[4],
    const InterleavedPoint *table, int idx
) {
    const InterleavedPoint *p = &table[idx];

    // Load x coordinates
    px[0] = p->x[0];
    px[1] = p->x[1];
    px[2] = p->x[2];
    px[3] = p->x[3];

    // Load y coordinates
    py[0] = p->y[0];
    py[1] = p->y[1];
    py[2] = p->y[2];
    py[3] = p->y[3];
}

// Vectorized load using 128-bit loads for better memory bandwidth
__device__ __forceinline__ void loadPointVectorized(
    uint64_t px[4], uint64_t py[4],
    const uint64_t *tableX, const uint64_t *tableY, int idx
) {
    // Use 128-bit vector loads
    uint4 *px_vec = (uint4*)px;
    uint4 *py_vec = (uint4*)py;

    const uint4 *srcX = (const uint4*)&tableX[idx * 4];
    const uint4 *srcY = (const uint4*)&tableY[idx * 4];

    // Two 128-bit loads for x
    px_vec[0] = srcX[0];
    px_vec[1] = srcX[1];

    // Two 128-bit loads for y
    py_vec[0] = srcY[0];
    py_vec[1] = srcY[1];
}

// ============================================================================
// PRECOMPUTED ODD MULTIPLES TABLE (64KB Version)
// ============================================================================

// 2048 odd multiples of G: 1G, 3G, 5G, ..., 4095G
// Each point is 64 bytes (32 bytes x + 32 bytes y)
// Total: 2048 * 64 = 128KB (split into x and y tables = 64KB each)

// Only store odd multiples since even can be derived
// oddTable[i] = (2*i + 1) * G
#define ODD_TABLE_SIZE 2048

// Declare in constant memory for fast broadcast access
// Note: Total constant memory is 64KB, so we use half for x and half for y
__device__ __constant__ uint64_t OddGx[ODD_TABLE_SIZE][4];
__device__ __constant__ uint64_t OddGy[ODD_TABLE_SIZE][4];

// Get odd multiple of G
// Returns (2*idx + 1) * G
__device__ __forceinline__ void getOddMultiple(
    uint64_t px[4], uint64_t py[4], int idx
) {
    px[0] = OddGx[idx][0];
    px[1] = OddGx[idx][1];
    px[2] = OddGx[idx][2];
    px[3] = OddGx[idx][3];

    py[0] = OddGy[idx][0];
    py[1] = OddGy[idx][1];
    py[2] = OddGy[idx][2];
    py[3] = OddGy[idx][3];
}

// ============================================================================
// TEXTURE MEMORY IMPLEMENTATION (Optional)
// ============================================================================

#if USE_TEXTURE_MEMORY

// Texture objects for point table
cudaTextureObject_t texGx;
cudaTextureObject_t texGy;

// Initialize texture memory for generator table
__host__ void initTextureTable(const uint64_t *hostGx, const uint64_t *hostGy, int numPoints) {
    cudaChannelFormatDesc channelDesc = cudaCreateChannelDesc<uint4>();

    // Allocate CUDA arrays
    cudaArray_t cuArrayGx, cuArrayGy;
    cudaMallocArray(&cuArrayGx, &channelDesc, numPoints * 2, 1); // 2 uint4 per point
    cudaMallocArray(&cuArrayGy, &channelDesc, numPoints * 2, 1);

    // Copy data to arrays
    cudaMemcpyToArray(cuArrayGx, 0, 0, hostGx, numPoints * 32, cudaMemcpyHostToDevice);
    cudaMemcpyToArray(cuArrayGy, 0, 0, hostGy, numPoints * 32, cudaMemcpyHostToDevice);

    // Create texture objects
    cudaResourceDesc resDesc;
    memset(&resDesc, 0, sizeof(resDesc));
    resDesc.resType = cudaResourceTypeArray;

    cudaTextureDesc texDesc;
    memset(&texDesc, 0, sizeof(texDesc));
    texDesc.addressMode[0] = cudaAddressModeClamp;
    texDesc.filterMode = cudaFilterModePoint;
    texDesc.readMode = cudaReadModeElementType;

    resDesc.res.array.array = cuArrayGx;
    cudaCreateTextureObject(&texGx, &resDesc, &texDesc, NULL);

    resDesc.res.array.array = cuArrayGy;
    cudaCreateTextureObject(&texGy, &resDesc, &texDesc, NULL);
}

// Load point from texture memory
__device__ __forceinline__ void loadPointTexture(
    uint64_t px[4], uint64_t py[4], int idx
) {
    uint4 x0 = tex1Dfetch<uint4>(texGx, idx * 2);
    uint4 x1 = tex1Dfetch<uint4>(texGx, idx * 2 + 1);
    uint4 y0 = tex1Dfetch<uint4>(texGy, idx * 2);
    uint4 y1 = tex1Dfetch<uint4>(texGy, idx * 2 + 1);

    px[0] = ((uint64_t)x0.y << 32) | x0.x;
    px[1] = ((uint64_t)x0.w << 32) | x0.z;
    px[2] = ((uint64_t)x1.y << 32) | x1.x;
    px[3] = ((uint64_t)x1.w << 32) | x1.z;

    py[0] = ((uint64_t)y0.y << 32) | y0.x;
    py[1] = ((uint64_t)y0.w << 32) | y0.z;
    py[2] = ((uint64_t)y1.y << 32) | y1.x;
    py[3] = ((uint64_t)y1.w << 32) | y1.z;
}

#endif // USE_TEXTURE_MEMORY

// ============================================================================
// SHARED MEMORY TILE LOADING
// ============================================================================

// Load a tile of generator points into shared memory
// This reduces repeated global memory accesses
__device__ void loadGeneratorTile(
    uint64_t sharedGx[][4], uint64_t sharedGy[][4],
    int tileStart, int tileSize
) {
    int tid = threadIdx.x;

    // Cooperative loading - each thread loads one point
    if (tid < tileSize) {
        int globalIdx = tileStart + tid;
        if (globalIdx < GRP_SIZE / 2) {
            sharedGx[tid][0] = Gx[globalIdx][0];
            sharedGx[tid][1] = Gx[globalIdx][1];
            sharedGx[tid][2] = Gx[globalIdx][2];
            sharedGx[tid][3] = Gx[globalIdx][3];

            sharedGy[tid][0] = Gy[globalIdx][0];
            sharedGy[tid][1] = Gy[globalIdx][1];
            sharedGy[tid][2] = Gy[globalIdx][2];
            sharedGy[tid][3] = Gy[globalIdx][3];
        }
    }
    __syncthreads();
}

// ============================================================================
// L2 CACHE PREFETCH HINTS
// ============================================================================

// Prefetch point to L2 cache (Compute Capability 3.5+)
__device__ __forceinline__ void prefetchPoint(const uint64_t *px, const uint64_t *py) {
    #if __CUDA_ARCH__ >= 350
    asm volatile("prefetch.global.L2 [%0];" :: "l"(px));
    asm volatile("prefetch.global.L2 [%0];" :: "l"(py));
    #endif
}

// Prefetch generator table entry
__device__ __forceinline__ void prefetchGenerator(int idx) {
    #if __CUDA_ARCH__ >= 350
    if (idx < GRP_SIZE / 2) {
        asm volatile("prefetch.global.L2 [%0];" :: "l"(&Gx[idx]));
        asm volatile("prefetch.global.L2 [%0];" :: "l"(&Gy[idx]));
    }
    #endif
}

// ============================================================================
// TABLE STATISTICS
// ============================================================================

// Get memory usage statistics
__host__ void printTableStats() {
    printf("Generator Table Statistics:\n");
    printf("  GRP_SIZE: %d\n", GRP_SIZE);
    printf("  Table entries: %d\n", GRP_SIZE / 2);
    printf("  Bytes per entry: 64 (32 x + 32 y)\n");
    printf("  Total table size: %d KB\n", (GRP_SIZE / 2) * 64 / 1024);
    #if USE_TEXTURE_MEMORY
    printf("  Using texture memory: Yes\n");
    #else
    printf("  Using constant memory: Yes\n");
    #endif
}

#endif // GPU_TABLE_OPTIMIZED_H
