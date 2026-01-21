# K3 Bloom Filter Detection Issue - Root Cause & Solution

## Executive Summary

K3 GPU Bloom Filter Search was failing to detect valid target keys despite them being in the database. After extensive debugging, the root cause was identified as a **hash method mismatch** between how the bloom filter was built and how K3 queries it.

**Root Cause**: Bloom filter built with MODULO (`h % bits`), but K3 uses AND mask (`h & (bits-1)`)

**Impact**: Valid entries fail bloom filter checks, causing false negatives

**Solution**: Rebuild bloom filter using K3-compatible AND mask method

---

## Problem Description

A specific private key that should have been detected by K3 was being missed:

- **Target Private Key**: `74120947517767895891355266452452269842804955139343486161984562552406380210176`
- **Target Hash160 (uncompressed)**: `abeddf6b115157b704de34c50d22beefbeb59c98`
- **Target Address**: `1Gg5WVQsrfk8L9uMpmtsFqW7NoS2ZpoKPs`
- **Expected Position**: Thread 256, Iteration 205

Despite:
- ✅ Being confirmed in the h160db database
- ✅ Hash160 computation matching expected value
- ✅ Being at a predictable, reachable position

The key was NOT being found by K3.

---

## Investigation Process

### Step 1: Verify Hash Computation

Confirmed that Python's hash160 computation matches K3's expected output:

```
Target hash160 (uncompressed): abeddf6b115157b704de34c50d22beefbeb59c98
Expected hash160:              abeddf6b115157b704de34c50d22beefbeb59c98
Match: True
```

### Step 2: Verify Thread/Iteration Calculation

Confirmed the target would be processed at:
- **Thread**: 256 (offset 210176 mod 1024)
- **Iteration**: 205 (offset 210176 / 1024)

### Step 3: Test Bloom Filter Methods

Tested the target hash160 against the bloom filter using BOTH methods:

#### MODULO Method (Original):
```
Testing with MODULO (h % 335098344):
  Seed a3b1799d: h=076fb15d bitPos=124,760,413 -> PASS
  Seed 46685257: h=e6a56295 bitPos=183,516,573 -> PASS
  Seed 392456de: h=71af18b2 bitPos=231,808,810 -> PASS
  Seed bc8960a9: h=64b4d171 bitPos=14,079,977 -> PASS
  Seed 6c031199: h=68176f87 bitPos=70,874,623 -> PASS
  Seed 07a0ca6e: h=6e3216e4 bitPos=173,284,700 -> PASS
  Seed 37f8a88b: h=2fbe32a1 bitPos=130,797,265 -> PASS
  Seed 8b8148f6: h=da712355 bitPos=313,864,261 -> PASS
RESULT: ALL PASS ✓
```

#### AND Mask Method (K3):
```
Testing with AND mask (h & 0x1fffffff):
  Seed a3b1799d: h=076fb15d bitPos=124,760,413 -> PASS
  Seed 46685257: h=e6a56295 bitPos=111,501,973 -> FAIL ✗
  Seed 392456de: h=71af18b2 bitPos=296,687,794 -> PASS
  Seed bc8960a9: h=64b4d171 bitPos=78,958,961 -> FAIL ✗
  Seed 6c031199: h=68176f87 bitPos=135,753,607 -> PASS
  Seed 07a0ca6e: h=6e3216e4 bitPos=238,163,684 -> PASS
  Seed 37f8a88b: h=2fbe32a1 bitPos=264,123,041 -> PASS
  Seed 8b8148f6: h=da712355 bitPos=443,622,229 -> FAIL ✗
RESULT: FAILED ✗
```

**The bloom filter PASSES with MODULO but FAILS with AND mask!**

---

## Root Cause Analysis

### Original Bloom Filter Construction (Incompatible)
```python
# How the bloom filter was originally built:
bit_pos = murmur3_hash % bloom_bits  # MODULO operation
```

### K3's Bloom Check Implementation (What it expects)
```cuda
// K3's bloom_check_k3 function (BloomSearch32K3.cu line 127):
uint64_t bitPos = h & bitsMask;  // AND mask - requires power-of-2 size
```

### Why the Mismatch Occurs

| Seed       | Hash       | MODULO (h % 335098344) | AND mask (h & 0x1fffffff) | Match? |
|------------|------------|------------------------|---------------------------|--------|
| 0xa3b1799d | 0x076fb15d | 124,760,413           | 124,760,413               | ✓      |
| 0x46685257 | 0xe6a56295 | 183,516,573           | 111,501,973               | ✗      |
| 0x392456de | 0x71af18b2 | 231,808,810           | 296,687,794               | ✗      |
| 0xbc8960a9 | 0x64b4d171 | 14,079,977            | 78,958,961                | ✗      |

