# VanitySearch GPU Optimization Implementation Plan

## Codebase Analysis Summary

### Current Architecture

**Key Files:**
- `GPU/GPUMath.h` - 256-bit modular arithmetic (assembly-optimized)
- `GPU/GPUCompute.h` - Main kernel computation (point addition, hash checking)
- `GPU/GPUEngine.cu` - CUDA kernel launch, memory management
- `IntGroup.cpp` - CPU batch inversion (Montgomery's trick)
- `SECP256K1.cpp` - Elliptic curve operations
- `GLV.h` - Existing GLV implementation (CPU-side, not integrated into GPU)

**Current Optimizations Already Present:**
1. `UMultSpecial` macro for secp256k1 constant multiplication
2. `ModSub256isOdd` for parity-only computation
3. Batch inversion with `GRP_SIZE/2+1` elements (currently 513)
4. Endomorphism points (_beta, _beta2) used for 6x address checking per key
5. Symmetric point exploitation (P and -P share same x-coordinate)

**Current Performance:**
- ~22.6 billion keys/second on 4x RTX 4080 SUPER
- Each key generates 6 hashes (point, endo1, endo2 × symmetric)
- Group size: 1024 points, batch inversion: 513 elements

---

## Optimization 1: GLV Endomorphism for Initial Key Generation (20-30% gain)

### Current State
- GLV.h exists but is **CPU-only** and **not used in the GPU kernel**
- GPU kernel uses fixed increments (+G) to traverse keyspace
- Each thread starts from a precomputed point and adds G repeatedly

### Proposed Changes

**Goal:** Use GLV to accelerate the initial key generation on CPU, reducing GPU setup time.

**Implementation:**

1. **Modify `Vanity.cpp` - `ComputeKeys()` function:**
```cpp
// Current: Uses standard scalar multiplication
Point Vanity::ComputePublicKey(Int *privKey) {
    return secp->ComputePublicKey(privKey);
}

// New: Use GLV decomposition for faster computation
Point Vanity::ComputePublicKeyGLV(Int *privKey) {
    GLV::Init(secp);
    return GLV::ScalarMult(secp, privKey, &secp->G);
}
```

2. **Optimize batch key generation in `Vanity.cpp`:**
```cpp
void Vanity::InitGPUKeys(Point *keys, int nbThread, Int *baseKey) {
    // Use GLV for initial key computation
    #pragma omp parallel for
    for (int i = 0; i < nbThread; i++) {
        Int k;
        k.Set(baseKey);
        k.Add(i * GRP_SIZE);
        keys[i] = GLV::ScalarMult(secp, &k, &secp->G);
    }
}
```

3. **Files to modify:**
   - `Vanity.cpp` (lines 200-250, key initialization)
   - `Vanity.h` (add GLV include)
   - `GLV.h` (ensure static members are properly defined)

**Expected Gain:** 20-30% faster startup, minimal runtime impact (startup is small % of total time)

**Trade-offs:**
- Adds ~500 lines of GLV code complexity
- Only helps with initial key generation (one-time)
- Requires careful handling of negative decomposition results

---

## Optimization 2: Increased Batch Inversion (10-15% gain)

### Current State
- GPU batch inversion in `_ModInvGrouped()` processes `GRP_SIZE/2+1 = 513` elements
- Uses Montgomery's trick: 1 inversion + 4N multiplications for N elements
- Inversion cost: ~200 field multiplications (using extended Euclidean)

### Proposed Changes

**Goal:** Increase batch size to amortize inversion cost over more elements.

**Implementation:**

1. **Modify `GPU/GPUCompute.h` - Increase group processing:**
```cpp
// Current: GRP_SIZE = 1024, processes 513 inversions per batch
#define GRP_SIZE 1024
#define HSIZE (GRP_SIZE / 2 - 1)  // 511

// Option A: Double group size
#define GRP_SIZE 2048
#define HSIZE (GRP_SIZE / 2 - 1)  // 1023

// Option B: Process multiple groups in single inversion
__device__ void _ModInvGroupedLarge(uint64_t r[GRP_SIZE + 1][4]) {
    // Process 1025 elements instead of 513
}
```

2. **Memory considerations:**
```cpp
// Current register usage per thread:
// dx[GRP_SIZE/2+1][4] = 513 * 4 * 8 = 16,416 bytes (too much for registers)
// Actually stored in local memory (slower)

// Proposed: Use shared memory for batch inversion
__shared__ uint64_t shared_dx[BLOCK_SIZE][4];
```

3. **Files to modify:**
   - `GPU/GPUMath.h` - `_ModInvGrouped()` function
   - `GPU/GPUCompute.h` - `ComputeKeys()` dx array sizing
   - `GPU/GPUEngine.h` - `GRP_SIZE` constant

**Expected Gain:** 10-15%

**Trade-offs:**
- Increased register pressure → lower occupancy
- More shared memory usage
- Diminishing returns past ~2048 elements

---

## Optimization 3: Warp-Level Primitives (5-10% gain)

### Current State
- No use of warp shuffle instructions
- `__syncthreads()` used for thread synchronization
- Each thread works independently on its key group

### Proposed Changes

**Goal:** Use warp-level intrinsics for faster intra-warp communication.

**Implementation:**

1. **Add warp shuffle for modular inverse sharing:**
```cpp
// In GPU/GPUMath.h - Add warp-level reduction
__device__ __forceinline__ uint64_t warpReduceAdd(uint64_t val) {
    for (int offset = 16; offset > 0; offset /= 2) {
        val += __shfl_down_sync(0xffffffff, val, offset);
    }
    return val;
}

// Broadcast inverse result to warp
__device__ __forceinline__ uint64_t warpBroadcast(uint64_t val, int srcLane) {
    return __shfl_sync(0xffffffff, val, srcLane);
}
```

2. **Optimize batch inversion with warp cooperation:**
```cpp
__device__ void _ModInvGroupedWarp(uint64_t r[][4]) {
    // Each warp (32 threads) cooperates on batch inversion
    int lane = threadIdx.x & 31;
    int warpId = threadIdx.x >> 5;

    // Parallel prefix product within warp
    uint64_t product[4];
    Load256(product, r[lane]);

    for (int delta = 1; delta < 32; delta *= 2) {
        uint64_t other[4];
        other[0] = __shfl_up_sync(0xffffffff, product[0], delta);
        other[1] = __shfl_up_sync(0xffffffff, product[1], delta);
        other[2] = __shfl_up_sync(0xffffffff, product[2], delta);
        other[3] = __shfl_up_sync(0xffffffff, product[3], delta);
        if (lane >= delta) {
            _ModMult(product, product, other);
        }
    }

    // Lane 31 has the final product, compute inverse
    if (lane == 31) {
        _ModInv(product);
    }

    // Broadcast inverse back
    // ... (parallel suffix product for individual inverses)
}
```

3. **Files to modify:**
   - `GPU/GPUMath.h` - Add warp primitives
   - `GPU/GPUCompute.h` - Use warp-level batch inversion

**Expected Gain:** 5-10%

**Trade-offs:**
- Only works within 32-thread warps
- Increased code complexity
- Requires compute capability 7.0+ (RTX 4080 has 8.9, OK)
- More synchronization points

---

## Optimization 4: Precomputed Odd Multiples Table (5-10% gain)

### Current State
- Generator table `Gx[], Gy[]` stored in constant memory
- Table generated by `GPU/GPUGenerate.cpp`
- Size: `GRP_SIZE/2 * 2 * 32 bytes = 32KB`

### Proposed Changes

**Goal:** Optimize table layout and access patterns.

**Implementation:**

1. **Precompute odd multiples (1G, 3G, 5G, ... up to 4095G):**
```cpp
// In GPU/GPUGroup.h
// Current: Gx[i] = (2i+1)*G for i in [0, GRP_SIZE/2-1]
// This is already odd multiples!

// Optimization: Pack x and y coordinates together for coalesced access
__device__ __constant__ uint64_t GTable[GRP_SIZE][8]; // x[4], y[4] interleaved
```

2. **Use texture memory for better caching:**
```cpp
// Texture memory has 2D spatial locality caching
cudaTextureObject_t GTableTex;
// ... setup code ...

// Access with texture fetch
__device__ void GetGPoint(int idx, uint64_t *x, uint64_t *y) {
    // tex1Dfetch provides cached access
    x[0] = tex1Dfetch<uint64_t>(GTableTex, idx*8 + 0);
    // ...
}
```

3. **Files to modify:**
   - `GPU/GPUGenerate.cpp` - Generate optimized table layout
   - `GPU/GPUGroup.h` - New table format
   - `GPU/GPUCompute.h` - Use new access pattern

**Expected Gain:** 5-10% (if memory-bound)

**Trade-offs:**
- Texture memory setup overhead
- Code complexity
- May not help if compute-bound (likely already the case)

---

## Implementation Priority and Timeline

| Priority | Optimization | Gain | Complexity | Recommendation |
|----------|--------------|------|------------|----------------|
| 1 | Batch Inversion Increase | 10-15% | Medium | **Implement first** |
| 2 | Warp-Level Primitives | 5-10% | Medium | **Implement second** |
| 3 | Precomputed Table | 5-10% | Low | Benchmark first |
| 4 | GLV Endomorphism | 20-30% startup | High | Lower priority (runtime unaffected) |

---

## Recommended Implementation Order

### Phase 1: Batch Inversion (Highest Impact)
1. Increase `GRP_SIZE` from 1024 to 2048
2. Adjust `_ModInvGrouped()` for larger batches
3. Benchmark and verify correctness

### Phase 2: Warp Primitives
1. Implement `warpReduceAdd` and shuffle operations
2. Modify batch inversion to use warp cooperation
3. Benchmark and tune

### Phase 3: Table Optimization
1. Test texture memory vs constant memory
2. Implement coalesced access pattern
3. Benchmark

### Phase 4: GLV (If startup time matters)
1. Integrate GLV into CPU key generation
2. Test with large thread counts

---

## Testing and Validation

1. **Correctness:** Run `./VanitySearch -check` after each change
2. **Performance:** Compare keys/second before and after
3. **Memory:** Monitor with `nvidia-smi` and `nvprof`
4. **Stability:** Run for extended periods to ensure no drift

---

## Estimated Total Improvement

| Optimization | Individual Gain | Cumulative |
|--------------|-----------------|------------|
| Baseline | - | 22.6B keys/sec |
| Batch Inversion | +12% | 25.3B keys/sec |
| Warp Primitives | +7% | 27.1B keys/sec |
| Table Optimization | +5% | 28.5B keys/sec |

**Expected final performance: ~28-30B keys/second** (25-33% improvement)
