#!/bin/bash
# Setup VanitySearch-bitcrack with bloom filter support

set -e

WORK_DIR="/root/VanitySearch-1.15.4_bitcrack/src_VanitySearch-1.15.4_bitcrack_th512gr/full"
cd "$WORK_DIR"

echo "=== Creating GPUBloom.h ==="
cat > GPU/GPUBloom.h << 'EOF'
/*
 * GPUBloom.h - GPU-optimized Bloom Filter for hash160 matching
 * Integrated into VanitySearch-bitcrack for checking ALL generated keys
 */

#ifndef GPU_BLOOM_H
#define GPU_BLOOM_H

// Bloom filter constants - must match the Python bloom builder
#define BLOOM_NUM_HASHES 20

// Global bloom filter pointers (set by host before kernel launch)
__device__ __constant__ uint64_t d_bloomBits;
__device__ __constant__ uint32_t d_bloomHashes;
__device__ __constant__ uint32_t d_bloomSeeds[BLOOM_NUM_HASHES];

// Device pointer to bloom filter data (set via cudaMemcpyToSymbol)
__device__ uint8_t* d_bloomFilter;

// ============================================================================
// MURMUR3 HASH (GPU VERSION)
// ============================================================================

__device__ __forceinline__ uint32_t rotl32_bloom(uint32_t x, int8_t r) {
    return (x << r) | (x >> (32 - r));
}

