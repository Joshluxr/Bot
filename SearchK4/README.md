# SearchK4 - GPU Vanity Address Search with Fast Sequential Key Initialization

A high-performance GPU-accelerated Bitcoin vanity address search tool with optimized sequential keyspace searching.

## Features

- **Fast Sequential Key Initialization**: Initialize 65,536 keys in ~1 second (vs hanging indefinitely in original)
- GPU-accelerated Base58 address generation and pattern matching
- Sequential keyspace search from any starting point
- Support for both decimal and hex starting values
- State save/resume functionality
- Full private key reconstruction on match

## Performance

| Metric | Original | Optimized |
|--------|----------|-----------|
| Key init time | Hung indefinitely | **1-2 seconds** |
| Keys/sec (init) | ~0 | **65,000+** |

## Optimizations Implemented

### 1. Fixed Modular Multiplication (`mod_mul`)
The original implementation had a buggy reduction loop that caused infinite loops. The new version properly reduces using secp256k1's special form: `p = 2^256 - 0x1000003D1`.

### 2. Jacobian Coordinate Operations
Instead of affine coordinates (which require a modular inverse per operation), we use Jacobian coordinates:
- Point doubling: No division required
- Point addition: No division required  
- Only ONE `mod_inv` at the very end to convert back to affine

### 3. Montgomery Batch Inversion
For initializing N sequential keys, we reduce N modular inversions to just 1:
- Cost: 1 inversion + (3N-3) multiplications
- Speedup: ~500x for large N

### 4. Precomputed Generator Table (`CPUGroup.h`)
Pre-computed multiples of the generator point G:
- `Gx_cpu[i]` = (i+1)*G.x for i=0..511
- `Gy_cpu[i]` = (i+1)*G.y for i=0..511

This allows instant lookup for small multiples instead of expensive scalar multiplication.

## Files

- `SearchK4_fast.cu` - Main optimized implementation
- `SearchK4.cu` - Original version (for reference)
- `CPUGroup.h` - Precomputed G table (512 entries)
- `GPUGroup.h` - GPU-side precomputed tables (from VanitySearch)
- `GPUMath.h` - GPU math primitives (from VanitySearch)
- `GPUHash.h` - GPU hash functions (from VanitySearch)

## Building

```bash
# Compile optimized version
nvcc -O3 -arch=sm_89 -I../VanitySearch/GPU SearchK4_fast.cu -o SearchK4_fast

# For other GPU architectures, adjust -arch flag:
# RTX 4090: -arch=sm_89
# RTX 3090: -arch=sm_86
# RTX 2080: -arch=sm_75
```

## Usage

```bash
# Sequential search from decimal start point
./SearchK4_fast -patterns patterns.txt -start 12345678901234567890 -gpu 0

# Sequential search from hex start point
./SearchK4_fast -patterns patterns.txt -startx 0xAB54A98CEB1F0AD2 -gpu 0

# With state file for resume
./SearchK4_fast -patterns patterns.txt -start 12345678901234567890 -state state.bin -gpu 0
```

### Options

- `-patterns <file>` - File with vanity prefixes (one per line, required)
- `-gpu <id>` - GPU device ID (default: 0)
- `-start <value>` - Starting private key (decimal)
- `-startx <value>` - Starting private key (hex)
- `-state <file>` - State file for resume capability
- `-o <file>` - Output file (default: found_k4.txt)

## Technical Details

### Elliptic Curve Math

The secp256k1 curve uses the prime field:
```
p = 2^256 - 2^32 - 977 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
```

This special form allows fast modular reduction:
```
high * 2^256 mod p = high * 0x1000003D1 mod p
```

### Key Initialization Algorithm

1. Compute `P0 = baseKey * G` using Jacobian double-and-add (256 doublings, ~128 additions, 1 final inversion)
2. For keys 1 to N-1:
   - Look up `i*G` from precomputed table (or compute if i > 512)
   - Batch compute `dx[i] = (i*G).x - P0.x` for all i
   - Single batch inversion to get all `1/dx[i]`
   - Compute `P[i] = P0 + i*G` using precomputed inverses

### Memory Layout

Keys are stored in VanitySearch's **strided** memory layout for GPU coalesced access:
```
Block b, Thread t (within block):
  X[0]: h_keys[b * 512 * 8 + t]
  X[1]: h_keys[b * 512 * 8 + t + 512]
  X[2]: h_keys[b * 512 * 8 + t + 1024]
  X[3]: h_keys[b * 512 * 8 + t + 1536]
  Y[0]: h_keys[b * 512 * 8 + 2048 + t]
  Y[1]: h_keys[b * 512 * 8 + 2048 + t + 512]
  Y[2]: h_keys[b * 512 * 8 + 2048 + t + 1024]
  Y[3]: h_keys[b * 512 * 8 + 2048 + t + 1536]
```

This strided layout allows adjacent GPU threads to access adjacent memory locations,
maximizing memory bandwidth through coalesced reads.

## Changelog

### v1.3 (2025-01-29) - Private Key Y Parity Fix
**CRITICAL BUG FIX**: Fixed private key reconstruction for compressed public keys with odd Y coordinates.

**Problem**: When a match was found for an address starting with `03` (odd Y coordinate), the reconstructed private key produced a different address than what was matched.

**Root Cause**: Bitcoin compressed public keys encode the Y parity:
- `02` + X: Y is even
- `03` + X: Y is odd

When we initialize keys as `base_key + offset`, if the resulting point has odd Y, the GPU matches the `03` form. But if we just compute `base_key + offset` on reconstruction, we might get a point with even Y (depending on how the math works out). The fix is to check the Y parity and negate the private key if needed:

