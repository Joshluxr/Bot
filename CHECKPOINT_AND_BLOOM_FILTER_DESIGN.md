# VanitySearch: Checkpoint/Resume & Bloom Filter Matching

## Overview

This document outlines the implementation of two features:
1. **Checkpoint/Resume System** - Save and restore search progress
2. **Bloom Filter Matching** - Match generated keys against a large set of target public keys

---

## Part 1: Checkpoint/Resume System

### The Problem

VanitySearch currently has **no checkpoint system**. When the process stops:
- All progress is lost
- Same keys will be regenerated on restart
- For hard prefixes that take days/weeks, this is unacceptable

### How VanitySearch Generates Keys

Understanding the key generation is critical for designing checkpoints:

```
CPU Thread i: startKey + (i << 64) + offset
GPU Thread i: startKey + (i << 80) + (gpuId << 112) + offset
```

Each thread starts at a unique position in the 256-bit keyspace and increments by `GRP_SIZE` (1024) each iteration.

**Key insight:** The state of each thread is fully determined by:
1. The `startKey` (seed-derived)
2. Thread ID
3. Number of iterations completed (or current key position)

### Checkpoint Data Structure

```cpp
struct CheckpointData {
    // Version & Metadata
    uint32_t version;
    uint64_t timestamp;
    uint64_t totalKeysChecked;

    // Original Configuration (to verify resume compatibility)
    char seed[65];          // Original seed or "random"
    bool compressed;
    bool p2sh;
    uint32_t searchMode;

    // The crucial state: starting point for each thread
    // For deterministic mode: just need startKey + iterations count
    Int startKey;
    uint64_t iterationsCompleted;  // Global counter

    // For random/rekey mode: need each thread's current key
    bool isRandomMode;
    vector<Int> threadKeys;  // Only if random mode

    // Keyspace mode (BitCrack-style)
    bool hasKeyspace;
    Int ksStart;
    Int ksNext;
    Int ksEnd;
};
```

### Save Triggers

1. **Periodic saves** - Every N minutes (configurable, default: 5 min)
2. **On SIGINT/SIGTERM** - Graceful shutdown handler
3. **After each rekey** - When using `-r` flag
4. **On match found** - Save immediately after finding a key

### Implementation Changes

#### 1. Add checkpoint file handling to `Vanity.cpp`

```cpp
// New methods to add to VanitySearch class
void SaveCheckpoint(const string& filename);
bool LoadCheckpoint(const string& filename);
uint64_t GetIterationsCompleted();

// Checkpoint file format: Binary for speed, JSON header for readability
// File: checkpoint.dat
// [JSON Header: 4KB] [Binary State Data]
```

#### 2. Modify `getCPUStartingKey()` and `getGPUStartingKeys()`

```cpp
void VanitySearch::getCPUStartingKey(int thId, Int& key, Point& startP) {
    if (resumeFromCheckpoint && !isRandomMode) {
        // Calculate position based on saved iteration count
        key.Set(&startKey);
        Int off((int64_t)thId);
        off.ShiftL(64);
        key.Add(&off);

        // Add iterations already completed
        Int iterOffset;
        iterOffset.SetInt64(checkpointData.iterationsCompleted * CPU_GRP_SIZE);
        key.Add(&iterOffset);
    } else {
        // Original logic
    }
}
```

#### 3. Add SIGINT handler

```cpp
#include <signal.h>

volatile bool saveCheckpointRequested = false;

void signalHandler(int signum) {
    printf("\nInterrupt received, saving checkpoint...\n");
    saveCheckpointRequested = true;
    endOfSearch = true;
}

// In main():
signal(SIGINT, signalHandler);
signal(SIGTERM, signalHandler);
```

#### 4. Checkpoint file format (JSON header + binary data)

```json
{
    "version": "1.0",
    "program": "VanitySearch",
    "timestamp": "2024-01-15T12:34:56Z",
    "totalKeysChecked": 1234567890123,
    "keysPerSecond": 22600000000,
    "estimatedProgress": "0.0001%",
    "config": {
        "seed": "hex_or_random",
        "compressed": true,
        "searchMode": "P2PKH",
        "prefixes": ["1GUNPhjykrBdET"]
    },
    "state": {
        "startKey": "0x...",
        "iterationsCompleted": 12345678,
        "keyspaceMode": false
    }
}
```