__device__ __forceinline__ uint32_t murmur3_32_gpu(const uint8_t* key, int len, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;

    uint32_t h1 = seed;
    const int nblocks = len / 4;

    // Body - process 4 bytes at a time
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
// BLOOM FILTER CHECK - SINGLE HASH160
// Returns true if hash160 MIGHT be in the set (needs CPU verification)
// Returns false if definitely NOT in the set
// ============================================================================

__device__ __forceinline__ bool bloom_check_hash160(
    const uint8_t* hash160,      // 20-byte hash160
    const uint8_t* filter,       // Bloom filter data
    uint64_t numBits,            // Number of bits in filter
    const uint32_t* seeds,       // Hash seeds
    int numHashes                // Number of hash functions
) {
    #pragma unroll 4
    for (int i = 0; i < numHashes; i++) {
        uint32_t h = murmur3_32_gpu(hash160, 20, seeds[i]);
        uint64_t bitPos = h % numBits;
        uint64_t bytePos = bitPos >> 3;  // / 8
        uint8_t bitMask = 1 << (bitPos & 7);  // % 8

        if (!(filter[bytePos] & bitMask)) {
            return false;  // Definitely not in set
        }
    }
    return true;  // Probably in set
}

// ============================================================================
// BLOOM CHECK POINT - replaces prefix lookup
// ============================================================================

__device__ __noinline__ void CheckPointBloom(
    uint32_t* _h,                // hash160 as 5x uint32_t (20 bytes)
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
    uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;

    // Check bloom filter - if definitely not in set, return immediately
    if (!bloom_check_hash160((uint8_t*)_h, bloomFilter, bloomBits, bloomSeeds, bloomHashes)) {
        return;  // Not a match
    }

    // Potential match found! Report to CPU for verification
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

#endif // GPU_BLOOM_H
EOF

echo "=== Creating GPUComputeBloom.h (modified GPUCompute.h with bloom filter) ==="
cat > GPU/GPUComputeBloom.h << 'EOF'
/*
 * GPUComputeBloom.h - Modified GPUCompute.h with bloom filter checking
 * All generated keys are checked against the bloom filter
 */

#include "GPUBloom.h"

// -----------------------------------------------------------------------------------------
// BLOOM FILTER CHECK MACROS
// -----------------------------------------------------------------------------------------

#define CHECK_BLOOM(_h, incr, endo, mode) \
    CheckPointBloom(_h, incr, endo, mode, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out, P2PKH)

// -----------------------------------------------------------------------------------------
// CHECK HASH WITH BLOOM FILTER - COMPRESSED
// -----------------------------------------------------------------------------------------

__device__ __noinline__ void CheckHashCompBloom(
    uint64_t* px, 
    uint8_t isOdd, 
    int32_t incr,
    const uint8_t* bloomFilter,
    uint64_t bloomBits,
    const uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound, 
    uint32_t* out
) {
    uint32_t h[5];
    _GetHash160Comp(px, isOdd, (uint8_t*)h);
    CHECK_BLOOM(h, incr, 0, true);
}

// -----------------------------------------------------------------------------------------
// CHECK HASH WITH BLOOM FILTER - UNCOMPRESSED
// -----------------------------------------------------------------------------------------

__device__ __noinline__ void CheckHashUncompBloom(
    uint64_t* px, 
    uint64_t* py, 
    int32_t incr,
    const uint8_t* bloomFilter,
    uint64_t bloomBits,
    const uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound, 
    uint32_t* out
) {
    uint32_t h[5];
    _GetHash160(px, py, (uint8_t*)h);
    CHECK_BLOOM(h, incr, 0, false);
}

// -----------------------------------------------------------------------------------------
// CHECK HASH - DISPATCH BY MODE
// -----------------------------------------------------------------------------------------

__device__ __noinline__ void CheckHashBloom(
    uint32_t mode, 
    uint64_t* px, 
    uint64_t* py, 
    int32_t incr,
    const uint8_t* bloomFilter,
    uint64_t bloomBits,
    const uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound, 
    uint32_t* out
) {
    switch (mode) {
    case SEARCH_COMPRESSED:
        CheckHashCompBloom(px, (uint8_t)(py[0] & 1), incr, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);
        break;
    case SEARCH_UNCOMPRESSED:
        CheckHashUncompBloom(px, py, incr, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);
        break;
    case SEARCH_BOTH:
        CheckHashCompBloom(px, (uint8_t)(py[0] & 1), incr, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);
        CheckHashUncompBloom(px, py, incr, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);
        break;
    }
}

// -----------------------------------------------------------------------------------------
// MACRO FOR COMPUTING KEYS WITH BLOOM
// -----------------------------------------------------------------------------------------

#define CHECK_BLOOM_PREFIX(incr) \
    CheckHashBloom(mode, px, py, j*GRP_SIZE + (incr), bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out)

// -----------------------------------------------------------------------------------------
// COMPUTE KEYS WITH BLOOM FILTER
// -----------------------------------------------------------------------------------------

__device__ void ComputeKeysBloom(
    uint32_t mode, 
    uint64_t* startx, 
    uint64_t* starty,
    const uint8_t* bloomFilter,
    uint64_t bloomBits,
    const uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound, 
    uint32_t* out
) {
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
        ModSub256(dx[i], Gx[i], sx);
        ModSub256(dx[i+1], _2Gnx, sx);

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

            ModSub256(py, Gx[i], px);
            _ModMult(py, _s);
            ModAdd256(py, Gy[i]);

            CHECK_BLOOM_PREFIX(GRP_SIZE / 2 - (i + 1));
        }

        // First point
        Load256(px, sx);
        Load256(py, sy);
        ModNeg256(dy, Gy[i]);
        ModSub256(dy, py);

        _ModMult(_s, dy, dx[i]);
        _ModSqr(_p2, _s);

        ModSub256(px, _p2, px);
        ModSub256(px, Gx[i]);

        ModSub256(py, Gx[i], px);
        _ModMult(py, _s);
        ModAdd256(py, Gy[i]);

        CHECK_BLOOM_PREFIX(0);

        i++;

        // Next start point
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
    }

    // Update starting point
    __syncthreads();
    Store256A(startx, px);
    Store256A(starty, py);
}

EOF