The bit positions are DIFFERENT because:
- MODULO: `h % 335098344` (non-power-of-2)
- AND mask: `h & 0x1fffffff` (536870911, next power of 2 minus 1)

### Why K3 Uses AND Mask

Performance optimization:
- **MODULO operation**: ~30+ CPU/GPU cycles (division is expensive)
- **AND operation**: 1 cycle

K3 uses AND mask for speed, but this requires:
1. Bloom filter size MUST be a power of 2
2. Bloom filter MUST be built using AND mask (not MODULO)

---

## Solution

### Option 1: Automated Deployment (Recommended)

```bash
python3 deploy_fixed_k3.py
```

This script:
1. Connects to GPU server
2. Builds K3-compatible bloom filter from h160db
3. Verifies target hash160 passes
4. Launches K3 with fixed bloom filter
5. Monitors for target detection

### Option 2: Manual Build

```bash
# On the GPU server:
python3 build_k3_bloom.py build /data/bloom_opt.h160db /data/k3_bloom.bloom /data/k3_bloom.seeds 1073741824 12
```

Parameters:
- `1073741824` = 2^30 bits (128 MB, must be power of 2)
- `12` = number of hash functions

### Option 3: Test First

```bash
# Verify bloom filter compatibility
python3 test_local_bloom.py

# Test specific hash160
python3 build_k3_bloom.py test /data/k3_bloom.bloom /data/k3_bloom.seeds abeddf6b115157b704de34c50d22beefbeb59c98
```

---

## K3 Launch Parameters

After building the fixed bloom filter:

```bash
./BloomSearch32K3 \
    -gpu 0 \
    -prefix /data/prefix32.bin \
    -bloom /data/k3_bloom.bloom \
    -seeds /data/k3_bloom.seeds \
    -bits 1073741824 \
    -hashes 12 \
    -start "74120947517767895891355266452452269842804955139343486161984562552406380000000" \
    -both
```

**Critical**: The `-bits` parameter MUST be a power of 2!

---

## Files Created

| File | Purpose |
|------|---------|
| `build_k3_bloom.py` | Builds K3-compatible bloom filter using AND mask |
| `deploy_fixed_k3.py` | Automated deployment script for GPU server |
| `test_local_bloom.py` | Tests bloom filter compatibility (MODULO vs AND) |
| `debug_k3_hash.py` | Verifies hash160 computation and thread/iteration |
| `k3_debug_test.py` | Comprehensive debug test for GPU server |
| `check_gpu_server.py` | Checks GPU server status and processes |

---

## Verification

After deploying the fix, verify the target is found:

```bash
# Monitor K3 logs
tail -f /tmp/k3_gpu0_test.log | grep -i candidate

# Search for target hash160
grep abeddf6b /tmp/k3_gpu0_test.log
```

Expected output:
```
[K3 CANDIDATE UNCOMP] tid=256 meta=00000000 hash160=abeddf6b115157b704de34c50d22beefbeb59c98
```

---

## Technical Reference

### K3 Bloom Filter Check (CUDA)

```cuda
// BloomSearch32K3.cu lines 117-135
__device__ __forceinline__ bool bloom_check_k3(
    const uint8_t* hash160,
    const uint32_t* data,
    uint64_t bitsMask,  // bits - 1 for power-of-2
    const uint32_t* seeds,
    int num_hashes
) {
    #pragma unroll 4
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

### K3 Thread/Iteration Mapping

```
init_keys_from_decimal_start: thread t gets private key = start + t
Each kernel iteration: thread advances by STEP_SIZE (1024) keys

To find offset O from start:
  thread_id = O % STEP_SIZE
  iteration = O / STEP_SIZE

Example: offset 210176
  thread_id = 210176 % 1024 = 256
  iteration = 210176 / 1024 = 205
```

---

## Conclusion

The bloom filter was built with MODULO for flexibility (any size), but K3 was designed for speed using AND mask. This fundamental mismatch caused valid entries to fail the bloom filter check, resulting in false negatives.

**The fix is simple**: Rebuild the bloom filter using the AND mask method with a power-of-2 size.

This issue highlights the importance of ensuring that data structures are built using the same algorithm that will query them.
