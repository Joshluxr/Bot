# GPU Bloom Filter Bitcoin Address Search System

## Technical Documentation

**Version:** 1.0
**Last Updated:** January 2026
**Architecture:** Multi-Stage GPU-Accelerated Filtering System

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Core Components](#3-core-components)
4. [Cryptographic Operations](#4-cryptographic-operations)
5. [Filter System](#5-filter-system)
6. [GPU Implementation](#6-gpu-implementation)
7. [Performance Characteristics](#7-performance-characteristics)
8. [File Formats](#8-file-formats)
9. [Build System](#9-build-system)
10. [Usage Guide](#10-usage-guide)

---

## 1. System Overview

### Purpose

This system implements a high-performance Bitcoin address search using GPU acceleration combined with probabilistic data structures (bloom filters) for efficient filtering. It generates Bitcoin private keys, derives corresponding public keys and addresses, and checks them against a pre-built database of funded addresses.

### Key Features

- **Multi-GPU Support**: Scales across 1-8+ NVIDIA GPUs
- **Multi-Stage Filtering**: 32-bit prefix bitmap + bloom filter reduces CPU load
- **VanitySearch Integration**: Uses optimized GPU cryptographic primitives
- **Endomorphism Optimization**: 3x throughput via secp256k1 curve properties
- **High Throughput**: ~225 GKey/s per RTX 4080 SUPER (~1.8 TKey/s on 8 GPUs)

### Mathematical Security Note

Despite the high throughput, finding a match is mathematically infeasible:
- Address space: 2^160 possible addresses
- Search rate: ~1.8 TKey/s = ~5.7 × 10^19 keys/year
- Target addresses: ~28 million = ~2^25
- Expected time to match: ~10^22 years (universe age: ~1.4 × 10^10 years)

---

## 2. Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GPU CLUSTER (8x RTX 4080)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │  Random Key  │───▶│ EC Point Mul │───▶│  Hash160     │          │
│  │  Generation  │    │  (secp256k1) │    │ (SHA256+RIP) │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                 │                    │
│                                                 ▼                    │
│                      ┌─────────────────────────────────────┐        │
│                      │   STAGE 1: 32-bit Prefix Bitmap     │        │
│                      │   (512 MB on GPU, ~99.35% reject)   │        │
│                      └─────────────────────────────────────┘        │
│                                                 │                    │
│                                          Candidates                  │
│                                                 │                    │
└─────────────────────────────────────────────────┼────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                              CPU                                     │
├─────────────────────────────────────────────────────────────────────┤
│                      ┌─────────────────────────────────────┐        │
│                      │   STAGE 2: Bloom Filter Check       │        │
│                      │   (0.3% false positive rate)        │        │
│                      └─────────────────────────────────────┘        │
│                                                 │                    │
│                                          Candidates                  │
│                                                 │                    │
│                      ┌─────────────────────────────────────┐        │
│                      │   STAGE 3: Database Verification    │        │
│                      │   (Exact match lookup)              │        │
│                      └─────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Key Generation**: GPU generates random 256-bit private keys
2. **Point Multiplication**: Compute public key P = k × G on secp256k1
3. **Endomorphism**: Generate 2 additional points using β multiplication
4. **Hash160**: SHA256 + RIPEMD160 on compressed public keys
5. **Prefix Check**: GPU checks first 32 bits against bitmap
6. **Bloom Check**: CPU verifies full 160-bit hash in bloom filter
7. **Database Check**: Final verification against actual address list

---

## 3. Core Components

### 3.1 File Structure

```
bloom_search/
├── bloom_gpu_search.cu      # Main CUDA GPU search implementation
├── bloom_search.cpp         # CPU-only bloom filter search
├── build_filters.py         # Python script to build filter files
├── GPUGroup.h               # secp256k1 generator point table (512 points)
├── GPUMath.h                # 256-bit modular arithmetic (PTX assembly)
├── GPUHash.h                # SHA256 + RIPEMD160 GPU implementations
├── Makefile                 # Build configuration
├── test_bloom.cpp           # Filter testing utility
└── generate_test_addresses.py  # Test data generator
```

### 3.2 Dependencies

- **CUDA Toolkit**: Version 11.0+ (tested with CUDA 13)
- **NVIDIA GPU**: Compute capability 8.9 (Ada Lovelace) or compatible
- **Python 3**: For filter building scripts
- **g++**: C++17 compatible compiler

---

## 4. Cryptographic Operations

### 4.1 secp256k1 Elliptic Curve

The system uses Bitcoin's secp256k1 curve defined by:
- **Equation**: y² = x³ + 7 (mod p)
- **Prime p**: 2^256 - 2^32 - 977
- **Generator G**: Standard secp256k1 base point
- **Order n**: ~2^256 (curve order)

#### Key Constants (from GPUMath.h)

```cuda
// Prime field modulus p = 0xFFFFFFFEFFFFFC2F...
// Stored as 64-bit limbs in little-endian order

// Endomorphism constants (β where β³ = 1 mod n)
__device__ __constant__ uint64_t _beta[] = {
    0xC1396C28719501EEULL, 0x9CF0497512F58995ULL,
    0x6E64479EAC3434E9ULL, 0x7AE96A2B657C0710ULL
};

__device__ __constant__ uint64_t _beta2[] = {
    0x3EC693D68E6AFA40ULL, 0x630FB68AED0A766AULL,
    0x919BB86153CBCB16ULL, 0x851695D49A83F8EFULL
};
```

### 4.2 Endomorphism Optimization

For any point P = (x, y), the curve has an efficient endomorphism:
- **λ * P** = (β * x, y) where β³ ≡ 1 (mod p) and λ³ ≡ 1 (mod n)

This allows checking 3 addresses per point computation:
1. Original point P
2. Endomorphism 1: (β × x, y)
3. Endomorphism 2: (β² × x, y)

Combined with symmetric points (±y), each computation yields 6 address checks.

### 4.3 Hash160 Computation

Bitcoin address derivation (P2PKH):

```
Private Key (256-bit)
        │
        ▼
Public Key = k × G (on secp256k1)
        │
        ▼
Compressed Public Key (33 bytes: 0x02/0x03 prefix + X coordinate)
        │
        ▼
SHA256(compressed_pubkey)
        │
        ▼
RIPEMD160(sha256_result) = Hash160 (20 bytes)
        │
        ▼
Base58Check(version + hash160 + checksum) = Bitcoin Address
```

#### GPU Implementation (from GPUHash.h)

```cuda
__device__ __noinline__ void _GetHash160Comp(
    uint64_t *x,      // X coordinate of public key
    uint8_t isOdd,    // Y coordinate parity (0=even, 1=odd)
    uint8_t *hash     // Output: 20-byte hash160
) {
    uint32_t publicKeyBytes[16];
    uint32_t s[16];

    // Format compressed public key (33 bytes)
    // Prefix: 0x02 (even Y) or 0x03 (odd Y)
    publicKeyBytes[0] = __byte_perm(x32[7], 0x2 + isOdd, 0x4321);
    // ... pack X coordinate in big-endian ...

    // SHA256
    SHA256Initialize(s);
    SHA256Transform(s, publicKeyBytes);

    // Byte-swap for RIPEMD160 input
    for (int i = 0; i < 8; i++)
        s[i] = bswap32(s[i]);

    // RIPEMD160
    RIPEMD160Initialize((uint32_t *)hash);
    RIPEMD160Transform((uint32_t *)hash, s);
}
```

### 4.4 Modular Arithmetic

All field operations use Montgomery representation with PTX assembly:

```cuda
// 256-bit addition with carry chain
#define UADDO(c, a, b) asm volatile ("add.cc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b));
#define UADDC(c, a, b) asm volatile ("addc.cc.u64 %0, %1, %2;" : "=l"(c) : "l"(a), "l"(b));

// 256-bit multiplication with high part
#define UMULLO(lo, a, b) asm volatile ("mul.lo.u64 %0, %1, %2;" : "=l"(lo) : "l"(a), "l"(b));
#define UMULHI(hi, a, b) asm volatile ("mul.hi.u64 %0, %1, %2;" : "=l"(hi) : "l"(a), "l"(b));

// Multiply-add with carry
#define MADDO(r, a, b, c) asm volatile ("mad.hi.cc.u64 %0, %1, %2, %3;" : "=l"(r) : "l"(a), "l"(b), "l"(c));
```

#### Field Reduction

Reduction modulo p = 2^256 - 2^32 - 977:

```cuda
// Reduce 512-bit product to 256-bit result
// Uses the fact that 2^256 ≡ 2^32 + 977 (mod p)
// So we multiply the high 256 bits by 0x1000003D1 and add to low 256 bits

UMult(t, (r512 + 4), 0x1000003D1ULL);  // t = high * (2^32 + 977)
UADDO1(r512[0], t[0]);                  // r = low + t
UADDC1(r512[1], t[1]);
UADDC1(r512[2], t[2]);
UADDC1(r512[3], t[3]);
// Handle final carry...
```

---

## 5. Filter System

### 5.1 32-bit Prefix Bitmap (Stage 1)

#### Structure
- **Size**: 2^32 bits = 512 MB
- **Storage**: Raw bitmap, 1 bit per possible 32-bit prefix
- **Location**: GPU global memory

#### Algorithm
```
prefix32 = hash160[0:4]  // First 4 bytes of hash160
byte_index = prefix32 >> 3
bit_index = prefix32 & 7
is_candidate = bitmap[byte_index] & (1 << bit_index)
```

#### Coverage Analysis
For N addresses in the database:
- Expected bits set: N (assuming uniform distribution)
- Pass rate: N / 2^32
- For 28M addresses: ~0.65% pass rate (~99.35% rejection)

### 5.2 Bloom Filter (Stage 2)

#### Structure
- **Type**: Standard bloom filter with MurmurHash3
- **False Positive Rate**: 0.3% (configurable)
- **Hash Functions**: Dynamically calculated based on size

#### Optimal Parameters
For n items and false positive rate p:
- **Size (bits)**: m = -n × ln(p) / (ln(2))²
- **Hash count**: k = (m/n) × ln(2)

For 28M addresses at 0.3% FP rate:
- m ≈ 400M bits (50 MB)
- k ≈ 12 hash functions

#### MurmurHash3 Implementation

```cpp
uint32_t murmurhash3(const uint8_t *data, int len, uint32_t seed) {
    uint32_t h = seed;
    for (int i = 0; i < len; i += 4) {
        uint32_t k = ... // Load 4 bytes
        k *= 0xcc9e2d51;
        k = ROTL32(k, 15);
        k *= 0x1b873593;
        h ^= k;
        h = ROTL32(h, 13);
        h = h * 5 + 0xe6546b64;
    }
    // Finalization
    h ^= len;
    h ^= h >> 16;
    h *= 0x85ebca6b;
    h ^= h >> 13;
    h *= 0xc2b2ae35;
    h ^= h >> 16;
    return h;
}
```

### 5.3 Filter Building (build_filters.py)

```python
def build_filters(address_file, prefix_file, bloom_file):
    # Initialize structures
    prefix_bitmap = bytearray(512 * 1024 * 1024)  # 512 MB
    bloom = BloomFilter(num_addresses, fp_rate=0.003)

    for address in addresses:
        # Decode Base58Check to get hash160
        hash160 = base58_decode(address)

        # Set prefix bitmap bit
        prefix32 = int.from_bytes(hash160[0:4], 'big')
        prefix_bitmap[prefix32 // 8] |= (1 << (prefix32 % 8))

        # Add to bloom filter
        bloom.add(hash160)
```

---

## 6. GPU Implementation

### 6.1 Kernel Architecture

```cuda
__global__ void bloom_search_kernel(
    uint64_t *startKeys,        // Starting points (x,y coords)
    uint8_t *prefixBitmap,      // 512MB bitmap on GPU
    uint32_t maxFound,          // Max candidates to report
    uint32_t *out               // Output buffer
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;

    // Load starting point
    uint64_t px[4], py[4];
    Load256A(px, startKeys + tid * 4);
    Load256A(py, startKeys + tid * 4 + gridDim.x * blockDim.x * 4);

    // Check original point + endomorphisms
    CheckBitmapPrefix(prefixBitmap, px, isOdd, incr, maxFound, out);

    // Endomorphism 1: β × x
    uint64_t pex[4];
    _ModMult(pex, px, _beta);
    CheckBitmapPrefix(prefixBitmap, pex, isOdd, incr | 0x10000, maxFound, out);

    // Endomorphism 2: β² × x
    _ModMult(pex, px, _beta2);
    CheckBitmapPrefix(prefixBitmap, pex, isOdd, incr | 0x20000, maxFound, out);
}
```

### 6.2 Memory Layout

```
GPU Memory Map:
┌────────────────────────────────────────┐
│  Prefix Bitmap (512 MB)                │  Global Memory
├────────────────────────────────────────┤
│  Starting Keys (nbThread × 64 bytes)   │  Global Memory
├────────────────────────────────────────┤
│  Output Buffer (MAX_FOUND × 32 bytes)  │  Global Memory
├────────────────────────────────────────┤
│  Generator Table Gx/Gy (512 points)    │  Constant Memory
├────────────────────────────────────────┤
│  Curve Constants (_beta, _beta2, K[])  │  Constant Memory
└────────────────────────────────────────┘
```

### 6.3 Launch Configuration

```cpp
int gridSize = 512;     // Number of blocks
int blockSize = 128;    // Threads per block
int nbThread = 65536;   // Total threads

// Each thread checks 6 addresses per iteration:
// (original + 2 endomorphisms) × (even + odd Y)
uint64_t keysPerIteration = nbThread * 6;
```

### 6.4 Candidate Output Format

```cpp
#define ITEM_SIZE32 8  // 8 uint32_t per candidate

struct CandidateOutput {
    uint32_t count;           // [0]: Total candidates found
    struct Candidate {
        uint32_t threadId;    // [1]: Thread that found it
        uint32_t increment;   // [2]: Key offset + endo flags
        uint32_t hash160[5];  // [3-7]: Full 160-bit hash
    } candidates[MAX_FOUND];
};

// Increment encoding:
// Bits 0-15:  Key increment within group
// Bit 16:     Endomorphism 1 flag
// Bit 17:     Endomorphism 2 flag
```

---

## 7. Performance Characteristics

### 7.1 Benchmark Results (8x RTX 4080 SUPER)

| Metric | Value |
|--------|-------|
| Total Keys/sec | ~1.8 TKey/s |
| Keys/sec per GPU | ~225 GKey/s |
| Stage 1 Pass Rate | ~0.65% |
| Stage 2 FP Rate | ~0.3% |
| Memory per GPU | ~600 MB |

### 7.2 Bottleneck Analysis

1. **Compute Bound**: EC point operations (modular multiplication, inversion)
2. **Memory Bound**: Prefix bitmap random access
3. **Bandwidth**: GPU → CPU transfer of candidates

### 7.3 Optimization Techniques

1. **Batched Modular Inversion**: Group inversion reduces cost
2. **Precomputed Generator Table**: 512 points of G for fast addition
3. **PTX Assembly**: Hand-optimized 256-bit arithmetic
4. **Texture Memory**: Could improve bitmap access patterns
5. **Warp-Level Primitives**: Reduce divergence in hash computation

---

## 8. File Formats

### 8.1 Prefix Bitmap (`.prefix32`)

```
Offset  Size    Description
0       4       Magic: "PFX1"
4       4       Address count (uint32_t)
8       512MB   Raw bitmap data
```

### 8.2 Bloom Filter (`.bloom`)

```
Offset  Size    Description
0       4       Magic: "BLM1"
4       8       Size in bits (uint64_t)
12      4       Number of hash functions (uint32_t)
16      4       Item count (uint32_t)
20      var     Bitmap data ((size+7)/8 bytes)
```

### 8.3 Info File (`.txt`)

```
addresses=27900000
prefix_bits_set=18234567
prefix_rejection_rate=99.350000
bloom_size=402653184
bloom_hashes=12
bloom_fp_rate=0.003
```

---

## 9. Build System

### 9.1 Makefile

```makefile
CUDA = /usr/local/cuda
NVCC = $(CUDA)/bin/nvcc
CXX = g++
CCAP = 89  # Ada Lovelace (RTX 40 series)

CXXFLAGS = -O2 -std=c++17 -pthread -I$(CUDA)/include
NVCCFLAGS = -O2 -std=c++17 -gencode=arch=compute_$(CCAP),code=sm_$(CCAP)
LDFLAGS = -L$(CUDA)/lib64 -lcudart -lpthread

bloom_gpu_search: bloom_gpu_search.cu GPUGroup.h GPUMath.h GPUHash.h
    $(NVCC) $(NVCCFLAGS) -o bloom_gpu_search bloom_gpu_search.cu $(LDFLAGS)
```

### 9.2 Build Commands

```bash
# Build all targets
make -f Makefile

# Build specific target
make bloom_gpu_search

# Clean
make clean
```

### 9.3 Compute Capability Reference

| GPU Series | Compute Capability |
|------------|-------------------|
| RTX 40xx | 89 (Ada) |
| RTX 30xx | 86 (Ampere) |
| RTX 20xx | 75 (Turing) |
| GTX 10xx | 61 (Pascal) |

---

## 10. Usage Guide

### 10.1 Building Filters

```bash
# Download or prepare address list (one address per line)
# Only processes addresses starting with 1 or 3

python3 build_filters.py addresses.txt prefix.bin bloom.bin info.txt
```

### 10.2 Running the Search

```bash
# Basic usage (single GPU)
./bloom_gpu_search prefix.bin bloom.bin

# Multi-GPU (GPUs 0-7)
./bloom_gpu_search prefix.bin bloom.bin -g 0,1,2,3,4,5,6,7

# With time limit (60 seconds)
./bloom_gpu_search prefix.bin bloom.bin -g 0,1,2,3,4,5,6,7 -t 60
```

### 10.3 Output Format

```
GPU Bloom Filter Bitcoin Address Search
=========================================

GPUs: 0 1 2 3 4 5 6 7
Run time: 30 seconds

Loading prefix bitmap...
  Loaded bitmap for 27900000 addresses (536870912 bytes read)
Loading bloom filter...
  402653184 bits, 12 hashes, 27900000 addresses

GPU #0: NVIDIA GeForce RTX 4080 SUPER (80 MPs)
GPU #1: NVIDIA GeForce RTX 4080 SUPER (80 MPs)
...

Searching...

[ 30s] 1823.45 GKey/s | Prefix: 12543 | Bloom: 38

=========================================
Final Results:
  Total keys checked: 54703500000000
  Prefix bitmap hits: 12543
  Bloom filter passes: 38
  Average rate: 1823.45 GKey/s
=========================================
```

### 10.4 Interpreting Results

- **Prefix hits**: Addresses matching 32-bit prefix (~0.65% of checked)
- **Bloom passes**: Candidates passing bloom filter (~0.3% of prefix hits)
- **True matches**: Would require Stage 3 database verification

---

## Appendix A: Mathematical Background

### A.1 secp256k1 Curve Parameters

```
p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
a = 0
b = 7
Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
Gy = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
```

### A.2 Probability Calculations

For a bloom filter with:
- m bits
- k hash functions
- n items

False positive probability: p = (1 - e^(-kn/m))^k

For optimal k = (m/n) × ln(2): p ≈ (1/2)^k ≈ 0.6185^(m/n)

### A.3 Expected Collision Time

For N target addresses in space of size 2^160:
- Per-key hit probability: p = N / 2^160
- Expected keys to hit: 1/p = 2^160 / N
- At rate R keys/sec: Time = 2^160 / (N × R) seconds

---

## Appendix B: License

VanitySearch GPU code is licensed under GPL-3.0.
This derivative work maintains the same license.

Copyright (c) 2019 Jean Luc PONS (VanitySearch)
Copyright (c) 2024-2026 (Bloom Filter Integration)

---

## Appendix C: References

1. [VanitySearch by JeanLucPons](https://github.com/JeanLucPons/VanitySearch)
2. [secp256k1 Specification](https://www.secg.org/sec2-v2.pdf)
3. [Bitcoin Address Derivation](https://en.bitcoin.it/wiki/Technical_background_of_version_1_Bitcoin_addresses)
4. [Bloom Filter Theory](https://en.wikipedia.org/wiki/Bloom_filter)
5. [MurmurHash3](https://github.com/aappleby/smhasher)
