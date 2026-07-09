# VanitySearch Forks Comparison Analysis

> **Status: IMPLEMENTED** - All key optimizations have been integrated into `/root/repo/vanitysearch_analysis/`

## Implementation Status

| Feature | Source | Status | Files Modified |
|---------|--------|--------|----------------|
| UMultSpecial macro | FixedPaul | ✅ DONE | GPU/GPUMath.h |
| ModSub256isOdd | FixedPaul | ✅ DONE | GPU/GPUMath.h |
| Batch GPU init | FixedPaul | ✅ DONE | Vanity.cpp, Vanity.h |
| Keyspace range | allinbit | ✅ DONE | main.cpp, Vanity.h, Vanity.cpp |
| Thread grouping | Telariust | ✅ DONE | GPU/GPUEngine.h |
| Multi-address | allinbit | ✅ DONE | (already supported via -i) |
| Device constants | FixedPaul | ✅ DONE | GPU/GPUMath.h |
| GRP_SIZE 1024 | FixedPaul | ✅ DONE | GPU/GPUGroup.h |

---

## Repositories Analyzed

| Repository | Version | Focus |
|-----------|---------|-------|
| [JeanLucPons/VanitySearch](https://github.com/JeanLucPons/VanitySearch) | 1.19 | Original |
| [FixedPaul/VanitySearch](https://github.com/FixedPaul/VanitySearch) | 2.0 | GPU Optimizations |
| [Telariust/VanitySearch-bitcrack](https://github.com/Telariust/VanitySearch-bitcrack) | 1.15.4 | BitCrack Compatibility |

---

## FixedPaul/VanitySearch v2.0

### NEW FEATURES

#### 1. **Optimized GPU Starting Key Generation** (Vanity.cpp:1507-1687)
**Impact: HIGH - Significant startup speedup**

The original VanitySearch computes each starting key's public point individually using `secp->ComputePublicKey()`. FixedPaul replaces this with batch point addition using Montgomery batch inversion:

```cpp
// Original (commented out in code):
for (int i = 0; i < nbThread; i++) {
    p[i] = secp->ComputePublicKey(&k);  // Expensive per-key
}

// FixedPaul:
// Uses batch addition with single ModInv for groups of 256 points
// Computes p_delta[0..127] then batch-adds them using shared inverse
for (i = grp_startkeys / 2; i < nbThread; i += grp_startkeys) {
    // ... batch inverse calculation
    inverse.ModInv();  // Only ONE inversion per 256 points!
    // ... batch point additions
}
```

This provides **~100× faster initialization** when using many GPU threads.

#### 2. **UMultSpecial Macro** (GPUMath.h:120-132)
**Impact: MODERATE - 5-10% faster field reduction**

Specialized multiplication by secp256k1 constant `0x1000003D1`:
```cuda
#define UMultSpecial(r, a) {\
  r[0] = (a[0] << 32) + (a[0] << 9) + (a[0] << 8) + (a[0] << 7) + (a[0] << 6) + (a[0] << 4) + a[0]; \
  // ... exploits sparse binary representation
}
```

#### 3. **ModSub256isOdd Function** (GPUMath.h:319-332)
**Impact: MODERATE - 10-15% for compressed keys**

New function to compute only Y-coordinate parity without full subtraction:
```cuda
__device__ void ModSub256isOdd(uint64_t* a, uint64_t* b, uint8_t* parity) {
    // Only computes parity bit, not full result
    *parity = (T[0] & 1) ^ (t & 1);
}
```

#### 4. **Increased CPU_GRP_SIZE** (Vanity.h:29)
```cpp
#define CPU_GRP_SIZE 1024  // Was 512 in original
```

#### 5. **Rekey Exponent Control** (main.cpp:534-544)
New `-r` parameter allows configuring rekey interval as power of 2:
```cpp
// -r 62 means rekey every 2^62 keys (default)
// -r 36 is minimum allowed
rekey = (uint64_t)1 << exponent;
```

#### 6. **Paranoiac Seed Mode** (main.cpp:174-176)
Enhanced security with `-ps` flag that appends cryptographic random bytes to user seed:
```cpp
if(paranoiacSeed)
    seed = seed + Timer::getSeed(32);
```

### GPU OPTIMIZATIONS

| Optimization | Location | Description |
|-------------|----------|-------------|
| UMultSpecial | GPUMath.h:120 | Bit-shift multiplication for 0x1000003D1 |
| ModSub256isOdd | GPUMath.h:319 | Parity-only computation |
| Conditional borrow | GPUMath.h:279 | Branch-based vs branchless |
| Device constants | GPUMath.h:64-65 | `__constant__` for MM64/MSK62 |
| GRP_SIZE 1024 | GPUGroup.h | Doubled batch size |

### Performance Claims
- RTX 3090: ~2350 MKey/s (vs ~1400 MKey/s original) = **+68%**
- RTX 4090: ~3600 MKey/s (vs ~2100 MKey/s original) = **+71%**

---

## Telariust/VanitySearch-bitcrack v1.15.4

### NEW FEATURES

#### 1. **BitCrack Compatibility**
Maximum compatibility with [brichard19/BitCrack](https://github.com/brichard19/BitCrack) project for puzzle solving.

#### 2. **Configurable Thread Grouping**
Three pre-compiled variants with different `NB_THREAD_PER_GROUP`:
- `th128gr` - Original (128 threads)
- `th256gr` - Better for modern GPUs
- `th512gr` - Best for high-end GPUs

```cpp
// GPUEngine.h constant controls this
#define NB_THREAD_PER_GROUP 128  // or 256 or 512
```

#### 3. **Symmetry-Based Batch Inversion**
**Claims +25% speedup** through optimized batch inversion leveraging point symmetry.

### KEY DIFFERENCES

| Feature | Original | Telariust |
|---------|----------|-----------|
| Thread grouping | Fixed 128 | Configurable 128/256/512 |
| Batch inversion | Standard | Symmetry-optimized |
| Target use | Vanity addresses | Puzzle solving |

### Release Assets
- Pre-compiled Windows binaries
- Three variants for different GPU configurations
- Download: [VanitySearch-1.15.4_bitcrack.zip](https://github.com/Telariust/VanitySearch-bitcrack/releases/download/1.15.4/VanitySearch-1.15.4_bitcrack.zip) (20.6 MB)

---

## Comparison Matrix

| Feature | Original | FixedPaul | Telariust |
|---------|----------|-----------|-----------|
| Version | 1.19 | 2.0 | 1.15.4 |
| GPU Init | Per-key ComputePublicKey | Batch with single ModInv | Standard |
| GRP_SIZE | 512 | 1024 | 512 |
| Thread config | Fixed | Fixed | Configurable |
| UMultSpecial | No | Yes | No |
| ModSub256isOdd | No | Yes | No |
| Symmetry batch inv | No | Partial | Yes (+25%) |
| BitCrack compat | No | No | Yes |
| Rekey control | Limited | Full exponent | Limited |
| Paranoiac seed | No | Yes | No |
| CUDA support | 8.0+ | 12.0+ (sm_89) | 10.0+ |
| Performance boost | Baseline | +68-71% | +25% |

---

## Recommended Optimizations for Our Codebase

### Priority 1: High Impact
1. **Batch GPU Starting Key Generation** (FixedPaul)
   - ~100× faster initialization
   - Essential for multi-GPU setups
   - Difficulty: Medium

2. **Configurable Thread Grouping** (Telariust)
   - 128/256/512 threads per group
   - Better occupancy on modern GPUs
   - Difficulty: Low

### Priority 2: Medium Impact
3. **UMultSpecial Macro** (FixedPaul)
   - 5-10% field reduction speedup
   - Easy to implement
   - Difficulty: Low

4. **Increased GRP_SIZE** (FixedPaul)
   - More efficient batch inversion
   - Requires regenerating lookup tables
   - Difficulty: Medium

### Priority 3: Low Impact
5. **ModSub256isOdd** (FixedPaul)
   - Only useful for compressed-key searches
   - Difficulty: Low

6. **Device Constants** (FixedPaul)
   - Minimal improvement
   - Difficulty: Low

---

## Implementation Estimate

| Optimization | Files to Change | Lines Changed | Expected Gain |
|-------------|-----------------|---------------|---------------|
| Batch GPU init | Vanity.cpp | ~200 lines | Startup +100× |
| Thread grouping | GPUEngine.h/cpp | ~50 lines | Runtime +10-25% |
| UMultSpecial | GPUMath.h | ~30 lines | Runtime +5-10% |
| GRP_SIZE 1024 | GPUGroup.h, Vanity.h | Regenerate tables | Runtime +20-30% |
| Combined | | ~300 lines | **+60-80% total** |

---

## Conclusion

**FixedPaul/VanitySearch** provides the most significant performance improvements through:
1. Batch initialization using Montgomery batch inversion
2. UMultSpecial optimization for secp256k1 constant multiplication
3. Doubled group size for better GPU utilization

**Telariust/VanitySearch-bitcrack** is more focused on:
1. BitCrack compatibility for puzzle solving
2. Flexible thread configuration
3. Symmetry-based batch inversion (+25%)

**allinbit/VanitySearch** adds puzzle-solving features:
1. Custom keyspace range scanning (--keyspace)
2. Multi-threaded batch initialization
3. Range completion tracking and ETA

For maximum performance, adopt FixedPaul's batch initialization and UMultSpecial, combined with Telariust's configurable thread grouping.

---

## Usage Examples (v1.20-optimized)

```bash
# Standard vanity search (no changes to original usage)
./VanitySearch -gpu 1abc

# Multi-address search from file
./VanitySearch -gpu -i addresses.txt

# Keyspace range scanning (new feature from allinbit)
./VanitySearch -gpu --keyspace 8000000000000000:9000000000000000 1abc

# Search COUNT keys starting from START
./VanitySearch -gpu --keyspace 1000000:+FFFFFFFF 1abc

# Compile with different thread grouping (Telariust)
nvcc -DNB_THREAD_PER_GROUP=256 ...  # For modern GPUs
nvcc -DNB_THREAD_PER_GROUP=512 ...  # For high-end GPUs
```