### Command Line Interface

```bash
# Save checkpoint every 5 minutes (default)
./VanitySearch -gpu -o found.txt --checkpoint checkpoint.dat 1GUNPh

# Custom checkpoint interval (in seconds)
./VanitySearch -gpu --checkpoint checkpoint.dat --checkpoint-interval 60 1GUNPh

# Resume from checkpoint
./VanitySearch -gpu --resume checkpoint.dat

# Resume with verification (checks config matches)
./VanitySearch -gpu --resume checkpoint.dat --verify-config
```

---

## Part 2: Bloom Filter Matching for 55M Public Keys

### The Problem

Instead of matching a single vanity prefix, you want to check each generated key against a database of 55 million public keys/addresses.

### Bloom Filter Basics

A Bloom filter is a probabilistic data structure that can tell you:
- **Definitely NOT in set** (100% accurate)
- **Probably in set** (may have false positives)

For 55M keys with 0.0001% false positive rate:
- Size needed: ~165 MB (1.32 billion bits)
- Hash functions: ~17

### Design Considerations

#### Option A: GPU-Based Bloom Filter (Recommended)
- Load bloom filter into GPU global memory (~165 MB)
- Check each generated hash160 against bloom filter in CUDA kernel
- False positives verified on CPU
- **Speed impact: ~5-10% slower due to memory access**

#### Option B: CPU-Side Bloom Filter
- GPU generates keys, returns all hash160s to CPU
- CPU checks against bloom filter
- **Speed impact: ~50-70% slower due to data transfer**

### Implementation Plan

#### 1. Bloom Filter Data Structure (GPU-Compatible)

```cpp
// GPU/GPUBloomFilter.h
#define BLOOM_BITS 1320000000ULL  // ~165 MB for 55M keys, 0.0001% FP
#define BLOOM_BYTES (BLOOM_BITS / 8)
#define BLOOM_K 17  // Number of hash functions

__device__ __constant__ uint32_t bloomSeeds[BLOOM_K];

class GPUBloomFilter {
public:
    uint8_t* d_filter;      // GPU memory
    uint64_t numBits;
    int numHashes;

    void LoadFromFile(const char* filename);
    void CopyToGPU();
};

// MurmurHash3 for bloom filter (GPU version)
__device__ uint32_t murmur3_32(const uint8_t* key, int len, uint32_t seed);

__device__ bool BloomCheck(const uint8_t* hash160, const uint8_t* filter) {
    for (int i = 0; i < BLOOM_K; i++) {
        uint32_t h = murmur3_32(hash160, 20, bloomSeeds[i]);
        uint64_t bitPos = h % BLOOM_BITS;
        uint64_t bytePos = bitPos / 8;
        uint8_t bitMask = 1 << (bitPos % 8);
        if (!(filter[bytePos] & bitMask)) {
            return false;  // Definitely not in set
        }
    }
    return true;  // Probably in set (verify on CPU)
}
```

#### 2. Modified GPU Kernel

```cpp
// In GPUCompute.h
__device__ __noinline__ void CheckPointBloom(
    uint32_t *_h,
    int32_t incr,
    int32_t endo,
    int32_t mode,
    const uint8_t* bloomFilter,  // Bloom filter in global memory
    uint32_t maxFound,
    uint32_t *out
) {
    // Check bloom filter instead of prefix table
    if (BloomCheck((uint8_t*)_h, bloomFilter)) {
        // Potential match - send to CPU for verification
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            out[pos*ITEM_SIZE32 + 1] = tid;
            out[pos*ITEM_SIZE32 + 2] = (uint32_t)(incr << 16) | (uint32_t)(mode << 15) | (uint32_t)(endo);
            out[pos*ITEM_SIZE32 + 3] = _h[0];
            out[pos*ITEM_SIZE32 + 4] = _h[1];
            out[pos*ITEM_SIZE32 + 5] = _h[2];
            out[pos*ITEM_SIZE32 + 6] = _h[3];
            out[pos*ITEM_SIZE32 + 7] = _h[4];
        }
    }
}
```

