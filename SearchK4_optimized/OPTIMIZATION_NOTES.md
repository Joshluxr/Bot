# SearchK4 Optimization: Uncompressed-Only Build with Bloom Filter

## Date: April 24-25, 2026

## Summary

SearchK4 was optimized for Bitcoin Puzzle #71 key searching on 8x RTX 5080 GPUs. The changes focus on removing unnecessary compressed address computation and adding a bloom filter for faster hash160 target lookups.

**Result: 0.53 GKey/s → 0.92 GKey/s per GPU (+74% throughput)**

---

## Server Environment

- **Server:** 74.48.78.46:40271 (SSH, root user, vast.ai instance)
- **GPUs:** 8x NVIDIA RTX 5080 (SM 12.0, 16 GB VRAM each)
- **CUDA:** Compute capability 120 (Blackwell)
- **Working directories:**
  - Original code: `/root/searchk4_hybrid/SearchK4_merged/`
  - Optimized code: `/root/searchk4_hybrid/SearchK4_optimized/`
  - Run data: `/root/searchk4_hybrid/SearchK4_merged/runs/puzzle71/`

---

## What Was Changed

### 1. Removed Compressed Address Checking from Direct Mode

**File:** `SearchK4_fast.cu`, lines 968-983

**Before:** In `-direct` mode, the kernel computed hash160 for both compressed AND uncompressed public keys for every candidate private key. This involved:
- `_GetHash160CompSym(px, h1, h2)` — computes SHA-256 → RIPEMD-160 on the 33-byte compressed pubkey (02/03 || x) for both Y and -Y parities
- `_GetHash160(px, py, h_uncomp1)` — computes SHA-256 → RIPEMD-160 on the 65-byte uncompressed pubkey (04 || x || y) for Y
- `_GetHash160(px, negY, h_uncomp2)` — same for -Y

That's **4 full double-hash computations** (SHA-256 + RIPEMD-160) per candidate key.

**After:** In `-direct` mode, the kernel ONLY computes uncompressed hashes:
- `_GetHash160(px, py, h_uncomp1)` — uncompressed hash for Y parity
- `_GetHash160(px, negY, h_uncomp2)` — uncompressed hash for -Y parity

That's **2 double-hash computations** per candidate key — a 50% reduction in the hot path.

The compressed hash (`_GetHash160CompSym`) is only computed in legacy prefix-match mode (non-direct), which is not used for Puzzle #71.

**Code change:**
```cuda
if (d_direct_mode) {
    // Hash160-direct mode: uncompressed only (Y and -Y).
    // Computes hash160 of the full 65-byte uncompressed pubkey (04||x||y).
    // Skips compressed hash entirely — saves one _GetHash160CompSym call.
    uint32_t h_uncomp1[5], h_uncomp2[5];
    _GetHash160(px, py, (uint8_t*)h_uncomp1);
    matched_idx = _MatchHash160(h_uncomp1);
    if (matched_idx >= 0) OutputMatchK4(out, tid, incr, h_uncomp1, matched_idx, 2);

    uint64_t negY[4];
    ModNeg256(negY, py);
    _GetHash160(px, negY, (uint8_t*)h_uncomp2);
    matched_idx = _MatchHash160(h_uncomp2);
    if (matched_idx >= 0) OutputMatchK4(out, tid, -incr, h_uncomp2, matched_idx, 3);
    return;  // Skip all compressed/legacy paths
}
```

The `return` statement at line 982 ensures the compressed hash computation (`_GetHash160CompSym`) at line 987 is never reached in direct mode.

### 2. Added Bloom Filter for Fast Pre-Screening

**File:** `SearchK4_fast.cu`

**Problem:** Binary search over 3,385+ sorted hash160 targets requires up to 12 comparison iterations, each reading 20 bytes from global memory. At ~400 cycles per global memory access, this is expensive — and 99.99%+ of candidates will NOT match any target.

**Solution:** A bloom filter (probabilistic set membership test) rejects non-matches with just 3 bit lookups before falling through to the binary search.

#### Bloom Filter Parameters (lines 50-54)
```c
#define BLOOM_SIZE_BITS  (512 * 1024)  // 512Kbit = 64KB
#define BLOOM_SIZE_U32   (BLOOM_SIZE_BITS / 32)
#define BLOOM_NUM_HASHES 3
```

