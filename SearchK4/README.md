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

Keys are stored in VanitySearch memory layout for compatibility:
```
Block b, Thread t:
  X coordinate: h_keys[b * 512 * 8 + t * 4 + 0..3]
  Y coordinate: h_keys[b * 512 * 8 + t * 4 + 4*512 + 0..3]
```

## Credits

- Based on [VanitySearch](https://github.com/JeanLucPons/VanitySearch) by Jean Luc PONS
- Jacobian coordinate formulas from [hyperelliptic.org](https://hyperelliptic.org/EFD/g1p/auto-shortw-jacobian-0.html)
- Montgomery batch inversion technique

## License

GNU General Public License v3.0