#### 3. Building the Bloom Filter (Preprocessing Step)

```python
#!/usr/bin/env python3
"""
build_bloom_filter.py - Create bloom filter from public key file

Input formats supported:
  - One public key per line (hex compressed: 33 bytes, uncompressed: 65 bytes)
  - One address per line (Base58 Bitcoin addresses)
  - One hash160 per line (40 hex chars)
"""

import hashlib
import mmh3  # MurmurHash3
import struct
import sys
from typing import BinaryIO

# Configuration for 55M keys with 0.0001% FP rate
NUM_KEYS = 55_000_000
FALSE_POSITIVE_RATE = 0.000001  # 0.0001%

# Calculate optimal bloom filter parameters
import math
BLOOM_BITS = int(-NUM_KEYS * math.log(FALSE_POSITIVE_RATE) / (math.log(2) ** 2))
BLOOM_K = int((BLOOM_BITS / NUM_KEYS) * math.log(2))
BLOOM_BYTES = (BLOOM_BITS + 7) // 8

print(f"Bloom filter size: {BLOOM_BYTES / 1024 / 1024:.2f} MB")
print(f"Number of hash functions: {BLOOM_K}")
print(f"Expected false positive rate: {FALSE_POSITIVE_RATE * 100}%")

def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()

def ripemd160(data: bytes) -> bytes:
    h = hashlib.new('ripemd160')
    h.update(data)
    return h.digest()

def pubkey_to_hash160(pubkey_hex: str) -> bytes:
    """Convert public key to hash160"""
    pubkey = bytes.fromhex(pubkey_hex.strip())
    return ripemd160(sha256(pubkey))

def address_to_hash160(address: str) -> bytes:
    """Convert Base58 Bitcoin address to hash160"""
    import base58
    decoded = base58.b58decode_check(address)
    return decoded[1:]  # Skip version byte

class BloomFilter:
    def __init__(self, num_bits: int, num_hashes: int):
        self.num_bits = num_bits
        self.num_hashes = num_hashes
        self.num_bytes = (num_bits + 7) // 8
        self.bits = bytearray(self.num_bytes)
        self.seeds = list(range(num_hashes))  # Simple seeds 0, 1, 2, ...

    def add(self, data: bytes):
        for seed in self.seeds:
            h = mmh3.hash(data, seed, signed=False)
            bit_pos = h % self.num_bits
            byte_pos = bit_pos // 8
            bit_offset = bit_pos % 8
            self.bits[byte_pos] |= (1 << bit_offset)

    def contains(self, data: bytes) -> bool:
        for seed in self.seeds:
            h = mmh3.hash(data, seed, signed=False)
            bit_pos = h % self.num_bits
            byte_pos = bit_pos // 8
            bit_offset = bit_pos % 8
            if not (self.bits[byte_pos] & (1 << bit_offset)):
                return False
        return True

    def save(self, filename: str):
        with open(filename, 'wb') as f:
            # Header
            f.write(struct.pack('<Q', self.num_bits))
            f.write(struct.pack('<I', self.num_hashes))
            f.write(struct.pack('<I', len(self.seeds)))
            for seed in self.seeds:
                f.write(struct.pack('<I', seed))
            # Bloom filter data
            f.write(self.bits)

    @classmethod
    def load(cls, filename: str) -> 'BloomFilter':
        with open(filename, 'rb') as f:
            num_bits = struct.unpack('<Q', f.read(8))[0]
            num_hashes = struct.unpack('<I', f.read(4))[0]
            num_seeds = struct.unpack('<I', f.read(4))[0]
            seeds = [struct.unpack('<I', f.read(4))[0] for _ in range(num_seeds)]

            bf = cls(num_bits, num_hashes)
            bf.seeds = seeds
            bf.bits = bytearray(f.read())
            return bf

def build_bloom_filter(input_file: str, output_file: str, input_format: str = 'hash160'):
    bf = BloomFilter(BLOOM_BITS, BLOOM_K)

    count = 0
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if input_format == 'hash160':
                hash160 = bytes.fromhex(line)
            elif input_format == 'pubkey':
                hash160 = pubkey_to_hash160(line)
            elif input_format == 'address':
                hash160 = address_to_hash160(line)
            else:
                raise ValueError(f"Unknown format: {input_format}")

            bf.add(hash160)
            count += 1

            if count % 1_000_000 == 0:
                print(f"Processed {count:,} keys...")

    print(f"Total keys added: {count:,}")
    print(f"Saving bloom filter to {output_file}...")
    bf.save(output_file)
    print("Done!")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python build_bloom_filter.py <input_file> <output.bloom> [hash160|pubkey|address]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    input_format = sys.argv[3] if len(sys.argv) > 3 else 'hash160'

    build_bloom_filter(input_file, output_file, input_format)
```