- **Size:** 512 Kbit (64 KB) in GPU global memory
- **Hash functions:** 3 independent hash functions using Knuth/FNV-style multiplicative hashing
- **False positive rate:** < 0.01% for up to 4,096 targets (far below the theoretical Bk = k * ln(2) optimum)
- **False negative rate:** 0% (guaranteed by construction — all target bits are set during upload)

#### Device Storage (lines 75-76)
```c
__device__ uint32_t d_bloom_filter[BLOOM_SIZE_U32];
```
Stored in global memory (64 KB is too large for constant memory's 64 KB limit shared with other data).

#### Bloom Probe Function (lines 912-926)
```c
__device__ __forceinline__ bool _BloomCheck(const uint32_t *h) {
    uint32_t h1 = h[0] ^ (h[1] * 2654435761u);  // Knuth multiplicative hash
    uint32_t bit1 = h1 % BLOOM_SIZE_BITS;
    if (!(d_bloom_filter[bit1 >> 5] & (1u << (bit1 & 31)))) return false;

    uint32_t h2 = h[2] ^ (h[3] * 2246822519u);
    uint32_t bit2 = h2 % BLOOM_SIZE_BITS;
    if (!(d_bloom_filter[bit2 >> 5] & (1u << (bit2 & 31)))) return false;

    uint32_t h3 = h[4] ^ (h[0] * 3266489917u);
    uint32_t bit3 = h3 % BLOOM_SIZE_BITS;
    if (!(d_bloom_filter[bit3 >> 5] & (1u << (bit3 & 31)))) return false;

    return true;
}
```

Each hash function uses a different pair of the 5 uint32 words from the hash160, mixed with a different Knuth constant. Short-circuit evaluation means most non-matches exit after just 1 bit lookup.

#### Bloom-Filtered Binary Search (lines 929-939)
```c
__device__ __forceinline__ int _MatchHash160(const uint32_t *h) {
    if (!_BloomCheck(h)) return -1;   // Fast reject: ~99.99% of calls exit here
    int lo = 0, hi = d_num_targets - 1;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        int c = _CmpH160(h, d_target_h160[mid]);
        if (c == 0) return mid;
        if (c < 0) hi = mid - 1; else lo = mid + 1;
    }
    return -1;
}
```

#### Host-Side Bloom Construction (host code, during target upload)
```c
static uint32_t h_bloom[BLOOM_SIZE_U32];
memset(h_bloom, 0, sizeof(h_bloom));
for (int i = 0; i < numTargets; i++) {
    uint32_t hv1 = h_targets[i][0] ^ (h_targets[i][1] * 2654435761u);
    uint32_t bit1 = hv1 % BLOOM_SIZE_BITS;
    h_bloom[bit1 >> 5] |= (1u << (bit1 & 31));
    // ... same for hv2 and hv3 with same constants as device
}
cudaMemcpy(d_ptr_bloom, h_bloom, sizeof(h_bloom), cudaMemcpyHostToDevice);
```

The host uses identical hash functions to the device, ensuring consistency. After upload, the fill rate is logged (e.g., "bloom filter uploaded (987/524288 bits set, 0.19% fill)").

### 3. Reduced CUDA Stack Size

**Before:** 36 KB per thread (needed ~33 KB for combined compressed + uncompressed paths)
**After:** 16 KB per thread

Removing the compressed code path eliminated large stack-allocated buffers from `_GetHash160CompSym`. The NVCC compiler reported actual kernel stack frame of **1104 bytes**, well within the 16 KB limit.

Lower stack per thread means the GPU can schedule more concurrent thread blocks (higher occupancy), improving throughput.

### 4. Host-Side Target Upload (Uncompressed Only)

The host-side target upload function was modified to decode Bitcoin addresses to hash160 values and upload them as uncompressed targets only. The `d_target_h160` array stores raw 20-byte hash160 values extracted from the target addresses via Base58Check decoding.

Parity encoding in match output:
- `parity=2` — uncompressed, Y coordinate (positive)
- `parity=3` — uncompressed, -Y coordinate (negated)

WIF encoding for found keys uses uncompressed format (starts with `5`).

---

## How It Was Built

### Build Command
```bash
cd /root/searchk4_hybrid/SearchK4_optimized
make clean && make searchk4_fast
```

### Build Output
The Makefile auto-detects GPU compute capability via `nvidia-smi`. For RTX 5080:
```
Building searchk4_fast for compute capability 120...
nvcc -O3 -std=c++14 -gencode=arch=compute_120,code=sm_120 \
     --ptxas-options=-v -maxrregcount=96 -I. -lineinfo \
     -o searchk4_fast SearchK4_fast.cu ripemd160.o -lcuda
```

Key compiler output: `Stack frame for kernel: 1104 bytes` (down from ~33KB previously).

---

## How It Was Tested

### Smoke Test 1: Compressed Address (Negative Test)
```bash
echo "1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH" > _test.txt
./searchk4_fast -patterns _test.txt -direct -bits 1 -threads 64 -o _found.txt
```
This is the **compressed** address for key=1. The uncompressed-only kernel correctly returned NO match.

### Smoke Test 2: Uncompressed Address (Positive Test)
The uncompressed address for key=1 is `1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm`.

Computed via:
```python
# secp256k1 generator point G (private key = 1)
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
pubkey = b'\x04' + Gx.to_bytes(32,'big') + Gy.to_bytes(32,'big')  # 65-byte uncompressed
hash160 = RIPEMD160(SHA256(pubkey))
address = Base58Check(0x00, hash160)
# Result: 1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm
```

```bash
echo "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm" > _test.txt
./searchk4_fast -patterns _test.txt -direct -bits 1 -threads 64 -o _found.txt
```

**Result:** Found match with:
- PrivKey: `0x...0001`
- WIF: `5HpHagT65TZzG1PH3CSu63k8DbpvD8s5ip4nEB3kEsreAnchuDf` (uncompressed WIF, starts with `5`)
- VerifiedAddress: `1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm`
- Parity: 2 (uncompressed Y) and 3 (uncompressed -Y)

### Production Validation: 8 Known Keys
Ran 8 GPU searches with known private keys and their uncompressed addresses. All 7 valid ranges found their keys correctly with verified output. Results:

| GPU | Address | WIF | Status |
|-----|---------|-----|--------|
| 0 | 115p8Gat4VwL1FuYGeYdrzZtzHsFajRsNw | 5KBVNusnnAyijeJu76GSYUDbfmRruXGhJmoG317gcrAygBJVrNn | Found, verified |
| 1 | 1F9AkynMNVQKUMBJS9H2pNUMHNssYJySX | 5KLEa4gAbbkYJoDfV919Lkh8ZFMNKrvCj7m5RZDt9iQwSc7tNDz | Found, verified |
| 2 | 1HZKjpAYdaiXvCV3b6mXExrhPd3djzDWM | 5JQskA7hBDRNtRiPEwfjWHMLt6naobixZXPBGnESGFz8hp3F9SB | Found, verified |
| 3 | 1K2rGvYh58r5kuTK6pSsizkN8uwhBFy7w | 5JMSj82vfRcevR1Z6KrHr3gGhRsJa2Mh8dVHQsM2WTtQ2apnP14 | Found, verified |
| 4 | 1PKGkvrFD2jheJZzEQb7C5dMBPqxRi5gz | 5JA9qKY6exzmuh5ELCZXTphFpycsUDYfHt4zytZBG4yJD1iE3Cz | Found, verified |
| 5 | 1UorHJPfKUUz21nbdycn2DDr4FtCRnzhM | — | Skipped (range was inverted) |
| 6 | 1mxUZmGj54cFwx2P7sQdmx1YfLJAQpS5Y | 5JkaXuhTZddPf3xFeGgP9gTdwABxkW62N19t2NPthb6BX5gPjWs | Found, verified |
| 7 | 1oCnANTGNN1iGVtxJTqcm8em2neq9LjCU | 5JoqgQMKeooxcs4xDtKx39Hht9ThLNb6Q3eZaYEhE7NLXJqFhyr | Found, verified |

---

## How It Was Deployed

### Deployment Script (`/root/deploy_optimized.sh`)
The deployment follows a safe sequence:

1. **SIGTERM all running searchk4_fast processes** — the program catches SIGTERM and writes state files (`gpu<id>.state`) before exiting cleanly
2. **Wait for clean exit** (up to 30 seconds per process)
3. **Backup old binary** to `searchk4_fast.bak.<timestamp>`
4. **Copy new binary** from optimized build directory
5. **Restart all 8 GPUs** with their original ranges and state files

### Launch Command Per GPU
```bash
nohup ./searchk4_fast -direct -patterns patterns71.txt \
    -gpu <GPU_ID> \
    -startx <HEX_START> -endx <HEX_END> \
    -o gpu<ID>_found.txt \
    > logs/gpu<ID>.log 2>&1 &
```

### Key Flags
- `-direct` — hash160-direct mode (skip Base58 in kernel, raw 20-byte comparison)
- `-patterns <file>` — target addresses file (one address per line)
- `-gpu <N>` — bind to specific GPU device
- `-startx <hex>` / `-endx <hex>` — 256-bit hex range boundaries
- `-o <file>` — output file for verified matches

### State Resume
SearchK4 saves state every 500 iterations to `gpu<id>.state` (v2 format with FNV-1a checksums). On restart, if a state file exists matching the GPU ID, it automatically resumes from the saved iteration count. Use `-state <file>` to force a specific state file.

---

## Performance Numbers

| Metric | Before (Original) | After (Optimized) | Improvement |
|--------|-------------------|-------------------|-------------|
| Per-GPU throughput | 0.53 GKey/s | 0.92 GKey/s | +74% |
| Total (8 GPUs) | ~4.2 GKey/s | ~7.4 GKey/s | +74% |
| Kernel stack frame | ~33,000 bytes | 1,104 bytes | -97% |
| Hash computations per key | 4 (2 compressed + 2 uncompressed) | 2 (uncompressed only) | -50% |
| Target lookup (non-match) | 12 binary search iterations | 1-3 bloom filter bit checks | ~4x fewer memory accesses |

---

## File Listing

| File | Description |
|------|-------------|
| `SearchK4_fast.cu` | Main CUDA source — optimized uncompressed-only kernel with bloom filter |
| `SearchK4.cu` | Legacy/reference implementation (unmodified) |
| `GPUGroup.h` | GPU-side EC group operations (Jacobian coordinates, Montgomery batch inversion) |
| `GPUMath.h` | GPU-side 256-bit modular arithmetic |
| `GPUHash.h` | GPU-side SHA-256 and RIPEMD-160 implementations |
| `CPUGroup.h` | Host-side EC operations for key initialization |
| `ripemd160.c` / `.h` | Host-side RIPEMD-160 for post-match verification |
| `Makefile` | Build system with auto-detect compute capability, smoke test targets |
| `LICENSE` | GPLv3 (inherited from VanitySearch) |
| `README.md` | Original project readme |
| `MERGE_NOTES.md` | Notes from merging VanitySearch + BloomSearch32K3 codebases |
| `PATCH_NOTES_2026-04-19.md` | Previous patch notes |

---

## Architecture Overview

### Kernel Hot Path (Direct Mode)
```
For each thread (tid):
  1. Load EC point (px, py) for this thread's current key
  2. For each of STEP_SIZE/2 group additions:
     a. Compute next EC point via Jacobian addition + Montgomery batch inversion
     b. _GetHash160(px, py) → SHA-256 → RIPEMD-160 → 20-byte hash (uncompressed, Y)
     c. _BloomCheck(hash) → 3 bit lookups in 64KB bloom filter
        - If ALL 3 bits set: _MatchHash160() → binary search (12 iterations max)
        - If ANY bit clear: reject immediately (99.99% of calls)
     d. ModNeg256(py) → negated Y
     e. _GetHash160(px, negY) → hash of uncompressed -Y
     f. _BloomCheck + _MatchHash160 again
  3. Advance point by sequential delta (nbThread * STEP_SIZE)
```

### Match Verification (Host Side)
When the kernel reports a match:
1. Reconstruct full 256-bit private key from thread ID, increment, and iteration count
2. Perform independent EC scalar multiplication on host
3. Compute SHA-256 → RIPEMD-160 of the uncompressed public key using the host-side ripemd160.c
4. Compare against target hash160
5. If match: output as "verified"; if mismatch: output as "UNVERIFIED" (safety net)
6. Encode private key as WIF (uncompressed format, prefix `5`)

### Sequential Scanning
Each GPU scans a non-overlapping range of the 256-bit key space:
- Thread `tid` in iteration `iter` checks key: `base + iter * nbThread * STEP_SIZE + tid * STEP_SIZE + offset`
- STEP_SIZE = 1024 keys per thread per iteration
- Default threads: 16,384 (direct mode)
- Keys per iteration per GPU: 16,384 × 1,024 = 16,777,216

### State Persistence
- Format: v2 binary with FNV-1a checksums
- Saved every 500 iterations (configurable)
- Contains: iteration count, base key, GPU ID, range boundaries
- On SIGTERM: immediate state save before clean exit