echo "=== Backup original GPUEngine files ==="
cp GPU/GPUEngine.cu GPU/GPUEngine.cu.orig
cp GPU/GPUEngine.h GPU/GPUEngine.h.orig

echo "=== Creating modified GPUEngine.h with bloom support ==="
cat > GPU/GPUEngine.h << 'ENGHEADER'
/*
 * GPUEngine.h - Modified for bloom filter support
 */

#ifndef GPUENGINEH
#define GPUENGINEH

#include <string>
#include <vector>
#include "../SECP256k1.h"

// Item size for found entries (8 uint32_t)
#define ITEM_SIZE 32
#define ITEM_SIZE32 8

// Maximum number of found items
#define MAX_FOUND_DEFAULT 262144

// Address types
#define P2PKH  0
#define P2SH   1
#define BECH32 2

// Search modes
#define SEARCH_COMPRESSED   0
#define SEARCH_UNCOMPRESSED 1
#define SEARCH_BOTH         2

typedef uint16_t prefix_t;
typedef uint32_t prefixl_t;

class GPUEngine {
public:
    GPUEngine(int nbThreadGroup, int gpuId, uint32_t maxFound, bool rekey);
    ~GPUEngine();
    
    bool SetKeys(Point *p);
    void SetSearchMode(int searchMode);
    void SetSearchType(int searchType);
    
    // Standard prefix-based launch
    bool Launch(std::vector<ITEM> &prefixFound, bool spinWait = false);
    bool LaunchSEARCH_MODE_MA(std::vector<ITEM> &found, bool spinWait = false);
    
    // NEW: Bloom filter launch
    bool LaunchBloom(std::vector<ITEM> &bloomFound, bool spinWait = false);
    
    // Bloom filter setup
    bool SetBloomFilter(uint8_t* filterData, uint64_t numBits, uint32_t numHashes, uint32_t* seeds);
    
    int GetNbThread();
    int GetGroupSize();
    std::string deviceName;
    
    bool Check(Secp256K1 *secp);
    
    // Prefix table
    void SetPrefix(std::vector<prefix_t> prefixes);
    void SetPrefix(std::vector<prefix_t> prefixes, std::vector<prefixl_t> prefixesLookup);
    void SetPattern(const char *pattern);
    
    // Status
    static void PrintCudaInfo();
    static void GenerateCode(Secp256K1 *secp, int size);
    
    bool callKernelAndWait();
    bool callKernel();
    uint64_t IsStepComplete();
    bool IsInitialized() { return initialised; }

private:
    bool initialised;
    bool rekey;
    int searchMode;
    int searchType;
    uint32_t maxFound;
    uint32_t outputSize;
    int nbThread;
    int nbThreadPerGroup;
    int nbGroup;
    
    // Prefix data
    prefix_t *inputPrefix;
    prefix_t *inputPrefixPinned;
    prefixl_t *inputPrefixLookup;
    uint32_t *inputPrefixLookupPinned;
    
    // Keys
    uint64_t *inputKey;
    uint64_t *inputKeyPinned;
    
    // Output
    uint32_t *outputPrefix;
    uint32_t *outputPrefixPinned;
    
    // Pattern
    char *inputPattern;
    char *inputPatternPinned;
    
    // Bloom filter
    uint8_t *d_bloomFilter;
    uint64_t bloomBits;
    uint32_t bloomHashes;
    uint32_t *d_bloomSeeds;
    bool bloomInitialized;
};

// Item structure for found results
struct ITEM {
    uint32_t thId;
    int16_t incr;
    uint8_t mode;
    uint8_t endo;
    uint8_t hash[20];
};

#endif // GPUENGINEH
ENGHEADER

echo "=== Creating modified GPUEngine.cu with bloom kernel ==="
# We'll keep the original and add bloom-specific code
cat > GPU/GPUEngineBloom.cu << 'ENGBLOOM'
/*
 * GPUEngineBloom.cu - Bloom filter kernel for VanitySearch
 * This file adds bloom filter checking to all generated keys
 */

