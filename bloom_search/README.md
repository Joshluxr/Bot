# BloomSearch - GPU-Accelerated Bitcoin Address Matching

A high-performance system for matching GPU-generated Bitcoin addresses against a bloom filter containing 55+ million funded addresses.

## Overview

This system combines:
- **VanitySearch GPU kernel** - Fast elliptic curve point multiplication on CUDA GPUs
- **Bloom Filter** - Probabilistic data structure for O(1) address lookups
- **Checkpoint/Resume** - Crash-resilient operation with progress persistence

## Components

### Bloom Filter
- **File:** `btc_addresses.bloom` (191 MB)
- **Addresses:** 55,291,075 Bitcoin addresses
- **Size:** 1.6 billion bits
- **Hash Functions:** 20 (MurmurHash3)
- **False Positive Rate:** ~0% (tested with 1000 random hashes)

### Scripts

| Script | Description |
|--------|-------------|
| `build_bloom_fast.py` | Build bloom filter from address list |
| `bloom_verifier.py` | Verify addresses against bloom filter |
| `run_bloom_search.sh` | Run VanitySearch with bloom checking |
| `continuous_search.sh` | Crash-resilient continuous runner |
| `test_bloom.py` | Test bloom filter functionality |

## Quick Start

### 1. Build Bloom Filter (if needed)
```bash
# Download addresses (1.4GB compressed)
wget -O btc_addresses.txt.gz 'http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz'

# Build bloom filter (~5 minutes)
python3 build_bloom_fast.py
```

### 2. Test Bloom Filter
```bash
python3 test_bloom.py

# Or test specific address
echo 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa | python3 bloom_verifier.py btc_addresses.bloom
```

### 3. Run Continuous Search
```bash
./continuous_search.sh
```

## GPU Requirements

- CUDA-capable GPU(s)
- CUDA Toolkit 11.0+
- Recommended: RTX 4080/4090 for best performance

## Performance

On 4x RTX 4080 SUPER:
- Key generation: ~2 billion keys/second
- Bloom filter checks: Negligible overhead
- Memory usage: ~200MB per GPU for bloom filter

## File Structure

```
/workspace/bloom_search/
├── btc_addresses.bloom      # 191MB bloom filter
├── btc_addresses.txt.gz     # 1.4GB compressed address list
├── build_bloom_fast.py      # Bloom filter builder
├── bloom_verifier.py        # Address verifier
├── continuous_search.sh     # Crash-resilient runner
├── run_bloom_search.sh      # Basic runner
├── test_bloom.py            # Test script
├── checkpoint.json          # Search progress checkpoint
├── found_matches.txt        # Verified matches output
└── GPU/
    ├── GPUBloom.h           # CUDA bloom filter header
    └── GPUBloomCompute.h    # GPU compute integration
```

## Checkpointing

The system saves progress to `checkpoint.json` every 10 seconds:
```json
{
  keys_checked: 1234567890,
  bloom_matches: 0,
  start_time: 2024-01-17T22:00:00,
  last_update: 2024-01-17T23:00:00
}
```

On restart, it continues from the last checkpoint.

## Output

Matches are saved to `found_matches.txt` with format:
```
TIMESTAMP | ADDRESS | PRIVATE_KEY_WIF | PRIVATE_KEY_HEX
```

## License

MIT License - For educational and research purposes only.

## Disclaimer

This tool is for educational purposes. The probability of finding a funded address randomly is astronomically low (~1 in 2^160).
