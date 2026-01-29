# SearchK4 Debugging History

This document details all critical bugs found and fixed during the development of SearchK4, a GPU-accelerated Bitcoin vanity address search tool.

## Overview

SearchK4 is designed to search for Bitcoin private keys that produce addresses matching specific prefixes. It uses 4x NVIDIA RTX 5090 GPUs, each capable of ~1.7 billion keys/second.

**Total bugs fixed: 6 major issues**

---

## Bug #1: Infinite Loop in Modular Multiplication (v1.0)

### Symptom
Program hangs indefinitely during key initialization.

### Location
`SearchK4_fast.cu` - `mod_mul()` function

### Root Cause
The original modular multiplication had a buggy reduction loop that caused infinite loops when handling carries during secp256k1 field reduction.

```cpp
// BUGGY CODE - infinite loop on certain inputs
while (result >= P) {
    result -= P;  // Could loop forever due to improper carry handling
}
```

### Fix
Implemented proper secp256k1 reduction using the curve's special form `p = 2^256 - 0x1000003D1`:

```cpp
// FIXED CODE - proper reduction
// high * 2^256 mod p = high * 0x1000003D1 mod p
static void mod_mul(uint64_t* r, const uint64_t* a, const uint64_t* b) {
    // Full 512-bit multiplication
    uint64_t t[8];
    mul256(t, a, b);

    // Reduce using secp256k1 special form
    // If result >= 2^256, subtract and add high * 0x1000003D1
    reduce_secp256k1(r, t);
}
```

### Impact
Program could not initialize even a single key before the fix.

---

## Bug #2: Expensive Per-Key Modular Inversions (v1.0)

### Symptom
Key initialization extremely slow - only ~1 key/second instead of 65,000+.

### Location
`SearchK4_fast.cu` - `init_keys_from_start()` function

### Root Cause
Original code computed one modular inverse (~256 field multiplications) for every single key:

```cpp
// SLOW CODE - O(n) inversions
for (int i = 0; i < nbThread; i++) {
    // Each point addition requires computing 1/(x2-x1)
    mod_inv(inv, dx);  // ~256 multiplications EACH TIME
    // ... compute point ...
}
```

### Fix
Two optimizations:

1. **Jacobian Coordinates**: Perform all EC operations without division, only convert to affine at the end.

2. **Montgomery Batch Inversion**: Convert N inversions into 1 inversion + 3N multiplications:

```cpp
// FAST CODE - O(1) inversions via batching
// Step 1: Compute cumulative products
products[0] = dx[0];
for (int i = 1; i < n; i++)
    products[i] = products[i-1] * dx[i];

// Step 2: Single inversion
inv_all = mod_inv(products[n-1]);

// Step 3: Back-propagate to get individual inverses
for (int i = n-1; i > 0; i--) {
    inv[i] = inv_all * products[i-1];
    inv_all = inv_all * dx[i];
}
inv[0] = inv_all;
```

### Impact
**65,000x speedup** in key initialization (from ~1 key/sec to 65,000+ keys/sec).

---

## Bug #3: Memory Layout Mismatch (v1.1)

### Symptom
- GPU finds addresses but private keys don't match
- Reconstructed private key produces different address than what was matched
- **All found keys were INVALID**

### Location
`SearchK4_fast.cu` - `init_keys_from_start()` function, lines 829-895

### Root Cause
The fast key initialization stored public keys in **contiguous** format, but the GPU kernel expects **strided** format for coalesced memory access.

```cpp
// WRONG - Contiguous layout
// Key i stored at: X[0..3] = indices i*8+0, i*8+1, i*8+2, i*8+3
//                  Y[0..3] = indices i*8+4, i*8+5, i*8+6, i*8+7
for (int j = 0; j < 4; j++) {
    h_keys[i * 8 + j] = px[j];      // WRONG!
    h_keys[i * 8 + 4 + j] = py[j];  // WRONG!
}
```