#ifndef WIN64
#include <unistd.h>
#include <stdio.h>
#endif

#include "GPUEngine.h"
#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>

// Include the standard VanitySearch GPU headers
#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

// Include bloom filter support
#include "GPUBloom.h"
#include "GPUComputeBloom.h"

// -----------------------------------------------------------------------------------------
// BLOOM FILTER KERNEL
// -----------------------------------------------------------------------------------------

__global__ void comp_keys_bloom(
    uint32_t mode,
    uint64_t* keys,
    uint8_t* bloomFilter,
    uint64_t bloomBits,
    uint32_t* bloomSeeds,
    int bloomHashes,
    uint32_t maxFound,
    uint32_t* found
) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_TRHEAD_PER_GROUP;
    
    ComputeKeysBloom(
        mode,
        keys + xPtr,
        keys + yPtr,
        bloomFilter,
        bloomBits,
        bloomSeeds,
        bloomHashes,
        maxFound,
        found
    );
}

// -----------------------------------------------------------------------------------------
// HOST FUNCTIONS FOR BLOOM FILTER
// -----------------------------------------------------------------------------------------

bool GPUEngine::SetBloomFilter(uint8_t* filterData, uint64_t numBits, uint32_t numHashes, uint32_t* seeds) {
    cudaError_t err;
    
    // Store bloom parameters
    bloomBits = numBits;
    bloomHashes = numHashes;
    
    // Allocate and copy bloom filter to device
    uint64_t filterBytes = (numBits + 7) / 8;
    err = cudaMalloc(&d_bloomFilter, filterBytes);
    if (err != cudaSuccess) {
        printf("GPUEngine: Failed to allocate bloom filter: %s\n", cudaGetErrorString(err));
        return false;
    }
    
    err = cudaMemcpy(d_bloomFilter, filterData, filterBytes, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) {
        printf("GPUEngine: Failed to copy bloom filter: %s\n", cudaGetErrorString(err));
        return false;
    }
    
    // Allocate and copy seeds
    err = cudaMalloc(&d_bloomSeeds, numHashes * sizeof(uint32_t));
    if (err != cudaSuccess) {
        printf("GPUEngine: Failed to allocate bloom seeds: %s\n", cudaGetErrorString(err));
        return false;
    }
    
    err = cudaMemcpy(d_bloomSeeds, seeds, numHashes * sizeof(uint32_t), cudaMemcpyHostToDevice);
    if (err != cudaSuccess) {
        printf("GPUEngine: Failed to copy bloom seeds: %s\n", cudaGetErrorString(err));
        return false;
    }
    
    bloomInitialized = true;
    printf("GPUEngine: Bloom filter loaded (%.2f MB, %u hashes)\n", 
           filterBytes / (1024.0 * 1024.0), numHashes);
    
    return true;
}

bool GPUEngine::LaunchBloom(std::vector<ITEM>& bloomFound, bool spinWait) {
    if (!bloomInitialized) {
        printf("GPUEngine: Bloom filter not initialized!\n");
        return false;
    }
    
    // Reset found count
    cudaMemset(outputPrefix, 0, 4);
    
    // Launch bloom kernel
    comp_keys_bloom<<<nbThread / nbThreadPerGroup, nbThreadPerGroup>>>(
        searchMode,
        inputKey,
        d_bloomFilter,
        bloomBits,
        d_bloomSeeds,
        bloomHashes,
        maxFound,
        outputPrefix
    );
    
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("GPUEngine: Bloom kernel launch error: %s\n", cudaGetErrorString(err));
        return false;
    }
    
    if (spinWait) {
        cudaDeviceSynchronize();
    }
    
    // Copy results back
    uint32_t foundCount;
    cudaMemcpy(&foundCount, outputPrefix, 4, cudaMemcpyDeviceToHost);
    
    if (foundCount > 0) {
        if (foundCount > maxFound) foundCount = maxFound;
        
        // Copy found items
        cudaMemcpy(outputPrefixPinned, outputPrefix, 4 + foundCount * ITEM_SIZE, cudaMemcpyDeviceToHost);
        
        // Parse results
        bloomFound.clear();
        for (uint32_t i = 0; i < foundCount; i++) {
            ITEM item;
            uint32_t* data = outputPrefixPinned + 1 + i * ITEM_SIZE32;
            
            item.thId = data[0];
            uint32_t flags = data[1];
            item.incr = (int16_t)(flags >> 16);
            item.mode = (flags >> 15) & 1;
            item.endo = flags & 0x7FFF;
            
            memcpy(item.hash, data + 2, 20);
            bloomFound.push_back(item);
        }
    }
    
    return true;
}
ENGBLOOM

