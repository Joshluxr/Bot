# VanitySearch Bloom Filter Extension

GPU-accelerated Bitcoin address search using bloom filters for efficient matching against large address datasets.

## Overview

This extension allows VanitySearch to check generated keys against millions of Bitcoin addresses using a bloom filter, enabling efficient "puzzle" or "funded address" searching.

## Performance

| Configuration | Speed per GPU | Notes |
|---------------|---------------|-------|
| Original VanitySearch (prefix) | ~6 GKey/s | Single prefix matching |
| Bloom Filter (8 hashes) | ~2.3 GKey/s | 28M addresses |

The speed reduction is due to bloom filter memory access patterns (8 random reads per key vs 1 cached read for prefix matching).

## Files

- `bloom_v2.zip` - Pre-built bloom filter for 27.9M Bitcoin addresses
  - `bloom_v2.bloom` - 42MB bloom filter (335M bits)
  - `bloom_v2.prefix` - 8KB 16-bit prefix table
  - `bloom_v2.seeds` - 8 murmur3 hash seeds
  - `bloom_v2.info` - Metadata
- `build_bloom.py` - Python script to build bloom filter from address list
- `BloomSearch.cu` - Basic CUDA bloom search implementation
- `BloomSearchPrefix.cu` - Optimized version with prefix pre-filtering
- `GPUBloom.h` - GPU bloom filter header
- `GPUBloomPrefix.h` - GPU bloom filter with prefix table header

## Bloom Filter Specifications

| Parameter | Value |
|-----------|-------|
| Addresses | 27,924,862 (1... and 3... legacy addresses) |
| Hash functions | 8 (murmur3) |
| Bits | 335,098,344 |
| Size | 42MB |
| False positive rate | ~0.3% |
| Prefix table | 8KB (65,536 unique 16-bit prefixes) |

## Building

```bash
# Compile BloomSearchPrefix (recommended)
nvcc -O3 -arch=sm_89 -o BloomSearchPrefix BloomSearchPrefix.cu -I../

# Compile basic BloomSearch
nvcc -O3 -arch=sm_89 -o BloomSearch BloomSearch.cu -I../
```

Adjust `-arch=sm_XX` for your GPU:
- RTX 4090/4080: sm_89
- RTX 3090/3080: sm_86
- RTX 2080: sm_75

## Usage

```bash
# Extract bloom filter
unzip bloom_v2.zip

# Run on single GPU
./BloomSearchPrefix -bloom bloom_v2.bloom -seeds bloom_v2.seeds -prefix bloom_v2.prefix -bits 335098344 -hashes 8 -gpu 0

# Run on multiple GPUs (example: 8 GPUs)
for i in {0..7}; do
    ./BloomSearchPrefix -bloom bloom_v2.bloom -seeds bloom_v2.seeds -prefix bloom_v2.prefix -bits 335098344 -hashes 8 -gpu $i > gpu$i.log 2>&1 &
done
```

## Building Custom Bloom Filter

Download fresh address list and build:

```bash
# Download latest funded addresses
wget http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz
gunzip Bitcoin_addresses_LATEST.txt.gz

# Build bloom filter (processes 1... and 3... addresses only)
python3 build_bloom.py Bitcoin_addresses_LATEST.txt my_bloom

# Output files:
# my_bloom.bloom  - Main bloom filter
# my_bloom.prefix - 16-bit prefix table
# my_bloom.seeds  - Hash seeds
# my_bloom.info   - Metadata
```

## Algorithm

1. **Key Generation**: VanitySearch generates batches of EC public keys using group operations
2. **Hash Computation**: Each public key is hashed (SHA256 + RIPEMD160) to get hash160
3. **Prefix Check**: First 16 bits of hash160 checked against 8KB prefix table (L1 cached)
4. **Bloom Check**: If prefix exists, full bloom filter check with 8 murmur3 hashes
5. **Match Logging**: Potential matches (including false positives) logged to `matches.txt`

## Verifying Matches

Matches in `matches.txt` are hash160 values (hex). To verify:

1. Convert hash160 to Bitcoin address
2. Check if address exists in original address list
3. If real match, derive private key from the search parameters

Note: ~0.3% of matches are false positives due to bloom filter nature.

## Source

Address data from [Loyce Club](http://addresses.loyce.club/) Bitcoin address database.
