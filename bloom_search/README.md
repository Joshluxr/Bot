# GPU Bloom Filter Bitcoin Address Search

High-performance GPU-accelerated Bitcoin address search using bloom filters for efficient key space elimination.

## Features

- **Dual Address Format Support** - Searches BOTH compressed AND uncompressed addresses
- **Early Bitcoin Coverage** - Finds Satoshi-era addresses (2009-2012) using uncompressed pubkeys
- **Three-Tier Bloom Filter** - 32-bit prefix + primary bloom + optional secondary bloom
- **Endomorphism Optimization** - 6x address checks per EC point multiplication
- **Batch Modular Inversion** - Montgomery's trick for faster EC operations
- **Persistent Checkpoints** - Resume search after restart or server migration

## Performance

| Hardware | Speed (Compressed Only) | Speed (Both Formats) |
|----------|------------------------|---------------------|
| RTX 4080 SUPER (single) | ~3.2 GKey/s | ~3.2 GKey/s |
| 8x RTX 4080 SUPER | ~25 GKey/s | ~25 GKey/s |

- 32-bit prefix filter eliminates 99.35% of keys before bloom filter check
- 12 addresses checked per EC point (with `-both` mode)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Dual-Format Search Pipeline                       │
├─────────────────────────────────────────────────────────────────────┤
│  Private Key                                                         │
│       │                                                              │
│       ▼                                                              │
│  EC Point (x, y)                                                     │
│       │                                                              │
│       ├─► Compressed (02/03+x) ─► SHA256 ─► RIPEMD160 ─► hash160_c  │
│       │                                                      │       │
│       └─► Uncompressed (04+x+y) ─► SHA256 ─► RIPEMD160 ─► hash160_u │
│                                                              │       │
│                              ┌───────────────────────────────┘       │
│                              ▼                                       │
│                    Prefix Check (99.35% rejected)                    │
│                              │                                       │
│                              ▼                                       │
│                    Bloom Filter (~0.1% false positive)               │
│                              │                                       │
│                              ▼                                       │
│                    Candidate for Verification                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Why Dual Format Matters

Early Bitcoin (2009-2012) used **uncompressed public keys** (65 bytes), while modern wallets use **compressed keys** (33 bytes). The same private key produces **two different addresses**:

```
Private Key: abc123...
     │
     ├─► Compressed:   1ABC...  (modern wallets)
     │
     └─► Uncompressed: 1XYZ...  (Satoshi's coins!)
```

**Satoshi's ~1M BTC are ALL in uncompressed addresses.** Without dual-format search, you'd never find them.

## Key Files

### Source Code (`src/`)
- `BloomSearch32K1.cu` - Main GPU kernel with dual-format support
- `BloomSearch32Silent.cu` - Silent mode (no candidate logging)
- `BloomSearch32.cu` - Legacy compressed-only version

### Headers
- `GPUGroup.h` - EC point group operations
- `GPUMath.h` - Modular arithmetic (256-bit)
- `GPUHash.h` - SHA256/RIPEMD160 implementations

### Scripts (`scripts/`)
- `gpu_only_search.sh` - Main search launcher for 8 GPUs
- `checkpoint_manager.py` - Upload/download checkpoints to VPS

## Usage

### Command Line Options

```
BloomSearch32K1 - K1-Optimized GPU Search with Three-Tier Bloom Filter

Required:
  -prefix <file>   32-bit prefix bitmap file
  -bloom <file>    Primary bloom filter file
  -seeds <file>    Primary bloom seeds file
  -bits <n>        Primary bloom filter bits

Address Format (IMPORTANT for early Bitcoin!):
  -both            Search BOTH compressed AND uncompressed (DEFAULT)
                   -> Required to find Satoshi's coins & 2009-2012 addresses!
  -compressed      Search compressed only (modern wallets, post-2012)
  -uncompressed    Search uncompressed only (early Bitcoin 2009-2012)

Optional:
  -bloom2 <file>   Secondary bloom filter (tier 3)
  -seeds2 <file>   Secondary bloom seeds
  -bits2 <n>       Secondary bloom filter bits
  -gpu <id>        GPU device ID (default: 0)
  -state <file>    State checkpoint file
```

