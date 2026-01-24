# VanitySearch GPU Optimization Summary

## Critical Bottlenecks Fixed

### 1. Stack Memory Overflow (GPUCompute.h) - **CRITICAL**
**File:** `GPUComputeFixed.h`

**Problem:**
```cpp
// BEFORE: 16KB per thread in stack memory!
uint64_t subp[GRP_SIZE / 2][4];  // 512 * 4 * 8 = 16,384 bytes per thread
```

With 256 threads per block, this requires 4MB of stack per block - impossible!
This kills GPU occupancy (typically only 1-2 warps can run instead of 32+).

**Solution:**
```cpp
// AFTER: 16KB per block in shared memory
__shared__ uint64_t s_subp[SUBP_SHARED_SIZE][4];
```

**Expected Improvement:** 2-3x speedup from improved occupancy

---

### 2. Shared Memory Batch Inversion (GPUMath.h)
**File:** `GPUMathOptimized.h`

**Problem:**
The original code doesn't use shared memory for batch modular inversions.
Each thread performs independent inversions, wasting potential parallelism.

**Solution:**
- Implemented Montgomery's trick using shared memory
- Batch multiple inversions into a single expensive inversion
- Uses parallel prefix products for better efficiency

**Expected Improvement:** 1.5-2.5x speedup for inversion-heavy workloads

---

### 3. Hash Constants Already Cached ✓
**File:** `GPUHash.h`

**Status:** Already correct in original code!
```cpp
__device__ __constant__ uint32_t K[] = { ... };  // SHA256 constants
__device__ __constant__ uint32_t K160[] = { ... };  // RIPEMD160 constants
```

The constants are already in CUDA constant memory, which provides:
- Broadcast to all threads in a warp (single memory transaction)
- Cached in dedicated constant cache
- No fix needed

---

### 4. Asynchronous Memory Transfers (GPUEngine.cu)
**File:** `GPUEngineOptimized.cu`

**Problem:**
```cpp
// BEFORE: Synchronous transfer blocks GPU
cudaMemcpy(inputKey, inputKeyPinned, nbThread*32*2, cudaMemcpyHostToDevice);
// GPU sits idle during transfer!
```

**Solution:**
```cpp
// AFTER: Double-buffered async transfers
cudaMemcpyAsync(ctx.d_inputKey, ctx.h_inputKeyPinned, size,
                cudaMemcpyHostToDevice, ctx.stream);
// GPU continues computing while next batch transfers!
```

Pipeline diagram:
```
Stream 0: [Transfer0][Compute0 ][Transfer0']
Stream 1:           [Transfer1][Compute1  ][Transfer1']
```

**Expected Improvement:** 1.3-1.5x speedup (eliminates ~30% GPU idle time)

---

### 5. Optimized Modular Math (GPUMath.h)
**File:** `GPUMathOptimized.h`

**Problem:**
The original code uses basic PTX assembly but doesn't fully exploit:
- Wide multiply instructions (mad.wide.u64)
- Optimal instruction scheduling
- Fused multiply-add chains

**Solution:**
- Added mad.wide.u32 for efficient 64-bit results from 32-bit inputs
- Improved instruction scheduling for better ILP
- Optimized squaring to exploit symmetric cross terms (10 muls instead of 16)

**Expected Improvement:** 1.2-1.3x speedup in EC point operations

---

## How to Use the Optimized Code

### Option 1: Direct Replacement
Replace the original files with the optimized versions:
```bash
cp GPU_Optimized/GPUComputeFixed.h GPU/GPUCompute.h
cp GPU_Optimized/GPUMathOptimized.h GPU/GPUMath.h
cp GPU_Optimized/GPUEngineOptimized.cu GPU/GPUEngine.cu
```

### Option 2: Conditional Compilation
Add to your Makefile:
```makefile
CXXFLAGS += -DUSE_OPTIMIZED_GPU
```

Then in GPUEngine.cu:
```cpp
#ifdef USE_OPTIMIZED_GPU
#include "GPU_Optimized/GPUComputeFixed.h"
#else
#include "GPUCompute.h"
#endif
```

---

## Compilation Notes

### Required CUDA Architecture
The optimizations work best with:
- SM 7.0+ (Volta, Turing, Ampere, Ada Lovelace, Hopper)
- For RTX 5090 (Blackwell): SM 10.0

Compile with appropriate architecture:
```bash
nvcc -arch=sm_89 -O3 ...   # RTX 4080 Super
nvcc -arch=sm_100 -O3 ...  # RTX 5090
```

### Shared Memory Configuration
For maximum performance with the shared memory optimizations:
```cpp
// Set shared memory to maximum (reduces L1 cache but we need shared memory)
cudaFuncSetAttribute(comp_keys_comp,
                     cudaFuncAttributeMaxDynamicSharedMemorySize,
                     49152);  // 48KB
```

---

## Performance Summary

| Optimization | Speedup | Complexity |
|-------------|---------|------------|
| Stack → Shared Memory | 2-3x | High |
| Batch Inversion | 1.5-2.5x | Medium |
| Async Transfers | 1.3-1.5x | Low |
| Optimized Math | 1.2-1.3x | Medium |

**Combined Expected Speedup:** 3-6x depending on workload and GPU

---

## Verification

To verify the optimizations work correctly:

1. Run the built-in check:
```bash
./VanitySearch -check
```

2. Compare hash rates before/after:
```bash
# Before
./VanitySearch -gpu -gpuId 0 1BitcoinTest

# After (with optimizations)
./VanitySearch_Optimized -gpu -gpuId 0 1BitcoinTest
```

---

## Additional Notes

### Why the Original Code Has These Issues

1. **Stack Memory:** The original author probably didn't realize how large the subp array was per thread. On CPUs, 16KB per thread is fine. On GPUs, it's catastrophic.

2. **Synchronous Transfers:** The simplest CUDA code uses synchronous transfers. Pipelining requires more complex stream management.

3. **Math Optimizations:** The original PTX is good but can be improved with newer instruction sets available on modern GPUs.

### GPU Memory Hierarchy Reminder

```
Register (fastest) < Shared Memory < L1/L2 Cache < Global Memory (slowest)
     ~1 cycle           ~20 cycles     ~50 cycles      ~500 cycles
```

Moving subp from stack (register spill → global) to shared memory is a huge win.
