# K3 Bloom Filter Detection Issue - Root Cause & Solution

## Summary

A specific private key that should have been detected by K3 was being missed despite:
- Being confirmed in the h160db database
- Being at a predictable position (thread=256, iteration=205)
- The hash160 computation being correct

## Root Cause

**The bloom filter was built with MODULO but K3 uses AND mask.**

### Original Bloom Filter (Incompatible)
```python
# How the bloom filter was built:
bit_pos = murmur3_hash % bloom_bits  # MODULO operation
```

### K3's Bloom Check (What it expects)
```cuda
// K3's bloom_check_k3 function (BloomSearch32K3.cu line 127):
uint64_t bitPos = h & bitsMask;  // AND mask - requires power-of-2 size
```

### The Mismatch

When testing the target hash160 `abeddf6b115157b704de34c50d22beefbeb59c98`:

| Seed       | Hash       | MODULO (h % 335098344) | AND mask (h & 0x1fffffff) |
|------------|------------|------------------------|---------------------------|
| 0xa3b1799d | 0x076fb15d | 124,760,413 ✓         | 124,760,413 ✓            |
| 0x46685257 | 0xe6a56295 | 183,516,573 ✓         | 111,501,973 ✗            |
| 0x392456de | 0x71af18b2 | 231,808,810 ✓         | 296,687,794 ✓            |
| 0xbc8960a9 | 0x64b4d171 | 14,079,977 ✓          | 78,958,961 ✗             |
| ... | ... | ... | ... |

The bloom filter PASSES with MODULO but FAILS with AND mask because the bit positions are different!

## Solution

Rebuild the bloom filter using K3's AND mask method:

```bash
# On the GPU server:
python3 build_k3_bloom.py build /data/bloom_opt.h160db /data/k3_bloom.bloom /data/k3_bloom.seeds
```

Or run the automated deployment:
```bash
python3 deploy_fixed_k3.py
```

### Key Parameters for K3

When launching K3 with the new bloom filter:
```bash
./BloomSearch32K3 \
    -bloom /data/k3_bloom.bloom \
    -seeds /data/k3_bloom.seeds \
    -bits 1073741824 \  # Must be power of 2 (2^30)
    -hashes 12 \
    ...
```

**Critical**: The `-bits` parameter MUST be a power of 2 for K3's AND mask to work correctly.

## Files Created

1. **build_k3_bloom.py** - Builds K3-compatible bloom filter from h160db
2. **deploy_fixed_k3.py** - Automated deployment script for GPU server
3. **test_local_bloom.py** - Test script to verify bloom filter compatibility
4. **debug_k3_hash.py** - Debug script to verify hash computations

## Verification

After deploying the fix, the target should be found at:
- **Thread**: 256
- **Iteration**: 205
- **Hash160**: abeddf6b115157b704de34c50d22beefbeb59c98
- **Address**: 1Gg5WVQsrfk8L9uMpmtsFqW7NoS2ZpoKPs

## Technical Details

### K3's Bloom Filter Implementation

```cuda
// BloomSearch32K3.cu lines 117-135
__device__ __forceinline__ bool bloom_check_k3(
    const uint8_t* hash160,
    const uint32_t* data,
    uint64_t bitsMask,  // bits - 1 for power-of-2
    const uint32_t* seeds,
    int num_hashes
) {
    for (int i = 0; i < num_hashes; i++) {
        uint32_t h = murmur3_32_k3(hash160, 20, seeds[i]);
        uint64_t bitPos = h & bitsMask;  // K3 uses AND mask!
        uint64_t wordPos = bitPos >> 5;
        uint32_t bitMask = 1u << (bitPos & 31);
        if (!(data[wordPos] & bitMask)) {
            return false;
        }
    }
    return true;
}
```

### Why AND Mask is Faster

- MODULO operation: ~30+ CPU cycles (division is expensive)
- AND operation: 1 CPU cycle

K3 uses AND mask for performance, but this requires:
1. Bloom filter size must be a power of 2
2. Bloom filter must be built using AND mask (not MODULO)

## Conclusion

The bloom filter was built with MODULO for flexibility (any size), but K3 was designed for speed using AND mask. This mismatch caused valid entries to not be found.

The fix is simple: rebuild the bloom filter using the AND mask method with a power-of-2 size.