The GPU kernel uses VanitySearch's `Load256A` macro which expects:
```
For thread t in block b (blockDim = 512):
  X[0] at index: b * 4096 + t
  X[1] at index: b * 4096 + t + 512
  X[2] at index: b * 4096 + t + 1024
  X[3] at index: b * 4096 + t + 1536
  Y[0] at index: b * 4096 + 2048 + t
  Y[1] at index: b * 4096 + 2048 + t + 512
  ...
```

### Fix
Changed initialization to use proper strided layout:

```cpp
// CORRECT - Strided layout matching GPU kernel
int block = t / NB_THREAD_PER_GROUP;  // 512 threads per block
int tidInBlock = t % NB_THREAD_PER_GROUP;
int blockBase = block * NB_THREAD_PER_GROUP * 8;  // 4096 per block
int xBase = blockBase + tidInBlock;
int yBase = blockBase + 4 * NB_THREAD_PER_GROUP + tidInBlock;

for (int j = 0; j < 4; j++) {
    h_keys[xBase + j * NB_THREAD_PER_GROUP] = px[j];  // Strided X
    h_keys[yBase + j * NB_THREAD_PER_GROUP] = py[j];  // Strided Y
}
```

### Impact
All keys found before this fix were invalid. Search had to be restarted from beginning.

---

## Bug #4: Private Key Y Parity Mismatch (v1.3)

### Symptom
For addresses starting with `03` (odd Y coordinate), the reconstructed private key produced a different address.

### Location
`SearchK4_fast.cu` - `reconstruct_privkey()` function, lines 950-990

### Root Cause
Bitcoin compressed public keys encode Y coordinate parity:
- `02` + X: Y is even
- `03` + X: Y is odd

When the GPU matches a `03`-prefix key, it's matching a point with odd Y. But the simple reconstruction `baseKey + offset` might produce a point with even Y (the curve has two Y values for each X).

### Fix
Check Y parity and negate the private key if needed:

```cpp
// Compute the public key point
scalar_mult_G(px, py, basePrivkey);
bool actualYOdd = (py[0] & 1) != 0;

// If parity doesn't match what the GPU found, negate the key
if (actualYOdd != reportedOdd) {
    // privkey = N - privkey (negate mod curve order)
    sub256(privkey, SECP_N, basePrivkey);
}
```

### Impact
~50% of found keys (those with odd Y) would have wrong private keys before this fix.

---

## Bug #5: Thread Stride Initialization (v1.4) - THE CRITICAL BUG

### Symptom
- Search claimed to check billions of keys but couldn't find a known target
- Target key at offset 766M from start wasn't found after "919 billion" keys checked
- Search was **~1000x slower than expected**

### Location
`SearchK4_fast.cu` - `init_keys_from_start()` function, line 864

### Root Cause
Thread initialization used consecutive offsets instead of strided offsets:

```cpp
// WRONG - Consecutive offsets
uint64_t offset = processed + i;  // offset = 1, 2, 3, 4, ...
get_iG(&iGx_batch[i*4], &iGy_batch[i*4], offset);
```

This meant:
- Thread 0 gets public key for: `baseKey + 0`
- Thread 1 gets public key for: `baseKey + 1`
- Thread 2 gets public key for: `baseKey + 2`
- ...

But the GPU kernel makes each thread check **1024 keys** around its starting point (±512):
- Thread 0 checks keys: `baseKey - 512` to `baseKey + 511`
- Thread 1 checks keys: `baseKey - 511` to `baseKey + 512`  ← **99.9% overlap!**
- Thread 2 checks keys: `baseKey - 510` to `baseKey + 513`

With 65,536 threads, only **~66,000 unique keys** were checked per iteration, not 67 million!

### Fix
Use strided offsets so threads cover non-overlapping ranges:

```cpp
// CORRECT - Strided offsets
uint64_t offset = (uint64_t)(processed + i) * STEP_SIZE;  // offset = 1024, 2048, 3072, ...
get_iG(&iGx_batch[i*4], &iGy_batch[i*4], offset);
```

Now:
- Thread 0 gets key for: `baseKey + 0*1024`
- Thread 1 gets key for: `baseKey + 1*1024`
- Thread 2 gets key for: `baseKey + 2*1024`

Coverage becomes:
- Thread 0: `baseKey - 512` to `baseKey + 511`
- Thread 1: `baseKey + 512` to `baseKey + 1535`  ← **No overlap!**
- Thread 2: `baseKey + 1536` to `baseKey + 2559`

Also fixed private key reconstruction to match:

```cpp
// OLD (wrong)
add256_scalar(basePrivkey, g_baseKey, (uint64_t)tid);

// NEW (correct)
add256_scalar(basePrivkey, g_baseKey, (uint64_t)tid * STEP_SIZE);
```

### Impact
This was the **root cause** of not finding the target key. The search was effectively 1000x slower than expected because it kept re-checking the same ~66K keys instead of covering 67M new keys per iteration.

**Before fix**: Target at offset 766M would require ~748,000 iterations (~4+ hours)
**After fix**: Target found in iteration 11 (~0.1 seconds)

---

## Verification

After all fixes, tested with start point 10M keys before target:
```
Start: 0x412cc8256ff579da05f048cafb7e2b82b876bbfc67e82901ec73dea8f211a22f
Target: 0x412cc8256ff579da05f048cafb7e2b82b876bbfc67e82901ec73dea8f2aa38af
```

Result:
```
[Thu Jan 29 04:13:52 2026] Pattern='1FeexV6bA' Address=1FeexV6bAj3wcS8docGuw6Wo8dr3nqb2T1
  PrivKey (HEX): 0x412cc8256ff579da05f048cafb7e2b82b876bbfc67e82901ec73dea8f2aa38af
  tid=9766 incr=128 parity=0 iter=0
```

**Target found immediately in iteration 0!**

---

## Summary Table

| Bug | Version | Location | Symptom | Fix | Impact |
|-----|---------|----------|---------|-----|--------|
| Infinite loop in mod_mul | v1.0 | `mod_mul()` | Program hangs | Proper secp256k1 reduction | Couldn't run at all |
| Slow inversion | v1.0 | `init_keys_from_start()` | 1 key/sec | Batch inversion + Jacobian coords | 65,000x speedup |
| Memory layout | v1.1 | `init_keys_from_start()` | Invalid keys | Strided layout | All keys invalid |
| Y parity | v1.3 | `reconstruct_privkey()` | Wrong key for 03-prefix | Check parity, negate if needed | 50% keys wrong |
| **Thread stride** | **v1.4** | `init_keys_from_start()` line 864 | **Can't find target** | **`offset * STEP_SIZE`** | **1000x slower** |

---

## Files Modified

1. **SearchK4_fast.cu** - Main CUDA implementation
   - `mod_mul()` - Fixed reduction algorithm
   - `init_keys_from_start()` - Fixed memory layout and thread stride
   - `reconstruct_privkey()` - Fixed Y parity handling

2. **CPUGroup.h** - Precomputed generator point table (512 entries)

3. **patterns.txt** - Search patterns including `1FeexV6bA`

---

## Bug #6: Invalid Address Checksums (v1.5)

### Symptom
Found addresses had **invalid checksums** when verified externally:
```
Address: 1FeexV6bAj3wcS8docGuw6Wo8dr3jvjKKP
Checksum: INVALID (got 032714d2, expected 8177dc66)
```

The addresses displayed in results were not valid Bitcoin addresses.

### Location
`SearchK4_fast.cu` - `hash160_to_address_host()` and `privkey_to_wif()` functions

### Root Cause
The host-side address and WIF generation functions used a **fake checksum** instead of proper Bitcoin double-SHA256:

```cpp
// WRONG - Simple hash, NOT Bitcoin checksum
uint32_t chksum = 0;
for (int i = 0; i < 21; i++) chksum = chksum * 31 + data[i];
data[21] = (chksum >> 24) & 0xFF;
data[22] = (chksum >> 16) & 0xFF;
data[23] = (chksum >> 8) & 0xFF;
data[24] = chksum & 0xFF;
```

Bitcoin addresses use **double SHA256** for the checksum (first 4 bytes of SHA256(SHA256(payload))).

### Fix
Implemented a proper SHA256 function and used double-SHA256 for checksums:

```cpp
// Host-side SHA256 implementation
static void sha256_host(const uint8_t* data, size_t len, uint8_t* hash) {
    // Full SHA256 implementation with proper padding and compression
    // ...
}

// CORRECT - Bitcoin standard checksum
void hash160_to_address_host(const uint8_t* hash160, char* addr) {
    uint8_t data[25];
    data[0] = 0x00;  // Mainnet P2PKH version
    memcpy(data + 1, hash160, 20);

    // Double SHA256 checksum
    uint8_t sha1[32], sha2[32];
    sha256_host(data, 21, sha1);
    sha256_host(sha1, 32, sha2);

    data[21] = sha2[0];
    data[22] = sha2[1];
    data[23] = sha2[2];
    data[24] = sha2[3];
    // ... base58 encode ...
}
```

Same fix applied to `privkey_to_wif()` for WIF format private keys.

### Verification
```
Input hash160: a0b0d60e5991578ed37cbda2b17d8b2ce23ab295
Generated:     1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF
Expected:      1FeexV6bAHb8ybZjqQMjJrcCrHGW9sb6uF
Match:         YES
```

### Impact
**All addresses displayed before this fix had invalid checksums.** The GPU search still worked correctly (it matches on hash160 prefix, not address string), but the displayed addresses in result files could not be used directly - they would be rejected by wallets and block explorers.

---

## Summary Table

| Bug | Version | Location | Symptom | Fix | Impact |
|-----|---------|----------|---------|-----|--------|
| Infinite loop in mod_mul | v1.0 | `mod_mul()` | Program hangs | Proper secp256k1 reduction | Couldn't run at all |
| Slow inversion | v1.0 | `init_keys_from_start()` | 1 key/sec | Batch inversion + Jacobian coords | 65,000x speedup |
| Memory layout | v1.1 | `init_keys_from_start()` | Invalid keys | Strided layout | All keys invalid |
| Y parity | v1.3 | `reconstruct_privkey()` | Wrong key for 03-prefix | Check parity, negate if needed | 50% keys wrong |
| **Thread stride** | **v1.4** | `init_keys_from_start()` line 864 | **Can't find target** | **`offset * STEP_SIZE`** | **1000x slower** |
| **Invalid checksum** | **v1.5** | `hash160_to_address_host()` | **Invalid addresses** | **Double SHA256 checksum** | **Display only** |

---

## Files Modified

1. **SearchK4_fast.cu** - Main CUDA implementation
   - `mod_mul()` - Fixed reduction algorithm
   - `init_keys_from_start()` - Fixed memory layout and thread stride
   - `reconstruct_privkey()` - Fixed Y parity handling
   - `sha256_host()` - NEW: Host-side SHA256 implementation
   - `hash160_to_address_host()` - Fixed to use proper checksum
   - `privkey_to_wif()` - Fixed to use proper checksum

2. **CPUGroup.h** - Precomputed generator point table (512 entries)

3. **patterns.txt** - Search patterns including `1FeexV6bA`

---

## Current Configuration

- **GPUs**: 4x NVIDIA RTX 5090
- **Threads**: 65,536 per GPU
- **Keys per iteration**: 67,108,864 (65,536 × 1,024)
- **Speed**: ~1.9-2.0 GKey/s per GPU, ~7.6 GKey/s total
- **Patterns**: 7 prefixes (9-11 characters)