### Example

```bash
# Search BOTH formats (recommended)
./BloomSearch32K1 \
  -prefix /root/bloom_v3.prefix32 \
  -bloom /root/bloom_v3.bloom \
  -seeds /root/bloom_v3.seeds \
  -bits 334945032 \
  -both \
  -gpu 0 \
  -state state_gpu0.dat

# Compressed only (faster, misses early coins)
./BloomSearch32K1 \
  -prefix /root/bloom_v3.prefix32 \
  -bloom /root/bloom_v3.bloom \
  -seeds /root/bloom_v3.seeds \
  -bits 334945032 \
  -compressed \
  -gpu 0
```

### Multi-GPU Launch

```bash
for gpu in 0 1 2 3 4 5 6 7; do
  nohup ./BloomSearch32K1 \
    -prefix /root/bloom_v3.prefix32 \
    -bloom /root/bloom_v3.bloom \
    -seeds /root/bloom_v3.seeds \
    -bits 334945032 \
    -both \
    -gpu $gpu \
    -state state_gpu${gpu}.dat \
    > log_gpu${gpu}.log 2>&1 &
done
```

## Output Format

```
GPU 0: NVIDIA GeForce RTX 4080 SUPER (K1-Optimized)
Features: Batch ModInv + Cached Endomorphism + Tiered Bloom
Search Mode: BOTH (compressed + uncompressed)
  -> Will find early Bitcoin (2009-2012) AND modern addresses!

Starting K1-optimized search (12 addresses per EC point)...

[CANDIDATE COMP] tid=34175 meta=fe008001 hash160=4e6ccf34...
[CANDIDATE UNCOMP] tid=30430 meta=02000002 hash160=9a2bc65a...

[10073s] 32.57T keys | 3.23 GKey/s | 664193470 candidates
```

- `COMP` = Compressed address match
- `UNCOMP` = Uncompressed address match (early Bitcoin!)
- `candidates` = Bloom filter matches (mostly false positives)

## Checkpoint System

State saved every 500 iterations. Files contain:
- Total keys checked (8 bytes)
- EC point states for all threads (4MB per GPU)

```bash
# Sync checkpoints to VPS
python3 scripts/checkpoint_manager.py upload -s root@vps.com -g 0
python3 scripts/checkpoint_manager.py download -s root@vps.com -g 0
```

## Building

```bash
# Compile for RTX 4080/4090 (sm_89)
nvcc -O3 -arch=sm_89 -o BloomSearch32K1 src/BloomSearch32K1.cu -I.

# For RTX 3080/3090 (sm_86)
nvcc -O3 -arch=sm_86 -o BloomSearch32K1 src/BloomSearch32K1.cu -I.

# For RTX 5090 (sm_100)
nvcc -O3 -arch=sm_100 -o BloomSearch32K1 src/BloomSearch32K1.cu -I.
```

## Mathematical Reality

Finding a match is essentially impossible:

| Metric | Value |
|--------|-------|
| Funded addresses | ~55 million (2^26) |
| Possible addresses | 2^160 (1.46 x 10^48) |
| Search rate | 25 GKey/s |
| Keys checked per year | 7.9 x 10^17 |
| Years to find 1 match | ~10^30 years |
| Age of universe | 1.4 x 10^10 years |

This demonstrates Bitcoin's cryptographic security.

## Changelog

### v2.0 (2025-01-19)
- Added dual-format search (`-both` mode) for compressed + uncompressed
- Added `COMP`/`UNCOMP` labels to candidate output
- Increased addresses per EC point from 6 to 12
- Now finds Satoshi-era (2009-2012) addresses

### v1.0
- Initial release with compressed-only search
- Three-tier bloom filter
- Endomorphism optimization

## License

For research and educational purposes only.
