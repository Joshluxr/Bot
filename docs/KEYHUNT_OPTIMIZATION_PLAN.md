# Keyhunt Optimization Integration Plan

## Overview

This document outlines the plan to integrate four key optimizations from the [keyhunt](https://github.com/albertobsd/keyhunt) codebase into our GPU bloom filter Bitcoin address search system.

**Target Files:**
- `/root/repo/bloom_search/src/BloomSearch32Silent.cu`
- `/root/repo/bloom_search/GPU/GPUComputeBloom.h`
- `/root/repo/bloom_search/GPU/GPUMath.h`

**Current Performance:** ~2.4 GKey/s per RTX 4080 SUPER (~19-20 GKey/s total with 8 GPUs)

**Target Performance:** 3-6x improvement → ~7-14 GKey/s per GPU

---

## 1. Batch Modular Inversion (Montgomery's Trick)

### What It Does
Instead of computing N modular inversions individually (each very expensive), compute them all with **only ONE modular inversion** plus 3N-3 multiplications.

### Current Implementation (GPU)
```cuda
// In BloomSearch32Silent.cu - line 66
_ModInvGrouped(dx);  // Already exists but may not be optimal
```

Looking at the current code, `_ModInvGrouped` is already implemented. However, keyhunt's implementation shows the optimal algorithm.

### Keyhunt's Algorithm (from IntGroup.cpp)
```cpp
void IntGroup::ModInv() {
    // Step 1: Compute cumulative products
    // subp[0] = ints[0]
    // subp[1] = ints[0] * ints[1]
    // subp[2] = ints[0] * ints[1] * ints[2]
    // ... etc
    subp[0].Set(&ints[0]);
    for (int i = 1; i < size; i++) {
        subp[i].ModMulK1(&subp[i-1], &ints[i]);
    }

    // Step 2: ONE modular inverse of the final product
    inverse.Set(&subp[size-1]);
    inverse.ModInv();  // ONLY ONE expensive operation!

    // Step 3: Propagate inverses backwards
    for (int i = size-1; i > 0; i--) {
        // ints[i]^-1 = subp[i-1] * inverse
        newValue.ModMulK1(&subp[i-1], &inverse);
        // Update inverse = inverse * ints[i] for next iteration
        inverse.ModMulK1(&ints[i]);
        ints[i].Set(&newValue);
    }
    ints[0].Set(&inverse);
}
```

### GPU Implementation Plan

**File:** `/root/repo/bloom_search/GPU/GPUMath.h`

```cuda
// Add after existing _ModInv function

// Batch modular inversion using Montgomery's trick
// Computes inverses of dx[0..size-1] in-place
// Uses only ONE modular inverse + 3*(size-1) multiplications
__device__ void _ModInvGroupedOptimized(uint64_t dx[][4], int size) {
    uint64_t subp[GRP_SIZE/2+1][4];  // Cumulative products
    uint64_t inverse[4];
    uint64_t newValue[4];

    // Step 1: Compute cumulative products
    Load256(subp[0], dx[0]);
    for (int i = 1; i < size; i++) {
        _ModMult(subp[i], subp[i-1], dx[i]);
    }

    // Step 2: Single modular inverse (expensive operation)
    _ModInv(inverse, subp[size-1]);

    // Step 3: Propagate inverses backward
    for (int i = size-1; i > 0; i--) {
        _ModMult(newValue, subp[i-1], inverse);
        _ModMult(inverse, inverse, dx[i]);
        Load256(dx[i], newValue);
    }
    Load256(dx[0], inverse);
}
```

### Verification
The current `_ModInvGrouped` should be checked to see if it already implements this. If not, replace it with the optimized version.

### Expected Speedup
- **Before:** N modular inversions (each ~1000 GPU cycles)
- **After:** 1 modular inversion + 3N multiplications (each ~50 GPU cycles)
- **Speedup for N=513:** ~6x faster for the inversion step

---

## 2. Three-Tier Bloom Filter Cascade

### What It Does
Uses three bloom filters with decreasing sizes to dramatically reduce false positives. Each tier filters out more candidates before the expensive database lookup.

### Current Implementation
```
GPU Prefix Bitmap (512MB) → CPU Bloom Filter → Database Lookup
```

### Keyhunt's Three-Tier System
```
Tier 1: bloom_bP      (Largest, ~7-58 GB for BSGS, ~200MB for addresses)
Tier 2: bloom_bPx2nd  (Medium, ~230 MB - 1.8 GB)
Tier 3: bloom_bPx3rd  (Smallest, ~7-57 MB)
```

### Why This Matters for Our System

Current false positive rate with single bloom filter:
- Bloom filter: 0.3% false positive rate
- At 2.4 GKey/s → ~7.2 million false positives per second!

With three-tier cascade:
- Tier 1: 0.3% pass → 7.2M candidates
- Tier 2: 0.3% of those → 21,600 candidates
- Tier 3: 0.3% of those → 65 candidates
- **Result:** 99.999% reduction in false positives

### Implementation Plan

**Step 1: Create Bloom Filter Generator Script**

**File:** `/root/repo/bloom_search/build_tiered_bloom.py`

```python
#!/usr/bin/env python3
"""
Build three-tier bloom filter system for GPU address search.
"""

import mmh3
import struct
import math
from bitarray import bitarray

class TieredBloomBuilder:
    def __init__(self, addresses_file, error_rate=0.001):
        self.addresses = self.load_addresses(addresses_file)
        self.error_rate = error_rate

    def load_addresses(self, filepath):
        """Load hash160 addresses from file."""
        addresses = []
        with open(filepath, 'rb') as f:
            while True:
                data = f.read(20)
                if not data:
                    break
                addresses.append(data)
        return addresses

    def calculate_bloom_params(self, n_items, error_rate):
        """Calculate optimal bloom filter parameters."""
        # m = -(n * ln(p)) / (ln(2)^2)
        m = int(-n_items * math.log(error_rate) / (math.log(2) ** 2))
        # k = (m/n) * ln(2)
        k = max(1, int((m / n_items) * math.log(2)))
        return m, k

    def build_tier(self, items, tier_name, error_rate):
        """Build a single bloom filter tier."""
        n = len(items)
        bits, hashes = self.calculate_bloom_params(n, error_rate)

        print(f"  {tier_name}: {n:,} items, {bits:,} bits ({bits//8//1024//1024} MB), {hashes} hashes")

        # Generate random seeds
        import random
        seeds = [random.randint(0, 0xFFFFFFFF) for _ in range(hashes)]

        # Build filter
        bf = bitarray(bits)
        bf.setall(0)

        for item in items:
            for seed in seeds:
                h = mmh3.hash(item, seed, signed=False)
                bf[h % bits] = 1

        return bf, seeds, bits, hashes

    def build_all_tiers(self, output_prefix):
        """Build all three tiers."""
        n = len(self.addresses)

        # Tier 1: Full set, low error rate (GPU-side)
        print(f"Building Tier 1 (GPU bloom)...")
        t1_bf, t1_seeds, t1_bits, t1_hashes = self.build_tier(
            self.addresses, "tier1", self.error_rate
        )

        # Tier 2: ~1/32 of tier 1 items (randomly sampled for structure)
        # Actually uses same addresses but smaller filter = higher error rate
        print(f"Building Tier 2 (CPU bloom 1)...")
        t2_error = self.error_rate * 10  # Higher error rate = smaller filter
        t2_bf, t2_seeds, t2_bits, t2_hashes = self.build_tier(
            self.addresses, "tier2", t2_error
        )

        # Tier 3: Smallest filter for final check before DB
        print(f"Building Tier 3 (CPU bloom 2)...")
        t3_error = self.error_rate * 100
        t3_bf, t3_seeds, t3_bits, t3_hashes = self.build_tier(
            self.addresses, "tier3", t3_error
        )

        # Save files
        self.save_bloom(f"{output_prefix}_tier1.bloom", t1_bf, t1_seeds, t1_bits)
        self.save_bloom(f"{output_prefix}_tier2.bloom", t2_bf, t2_seeds, t2_bits)
        self.save_bloom(f"{output_prefix}_tier3.bloom", t3_bf, t3_seeds, t3_bits)

        print(f"\nTotal memory: {(t1_bits + t2_bits + t3_bits)//8//1024//1024} MB")
```

**Step 2: Modify GPU Kernel for Three-Tier Checking**

**File:** `/root/repo/bloom_search/GPU/GPUBloomTiered.h`

```cuda
#ifndef GPU_BLOOM_TIERED_H
#define GPU_BLOOM_TIERED_H

// Three-tier bloom filter structure
struct TieredBloom {
    // Tier 1 - GPU global memory (largest, most accurate)
    uint32_t* tier1_data;
    uint64_t  tier1_bits;
    uint32_t* tier1_seeds;
    int       tier1_hashes;

    // Tier 2 - GPU global memory (medium)
    uint32_t* tier2_data;
    uint64_t  tier2_bits;
    uint32_t* tier2_seeds;
    int       tier2_hashes;

    // Tier 3 - GPU shared memory candidate (smallest)
    uint32_t* tier3_data;
    uint64_t  tier3_bits;
    uint32_t* tier3_seeds;
    int       tier3_hashes;
};

__device__ __forceinline__ bool bloom_check_tier(
    const uint8_t* hash160,
    const uint32_t* data,
    uint64_t bits,
    const uint32_t* seeds,
    int num_hashes
) {
    for (int i = 0; i < num_hashes; i++) {
        uint32_t h = murmur3_32(hash160, 20, seeds[i]);
        uint64_t bitPos = h % bits;
        uint64_t wordPos = bitPos >> 5;  // Divide by 32
        uint32_t bitMask = 1 << (bitPos & 31);

        if (!(data[wordPos] & bitMask)) {
            return false;
        }
    }
    return true;
}

__device__ __noinline__ void CheckPointTieredBloom(
    uint32_t* _h,
    int32_t incr,
    int32_t endo,
    int32_t mode,
    const TieredBloom* bloom,
    uint32_t maxFound,
    uint32_t* out
) {
    // Tier 1 check (fastest rejection)
    if (!bloom_check_tier((uint8_t*)_h,
            bloom->tier1_data, bloom->tier1_bits,
            bloom->tier1_seeds, bloom->tier1_hashes)) {
        return;  // Definitely not in set
    }

    // Tier 2 check (filter more false positives)
    if (!bloom_check_tier((uint8_t*)_h,
            bloom->tier2_data, bloom->tier2_bits,
            bloom->tier2_seeds, bloom->tier2_hashes)) {
        return;  // False positive from tier 1
    }

    // Tier 3 check (final filter before output)
    if (!bloom_check_tier((uint8_t*)_h,
            bloom->tier3_data, bloom->tier3_bits,
            bloom->tier3_seeds, bloom->tier3_hashes)) {
        return;  // False positive from tier 2
    }

    // All three tiers passed - high confidence match
    // Add to output for CPU database verification
    uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
    uint32_t pos = atomicAdd(out, 1);
    if (pos < maxFound) {
        out[pos * ITEM_SIZE32 + 1] = tid;
        out[pos * ITEM_SIZE32 + 2] = (incr << 16) | (mode << 15) | endo;
        out[pos * ITEM_SIZE32 + 3] = _h[0];
        out[pos * ITEM_SIZE32 + 4] = _h[1];
        out[pos * ITEM_SIZE32 + 5] = _h[2];
        out[pos * ITEM_SIZE32 + 6] = _h[3];
        out[pos * ITEM_SIZE32 + 7] = _h[4];
    }
}

#endif // GPU_BLOOM_TIERED_H
```

### Memory Layout Optimization

For optimal GPU performance:
- **Tier 1:** GPU global memory (L2 cache friendly)
- **Tier 2:** GPU global memory or texture memory
- **Tier 3:** Constant memory if small enough (<64KB)

### Expected Improvement
- **False positive reduction:** ~111x (0.3% → 0.00027%)
- **CPU verification load:** Reduced by 99.7%
- **Memory overhead:** +50-100 MB (tier 2 + tier 3)

---

## 3. Endomorphism Optimization

### What It Does
Exploits the secp256k1 curve's special structure to generate 6 related addresses from each computed public key point, effectively multiplying throughput by 6x.

### Mathematical Background

The secp256k1 curve has an efficiently computable endomorphism:
```
λ = 0x5363AD4CC05C30E0A5261C028812645A122E22EA20816678DF02967C1B23BD72
β = 0x7AE96A2B657C0710C1396C28719501EEULL (mod p)

For any point P = (x, y):
  λ * P = (β * x, y)     (mod p)
  λ² * P = (β² * x, y)   (mod p)
```

This means for each computed point P, we can derive:
1. P = (x, y)           → Address 1
2. -P = (x, -y)         → Address 2
3. λP = (βx, y)         → Address 3
4. -λP = (βx, -y)       → Address 4
5. λ²P = (β²x, y)       → Address 5
6. -λ²P = (β²x, -y)     → Address 6

**Cost:** 2 modular multiplications per point (β*x and β²*x)
**Benefit:** 6 addresses checked instead of 1

### Current Implementation Status

Looking at `/root/repo/bloom_search/GPU/GPUComputeBloom.h`, endomorphism is **already partially implemented**:

```cuda
// Line 144-172: CheckHashCompBloom already uses endomorphism
__device__ __noinline__ void CheckHashCompBloom(...) {
    // Original point
    CHECK_BLOOM(h, incr, 0, 1);

    // Endomorphism #1: β × x
    ModMult(pe1x, px, _beta);
    CHECK_BLOOM(h, incr, 1, 1);

    // Endomorphism #2: β² × x
    ModMult(pe2x, px, _beta2);
    CHECK_BLOOM(h, incr, 2, 1);

    // Symmetric points (negate Y) - 3 more addresses
    ...
}
```

### Verification Required

Check if `_beta` and `_beta2` constants are correctly defined in GPUMath.h:

```cuda
// Expected values from keyhunt:
__device__ __constant__ uint64_t _beta[4] = {
    0xC1396C28719501EEULL,
    0x9CF0497512F58995ULL,
    0x6E64479EAC3434E9ULL,
    0x7AE96A2B657C0710ULL
};

__device__ __constant__ uint64_t _beta2[4] = {
    0x3EC693D68E6AFA40ULL,
    0x630FB68AED0A766AULL,
    0x919BB86153CBCB16ULL,
    0x851695D49A83F8EFULL
};
```

### Optimization: Cache Beta Multiplications

Currently each check computes β*x and β²*x separately. Can optimize by computing once per point:

```cuda
__device__ void CheckHashCompBloomOptimized(
    uint64_t *px, uint64_t *py, uint8_t isOdd, int32_t incr,
    uint32_t maxFound, uint32_t *out
) {
    uint32_t h[5];
    uint64_t pe1x[4], pe2x[4];

    // Compute endomorphism X values ONCE
    _ModMult(pe1x, px, _beta);
    _ModMult(pe2x, px, _beta2);

    // Check all 6 points with cached values
    _GetHash160Comp(px, isOdd, (uint8_t*)h);
    CHECK_BLOOM(h, incr, 0, 1);

    _GetHash160Comp(pe1x, isOdd, (uint8_t*)h);
    CHECK_BLOOM(h, incr, 1, 1);

    _GetHash160Comp(pe2x, isOdd, (uint8_t*)h);
    CHECK_BLOOM(h, incr, 2, 1);

    // Negated Y (just flip parity bit)
    uint8_t oddNeg = isOdd ^ 1;

    _GetHash160Comp(px, oddNeg, (uint8_t*)h);
    CHECK_BLOOM(h, -incr, 0, 1);

    _GetHash160Comp(pe1x, oddNeg, (uint8_t*)h);
    CHECK_BLOOM(h, -incr, 1, 1);

    _GetHash160Comp(pe2x, oddNeg, (uint8_t*)h);
    CHECK_BLOOM(h, -incr, 2, 1);
}
```

### Expected Speedup
- **Effective throughput:** 6x (checking 6 addresses per EC point)
- **Actual GPU compute:** +10% overhead for β multiplications
- **Net improvement:** ~5.5x effective speedup

---

## 4. Custom secp256k1 Optimizations

### What It Does
Keyhunt uses highly optimized 256-bit arithmetic specifically tuned for secp256k1's prime field.

### Key Optimizations from Keyhunt

#### 4.1 ModMulK1 - Fast Modular Multiplication

The secp256k1 prime has a special form: `p = 2^256 - 2^32 - 977`

This allows faster reduction:

```cpp
// From keyhunt's Int.cpp
void Int::ModMulK1(Int *a, Int *b) {
    // Standard 256x256 → 512-bit multiplication
    // Then fast reduction using p's special form

    // r = high_256_bits * 2^256 + low_256_bits
    // r mod p = low_256_bits + high_256_bits * (2^32 + 977)
}
```

#### 4.2 ModSquareK1 - Optimized Squaring

Squaring is ~1.5x faster than general multiplication due to symmetry.

#### 4.3 Montgomery Representation

For multiple operations on same values, Montgomery form avoids repeated divisions:
- Convert to Montgomery form once
- Do all multiplications in Montgomery space
- Convert back once at the end

### Current GPU Implementation Analysis

Looking at GPUMath.h, the current implementation uses PTX assembly for arithmetic. Key functions to optimize:

```cuda
// These are the hot spots:
_ModMult(result, a, b)   // 256-bit modular multiplication
_ModSqr(result, a)       // 256-bit modular squaring
_ModInv(result, a)       // 256-bit modular inverse (Fermat's)
```

### Optimization: Exploit secp256k1 Prime Structure

**File:** `/root/repo/bloom_search/GPU/GPUMathK1.h`

```cuda
// Fast reduction for secp256k1 prime: p = 2^256 - 0x1000003D1
// After 512-bit multiplication, reduce using:
// r mod p = r_low + r_high * 0x1000003D1

__device__ __forceinline__ void _ModReduceK1(uint64_t r[4], uint64_t t[8]) {
    // t[0..3] = low 256 bits
    // t[4..7] = high 256 bits

    uint64_t c = 0;
    uint64_t h[4] = {t[4], t[5], t[6], t[7]};

    // Multiply high part by 0x1000003D1 (= 2^32 + 977)
    // This is just h * 2^32 + h * 977

    // h * 977 (small constant multiplication)
    uint64_t mul977[5];
    UMUL128(mul977[0], mul977[1], h[0], 977ULL);
    UMUL128(mul977[2], mul977[3], h[1], 977ULL);
    // ... continue for h[2], h[3]

    // h * 2^32 (just shift left by 32 bits)
    uint64_t shift32[5] = {
        h[0] << 32,
        (h[0] >> 32) | (h[1] << 32),
        (h[1] >> 32) | (h[2] << 32),
        (h[2] >> 32) | (h[3] << 32),
        h[3] >> 32
    };

    // Add: t_low + mul977 + shift32
    // ... (carry-aware addition)

    // May need one more reduction if result >= p
}
```

### Performance Comparison

| Operation | Generic Mod | K1-Optimized | Speedup |
|-----------|-------------|--------------|---------|
| ModMult   | ~60 cycles  | ~45 cycles   | 1.3x    |
| ModSqr    | ~50 cycles  | ~35 cycles   | 1.4x    |
| ModInv    | ~1000 cycles| ~800 cycles  | 1.25x   |

### Expected Overall Speedup
- **Arithmetic operations:** 25-40% faster
- **Combined with batch inversion:** 2-3x overall

---

## Implementation Phases

### Phase 1: Verification & Benchmarking (1-2 hours)
1. Verify current batch modular inversion implementation
2. Benchmark current GPU kernel performance
3. Profile to identify actual bottlenecks
4. Verify endomorphism constants are correct

### Phase 2: Batch Inversion Optimization (2-3 hours)
1. Implement optimized Montgomery's trick if needed
2. Verify correctness with test vectors
3. Benchmark improvement

### Phase 3: Three-Tier Bloom Filter (4-6 hours)
1. Create Python builder script for tiered bloom filters
2. Modify GPU kernel to support three tiers
3. Optimize memory access patterns
4. Benchmark false positive reduction

### Phase 4: secp256k1 K1 Optimizations (3-4 hours)
1. Implement K1-specific reduction
2. Optimize ModMult and ModSqr
3. Verify correctness with test vectors
4. Benchmark improvement

### Phase 5: Integration & Testing (2-3 hours)
1. Integrate all optimizations
2. Full system benchmark
3. Verify no correctness regressions
4. Update deployment scripts

---

## Expected Results

| Optimization | Speedup Factor | Cumulative |
|--------------|----------------|------------|
| Batch Inversion | 1.2x | 1.2x |
| Three-Tier Bloom | 1.0x (reduces CPU load) | 1.2x |
| Endomorphism (verify) | Already 6x | 1.2x |
| K1 Arithmetic | 1.3x | 1.56x |

**Note:** Endomorphism is already implemented, so the main gains will come from batch inversion and K1 arithmetic optimizations.

**Realistic expectation:** 1.3-1.6x improvement on GPU throughput, plus massive reduction in CPU bloom filter verification load from three-tier cascade.

---

## Files to Modify

1. `/root/repo/bloom_search/GPU/GPUMath.h` - Add K1-optimized arithmetic
2. `/root/repo/bloom_search/GPU/GPUComputeBloom.h` - Optimize endomorphism caching
3. `/root/repo/bloom_search/src/BloomSearch32Silent.cu` - Integrate tiered bloom
4. `/root/repo/bloom_search/build_tiered_bloom.py` - New file for filter generation

---

## Testing Strategy

1. **Unit tests:** Verify each arithmetic operation with known test vectors
2. **Integration tests:** Compare output of optimized vs original kernel
3. **Performance tests:** Benchmark on single GPU before full deployment
4. **Correctness tests:** Run with known private keys to verify detection

---

## Rollback Plan

If issues arise:
1. Keep original kernel as `BloomSearch32Silent_original.cu`
2. Maintain backward-compatible bloom filter format
3. Add runtime flag to switch between implementations