#### 4. CPU-Side Verification

When GPU reports a bloom filter hit, CPU must verify:

```cpp
bool VanitySearch::VerifyBloomMatch(uint8_t* hash160) {
    // Binary search in sorted hash160 array
    // Or lookup in hash table
    return binarySearch(targetHash160s, numTargets, hash160) >= 0;
}
```

### Memory Considerations

| Component | Size |
|-----------|------|
| Bloom filter (GPU global mem) | ~165 MB |
| Hash160 verification table (CPU) | ~1.1 GB (55M × 20 bytes) |
| GPU constant memory limit | 64 KB |

**Important:** Bloom filter must go in GPU global memory, not constant memory (64 KB limit).

### Performance Impact

With bloom filter in GPU global memory:
- Each hash160 check: 17 memory accesses (one per hash function)
- Expected false positives per second: ~2,260 (at 22.6 Gkeys/s with 0.0001% FP rate)
- CPU can easily verify 2,260 candidates per second

**Estimated total slowdown: 5-15%**

---

## Part 3: Combined Command Line Interface

```bash
# Basic vanity search with checkpoint
./VanitySearch -gpu --checkpoint state.dat 1Bitcoin

# Resume from checkpoint
./VanitySearch -gpu --resume state.dat

# Bloom filter mode
./VanitySearch -gpu --bloom targets.bloom --checkpoint state.dat

# Build bloom filter first
python3 build_bloom_filter.py pubkeys_55m.txt targets.bloom pubkey

# Full command with all options
./VanitySearch -gpu -g 512,256 \
    --bloom targets.bloom \
    --checkpoint state.dat \
    --checkpoint-interval 300 \
    -o matches.txt
```

---

## Implementation Priority

### Phase 1: Checkpoint System (Easier)
1. Add checkpoint data structures
2. Implement save/load functions
3. Add SIGINT handler
4. Add command line arguments
5. Test with deterministic seed

### Phase 2: Bloom Filter Matching (More Complex)
1. Create bloom filter builder script (Python)
2. Implement GPU bloom filter check
3. Modify CUDA kernel to use bloom filter
4. Add CPU verification step
5. Integrate with checkpoint system

### Estimated Development Time
- Phase 1: ~200-300 lines of C++ changes
- Phase 2: ~400-500 lines of C++/CUDA changes + Python script

---

## Alternative: Quick & Dirty Checkpoint (Keyspace Mode)

If you don't want to modify the code extensively, you can use VanitySearch's existing keyspace mode:

```bash
# Start search from specific key range
./VanitySearch -gpu --keyspace 0000000000000000000000000000000000000000000000000000000000000001:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF 1GUNPh

# When you stop, note the last key processed
# Then resume from that key
./VanitySearch -gpu --keyspace <LAST_KEY>:FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF 1GUNPh
```

This requires manual tracking but works without code changes.

---

## Questions Before Implementation

1. **What format is your 55M public key file?**
   - Compressed public keys (33 bytes hex)?
   - Uncompressed public keys (65 bytes hex)?
   - Bitcoin addresses?
   - Hash160 values?

2. **What false positive rate is acceptable?**
   - 0.0001% = ~165 MB bloom filter
   - 0.00001% = ~200 MB bloom filter
   - 0.000001% = ~240 MB bloom filter

3. **Is checkpoint every 5 minutes acceptable, or do you need more frequent saves?**

4. **Do you want the bloom filter to check compressed keys only, uncompressed only, or both?**
   - Both = more hash160 computations per key