```cpp
// If matched compressed key starts with 03 (odd Y), we may need to negate
if (matched_compressed[0] == 0x03) {
    // Check if our reconstructed Y is even
    if ((y[0] & 1) == 0) {
        // Negate private key: new_key = curve_order - old_key
        key = CURVE_ORDER - key;
    }
}
```

**Impact**: All private keys found before this fix for `03`-prefix addresses need Y parity verification.

### v1.2 (2025-01-29) - Iteration Stride Fix
**BUG FIX**: Fixed key coverage overlap causing inefficient search.

**Problem**: Each iteration was only advancing by 1 key per thread instead of STEP_SIZE (1024), causing massive overlap:
- 65,536 threads × 1 = only 65,536 unique keys per iteration
- Should be: 65,536 threads × 1024 = 67,108,864 unique keys per iteration

**Root Cause**: The per-thread offset initialization used:
```cpp
// WRONG: All threads start with offset 1, massive overlap
offset[thread_id] = 1;
```

Should be:
```cpp
// CORRECT: Strided offsets, no overlap
offset[thread_id] = thread_id * STEP_SIZE;
```

**Fix Applied**:
1. Changed offset initialization to use strided pattern
2. Each thread now covers its own unique range of 1024 keys
3. Iteration advancement properly moves to next batch

**Impact**: Search was ~1000x slower than expected due to redundant key checking.

### v1.1 (2025-01-28) - Memory Layout Fix
**CRITICAL BUG FIX**: Fixed memory layout mismatch in `init_keys_from_start()`.

**Problem**: The fast key initialization was storing public keys in contiguous format, but the GPU kernel uses a strided memory layout (via `Load256A` macro). This caused:
- GPU reading wrong public keys
- Addresses found didn't match reconstructed private keys
- **All keys found before this fix are INVALID**

**Root Cause**: VanitySearch uses a strided memory layout for GPU coalesced access:
```
For thread t in block b:
  X[0..3] at indices: b*4096 + t, b*4096 + t+512, b*4096 + t+1024, b*4096 + t+1536
  Y[0..3] at indices: b*4096 + 2048+t, b*4096 + 2048+t+512, ...
```

The fast init was using contiguous layout:
```
For key i:
  X[0..3] at indices: i*8, i*8+1, i*8+2, i*8+3
  Y[0..3] at indices: i*8+4, i*8+5, i*8+6, i*8+7
```

**Fix Applied**: Converted `init_keys_from_start()` to use proper strided memory layout matching the GPU kernel's `Load256A`/`Load256` macros.

### v1.0 (2025-01-28) - Initial Fast Key Init
- 65,000x speedup in key initialization
- Montgomery batch inversion
- Jacobian coordinates
- Precomputed G table

**Problems solved in v1.0:**

1. **Buggy `mod_mul` function**: Original had an infinite loop in reduction when handling carries. Fixed by implementing proper secp256k1 reduction using the special form `p = 2^256 - 0x1000003D1`.

2. **Expensive per-key modular inversions**: Original code computed one `mod_inv` (~256 multiplications) for every key. Fixed by:
   - Using Jacobian coordinates (no division during EC operations)
   - Montgomery batch inversion (N inversions → 1 inversion + 3N multiplications)

## Current Search Configuration

### Active Patterns (as of 2025-01-29)
```
1FeexV6bA    (9 chars)  - Target address prefix
1A1zP1eP5Q   (10 chars) - Satoshi's genesis address prefix
1ARWCREnm    (9 chars)
1FvUkW8thc   (10 chars)
138EMxwMt    (9 chars)
1VeMPNgEtQ   (10 chars)
1NY5KheH3ko  (11 chars)
```

### GPU Allocation
Running on 4x NVIDIA RTX 5090 GPUs with non-overlapping keyspace ranges:
- **GPU 0**: Starting at `0xb53ec9e1eb29d0402eb35a46ef505ad012ce27c03d02ac9d6da6f42714482200`
- **GPU 1**: Starting at `0xfe1ef9e0309e12806a986cc9d2b9d35425a3d135494639a648e94a0c0a777e00`
- **GPU 2**: Starting at `0x412cc8256ff579da05f048cafb7e2b82b876bbfc67e82901ec73dea8c4f83400`
- **GPU 3**: Starting at `0xb77c205a702dec47dfdbaebbf2dd0850c6791bb5a48bb0ab8042f5817290d200`

### Performance Metrics
- **Per GPU**: ~1.65-1.68 GKey/s
- **Total (4 GPUs)**: ~6.7 GKey/s
- **Keys per iteration**: 67,108,864 (65,536 threads × 1,024 steps)

## Probability Analysis

For a k-character Base58 prefix, probability of match ≈ 1/58^(k-1):
| Prefix Length | Probability | Expected Keys to Check |
|---------------|-------------|------------------------|
| 6 chars       | 1/656,356   | ~656K |
| 7 chars       | 1/38M       | ~38M |
| 8 chars       | 1/2.2B      | ~2.2B |
| 9 chars       | 1/128B      | ~128B |
| 10 chars      | 1/7.4T      | ~7.4T |
| 11 chars      | 1/430T      | ~430T |

At 6.7 GKey/s:
- 9-char match: ~19 seconds average
- 10-char match: ~18 minutes average
- 11-char match: ~18 hours average

## Credits

- Based on [VanitySearch](https://github.com/JeanLucPons/VanitySearch) by Jean Luc PONS
- Jacobian coordinate formulas from [hyperelliptic.org](https://hyperelliptic.org/EFD/g1p/auto-shortw-jacobian-0.html)
- Montgomery batch inversion technique

## License

GNU General Public License v3.0
