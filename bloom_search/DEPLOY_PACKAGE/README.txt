BloomSearch Deployment Package
==============================

This package adds bloom filter matching to VanitySearch, allowing you to
search for Bitcoin addresses that exist in a database of 55+ million addresses.

QUICK START
-----------

1. Copy files to GPU server:
   scp -r DEPLOY_PACKAGE/* root@gpu-server:/root/VanitySearch/

2. Build the bloom filter (takes ~15-20 minutes):
   cd /root/VanitySearch
   python3 build_bloom.py

3. Copy GPUComputeBloom.h to GPU folder:
   cp GPUComputeBloom.h GPU/

4. The bloom filter is now ready!
   Files created:
   - targets.bloom (~200 MB) - bloom filter for GPU
   - targets.sorted (~1.1 GB) - sorted hash160s for CPU verification

FILES INCLUDED
--------------

build_bloom.py
  Python script to download Bitcoin addresses and build bloom filter.
  - Downloads 55M addresses from loyce.club
  - Creates bloom filter with 0.00001% false positive rate
  - Creates sorted hash160 file for verification

GPUComputeBloom.h
  CUDA header with bloom filter functions for GPU kernel.
  - murmur3_32() - Hash function matching Python builder
  - bloom_check() - Check if hash160 is in bloom filter
  - CheckHashBloom() - Integration with VanitySearch hash checking

Checkpoint.h
  C++ header for checkpoint/resume functionality.
  - Deterministic work unit partitioning
  - Never checks the same key twice
  - Resume from where you left off

INTEGRATION WITH VANITYSEARCH
-----------------------------

To fully integrate bloom filter into VanitySearch GPU kernel:

1. In GPU/GPUEngine.cu, add after other includes:

   #include "GPUComputeBloom.h"

   // After CUDA init, load bloom filter:
   uint8_t* h_bloom = loadBloomFilter("targets.bloom", &numBits, &numHashes, seeds);
   cudaMalloc(&d_bloom, numBytes);
   cudaMemcpy(d_bloom, h_bloom, numBytes, cudaMemcpyHostToDevice);
   cudaMemcpyToSymbol(d_bloomData, &d_bloom, sizeof(uint8_t*));
   cudaMemcpyToSymbol(d_bloomBits, &numBits, sizeof(uint64_t));
   cudaMemcpyToSymbol(d_bloomHashes, &numHashes, sizeof(uint32_t));
   cudaMemcpyToSymbol(d_bloomSeeds, seeds, numHashes * sizeof(uint32_t));

2. In GPU/GPUCompute.h, replace CHECK_POINT macro with:

   #ifdef USE_BLOOM_FILTER
   #define CHECK_POINT(h,incr,endo,mode) CHECK_POINT_BLOOM(h,incr,endo,mode)
   #else
   // original prefix-based checking
   #endif

3. On CPU side, verify bloom filter hits:

   // Binary search in sorted hash160 file
   bool verifyMatch(uint8_t* hash160, uint8_t* sortedData, uint64_t count) {
       int64_t left = 0, right = count - 1;
       while (left <= right) {
           int64_t mid = (left + right) / 2;
           int cmp = memcmp(sortedData + mid * 20, hash160, 20);
           if (cmp == 0) return true;
           if (cmp < 0) left = mid + 1;
           else right = mid - 1;
       }
       return false;
   }

PERFORMANCE
-----------

Bloom filter size: ~200 MB
False positive rate: 0.00001% (1 in 10 million)
At 23B keys/sec: ~2.3 false positives per second

The CPU can easily verify 2.3 candidates per second using binary search
in the sorted hash160 file.

Expected slowdown: 5-15% due to bloom filter memory accesses.

CHECKPOINT SYSTEM
-----------------

The checkpoint system divides the keyspace into "work units":
- Each work unit = 2^40 keys (~1 trillion)
- At 23B keys/sec = ~48 seconds per work unit
- Checkpoint saves which work units are complete

To use checkpoints:
1. Use same seed every time you run
2. Checkpoint file tracks completed work units
3. Resume skips completed units automatically

LICENSE
-------

MIT License - Use at your own risk.

DISCLAIMER
----------

This tool is for educational and research purposes only.
The probability of finding a collision is astronomically low (~1 in 2^160).