echo "=== Creating updated Makefile ==="
cat > Makefile.bloom << 'MAKEFILE'
# Makefile for VanitySearch with Bloom Filter
# For RTX 4090 (compute capability 8.9)

SRC = Base58.cpp IntGroup.cpp main.cpp Random.cpp \
      Timer.cpp Int.cpp IntMod.cpp Point.cpp SECP256K1.cpp \
      Vanity.cpp GPU/GPUGenerate.cpp hash/ripemd160.cpp \
      hash/sha256.cpp hash/sha512.cpp hash/ripemd160_sse.cpp \
      hash/sha256_sse.cpp Bech32.cpp Wildcard.cpp

OBJDIR = obj

OBJET = $(addprefix $(OBJDIR)/, \
        Base58.o IntGroup.o main.o Random.o Timer.o Int.o \
        IntMod.o Point.o SECP256K1.o Vanity.o GPU/GPUGenerate.o \
        hash/ripemd160.o hash/sha256.o hash/sha512.o \
        hash/ripemd160_sse.o hash/sha256_sse.o \
        GPU/GPUEngine.o Bech32.o Wildcard.o)

CXX        = g++
CUDA       = /usr/local/cuda
NVCC       = $(CUDA)/bin/nvcc

# For RTX 4090: compute capability 8.9
CCAP       = 89

CXXFLAGS   = -DWITHGPU -m64 -mssse3 -Wno-write-strings -O3 -I. -I$(CUDA)/include
LFLAGS     = -lpthread -L$(CUDA)/lib64 -lcudart

# NVCC flags for maximum performance
NVCCFLAGS  = -O3 --ptxas-options=-v -m64 -I$(CUDA)/include \
             -gencode=arch=compute_$(CCAP),code=sm_$(CCAP) \
             --compiler-options -fPIC

$(OBJDIR)/GPU/GPUEngine.o: GPU/GPUEngine.cu GPU/GPUBloom.h GPU/GPUComputeBloom.h
	$(NVCC) $(NVCCFLAGS) -o $@ -c $<

$(OBJDIR)/%.o : %.cpp
	$(CXX) $(CXXFLAGS) -o $@ -c $<

all: VanitySearch

VanitySearch: $(OBJET)
	@echo Making VanitySearch with Bloom Filter...
	$(CXX) $(OBJET) $(LFLAGS) -o VanitySearch

$(OBJET): | $(OBJDIR) $(OBJDIR)/GPU $(OBJDIR)/hash

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/GPU: $(OBJDIR)
	cd $(OBJDIR) && mkdir -p GPU

$(OBJDIR)/hash: $(OBJDIR)
	cd $(OBJDIR) && mkdir -p hash

clean:
	@echo Cleaning...
	@rm -f obj/*.o
	@rm -f obj/GPU/*.o
	@rm -f obj/hash/*.o
	@rm -f VanitySearch

.PHONY: all clean
MAKEFILE

echo "=== Setup complete ==="
ls -la GPU/
echo ""
echo "To build: make -f Makefile.bloom"
