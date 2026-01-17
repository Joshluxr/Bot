# BloomSearch - Bitcoin Address Collision Finder

A high-performance tool for finding Bitcoin addresses that exist in a known set of 55+ million addresses using bloom filters and deterministic work unit partitioning.

## Features

- **Bloom Filter Matching**: Instead of vanity prefix search, matches against a bloom filter of known addresses
- **Deterministic Checkpoint/Resume**: Never checks the same key twice, even after restart
- **Work Unit Partitioning**: Divides keyspace into independent work units for parallel/distributed search
- **GPU Acceleration**: CUDA-optimized for high throughput
- **Batch Processing**: Optimized for 23+ billion keys/second

## How It Works

### 1. Bloom Filter (0.00001% false positive rate)

Instead of checking each key against 55 million addresses one by one, we use a bloom filter:

```
55M addresses → 200 MB bloom filter → GPU checks in ~17 memory accesses per key
```

At 23 billion keys/second with 0.00001% FP rate = ~2.3 false positives/second (easily verified on CPU)

### 2. Deterministic Work Units

The 256-bit keyspace is divided into "work units" of 2^40 keys (~1.1 trillion):

```
Work Unit 0: key[0x0000...0000] to key[0x0000...FFFFFFFFFF]
Work Unit 1: key[seed_derived_1] to key[seed_derived_1 + 2^40]
...
```

Each work unit:
- Takes ~48 seconds at 23B keys/sec
- Has a unique ID
- Is marked complete in a bitmap file
- Can be assigned to different machines for distributed search

### 3. Checkpoint System

Progress is saved:
- Every 5 minutes automatically
- On Ctrl+C interrupt
- After each work unit completes

To resume, just run the same command - it will skip completed work units.

## Quick Start

### 1. Build the Bloom Filter (one-time, ~20 minutes)

```bash
cd bloom_search

# Download addresses and build bloom filter
python3 build_bloom_filter.py --download -o targets.bloom

# This creates:
#   - targets.bloom (200 MB) - bloom filter for GPU
#   - targets.sorted (1.1 GB) - sorted hash160s for CPU verification
```

### 2. Build BloomSearch

```bash
make
```

### 3. Run

```bash
./BloomSearch \
    -bloom targets.bloom \
    -sorted targets.sorted \
    -t 8 \
    -seed "my_unique_seed" \
    -o matches.txt
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-bloom <file>` | Bloom filter file (required) |
| `-sorted <file>` | Sorted hash160 file for verification (required) |
| `-checkpoint <file>` | Checkpoint file (default: checkpoint.dat) |
| `-o <file>` | Output file for matches |
| `-t <threads>` | Number of CPU threads (default: 4) |
| `-seed <string>` | Seed for deterministic work unit generation |
| `-compressed` | Search compressed keys only |
| `-uncompressed` | Search uncompressed keys only |
| `-gpu` | Enable GPU acceleration |
| `-gpuId <ids>` | GPU IDs to use (comma separated) |

## Distributed Search

Use different seeds on different machines to search different parts of the keyspace:

```bash
# Machine 1
./BloomSearch -bloom targets.bloom -sorted targets.sorted -seed "machine1" -o found1.txt

# Machine 2
./BloomSearch -bloom targets.bloom -sorted targets.sorted -seed "machine2" -o found2.txt

# Machine 3
./BloomSearch -bloom targets.bloom -sorted targets.sorted -seed "machine3" -o found3.txt
```

Each machine will search a completely different part of the keyspace.

## Performance

| Configuration | Keys/Second |
|--------------|-------------|
| 8 CPU threads | ~1-2 million |
| RTX 4080 SUPER (x1) | ~5-6 billion |
| RTX 4080 SUPER (x4) | ~22-23 billion |

At 23 billion keys/second:
- Work unit (2^40 keys) = 48 seconds
- One day = ~2 × 10^15 keys checked
- Full 256-bit keyspace = 10^62 years (obviously impossible!)

This is for research/educational purposes - finding real collisions is astronomically unlikely.

## File Formats

### Bloom Filter (.bloom)

```
Header (256 bytes):
  - uint64 numBits
  - uint64 numBytes
  - uint32 numHashes
  - uint32 itemCount
  - uint32[24] seeds
  - padding

Data:
  - raw bit array
```

### Checkpoint (.dat)

```
Header (256 bytes):
  - uint32 version
  - uint32 flags
  - uint64 totalWorkUnits
  - uint64 completedWorkUnits
  - uint64 totalKeysChecked
  - uint64 currentWorkUnitId
  - uint64 keysInCurrentUnit
  - uint8[32] seedHash
  - uint64 createdTimestamp
  - uint64 lastUpdateTimestamp
```

### Completed Bitmap (.completed)

Binary bitmap where bit N = 1 if work unit N is completed.

## Building the Bloom Filter Manually

```python
from build_bloom_filter import BloomFilter, address_to_hash160

# Create filter for custom address list
bf = BloomFilter(num_bits=1_600_000_000, num_hashes=20)

with open('my_addresses.txt') as f:
    for addr in f:
        h160 = address_to_hash160(addr.strip())
        if h160:
            bf.add(h160)

bf.save('my_targets.bloom')
```

## Technical Details

### Why Bloom Filters?

Checking 55M addresses naively:
- Binary search: O(log n) = 26 comparisons per key
- Hash table: O(1) but needs 1.1 GB in GPU memory

Bloom filter:
- 200 MB fits easily in GPU global memory
- 17 memory accesses per check
- False positives verified on CPU (only ~2/second)

### Why Work Units?

Random key generation has a problem:
- Birthday paradox means you'll check some keys twice
- No way to resume without regenerating everything

Work units solve this:
- Deterministic: same seed always produces same sequence
- Non-overlapping: each work unit covers unique keys
- Resumable: just skip completed work units
- Parallelizable: assign different work units to different machines

### Memory Usage

| Component | Size |
|-----------|------|
| Bloom filter (GPU) | 200 MB |
| Sorted hash160s (CPU) | 1.1 GB |
| Completed bitmap | Variable (~8 KB per 1M work units) |

## License

MIT License - Use at your own risk.

## Disclaimer

This tool is for educational and research purposes only. The probability of finding a collision with a funded Bitcoin address is astronomically low (roughly 1 in 2^160). This is computationally infeasible even with unlimited resources.
