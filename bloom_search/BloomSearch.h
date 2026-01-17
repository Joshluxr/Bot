/*
 * BloomSearch.h - Main header for bloom filter-based Bitcoin address search
 *
 * This is a modified VanitySearch that:
 * 1. Checks generated keys against a bloom filter of known addresses
 * 2. Uses deterministic work units for checkpoint/resume
 * 3. Supports batch GPU checking for maximum throughput
 *
 * Key differences from VanitySearch:
 * - No vanity prefix matching, instead bloom filter matching
 * - Deterministic keyspace partitioning (no random keys)
 * - Checkpoint system saves completed work units
 * - CPU verifies bloom filter hits against sorted hash160 list
 */

#ifndef BLOOM_SEARCH_H
#define BLOOM_SEARCH_H

#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <fstream>
#include "Checkpoint.h"

// Forward declarations from VanitySearch
class Secp256K1;
class Int;
class Point;
class IntGroup;

#ifdef WIN64
#include <Windows.h>
#endif

// ============================================================================
// BLOOM FILTER MANAGER
// ============================================================================

class BloomFilter {
public:
    uint64_t numBits;
    uint64_t numBytes;
    uint32_t numHashes;
    uint32_t itemCount;
    uint32_t seeds[24];
    uint8_t* data;         // CPU memory
    uint8_t* d_data;       // GPU memory (if loaded)

    BloomFilter() : numBits(0), numBytes(0), numHashes(0), itemCount(0),
                    data(nullptr), d_data(nullptr) {
        memset(seeds, 0, sizeof(seeds));
    }

    ~BloomFilter() {
        if (data) free(data);
        // Note: d_data freed by CUDA code
    }

    bool load(const std::string& filename);
    bool copyToGPU();
    bool check(const uint8_t* hash160);
};

// ============================================================================
// SORTED HASH160 LIST (for CPU verification)
// ============================================================================

class Hash160List {
public:
    uint8_t* data;
    uint64_t count;

    Hash160List() : data(nullptr), count(0) {}
    ~Hash160List() { if (data) free(data); }

    bool load(const std::string& filename);
    bool contains(const uint8_t* hash160);  // Binary search
};

// ============================================================================
// GPU ENGINE (simplified from VanitySearch)
// ============================================================================

class GPUEngine {
public:
    GPUEngine(int gpuId, uint32_t maxFound);
    ~GPUEngine();

    bool SetBloomFilter(BloomFilter* bf);
    void SetSearchMode(bool compressed, bool uncompressed);
    void SetKeys(std::vector<Point>& startPoints);

    int Launch(std::vector<ITEM>& matchItems, bool spinWait = false);

    int GetGroupSize() { return GRP_SIZE; }
    int GetNbThread() { return nbThread; }
    std::string GetDeviceName() { return deviceName; }
    uint64_t GetMemory() { return gpuMemory; }

private:
    int gpuId;
    int nbThread;
    uint64_t gpuMemory;
    std::string deviceName;

    // CUDA resources
    uint64_t* inputKey;
    uint64_t* inputKeyPinned;
    uint32_t* outputBuffer;
    uint32_t* outputBufferPinned;

    // Bloom filter on GPU
    uint8_t* d_bloomFilter;
    uint64_t bloomBits;
    uint32_t* d_bloomSeeds;
    int bloomHashes;

    bool searchCompressed;
    bool searchUncompressed;
};

// Match item structure
struct ITEM {
    uint32_t threadId;
    int32_t incr;
    int32_t endo;
    int32_t mode;
    uint8_t hash160[20];
};

// ============================================================================
// MAIN BLOOM SEARCH CLASS
// ============================================================================

class BloomSearch {
public:
    BloomSearch(Secp256K1* secp,
                const std::string& bloomFile,
                const std::string& sortedFile,
                const std::string& checkpointFile,
                bool compressed,
                bool uncompressed,
                const std::string& seed,
                const std::string& outputFile);

    ~BloomSearch();

    void Search(int numCPUThreads,
                std::vector<int>& gpuIds,
                std::vector<int>& gridSizes,
                bool& shouldExit);

    void PrintStats();
    void SaveCheckpoint();
    bool LoadCheckpoint();

private:
    // Secp256k1 context
    Secp256K1* secp;

    // Bloom filter and verification
    BloomFilter bloom;
    Hash160List hashList;

    // Checkpoint system
    CheckpointManager checkpoint;
    WorkUnitGenerator workGen;

    // Configuration
    bool searchCompressed;
    bool searchUncompressed;
    std::string outputFile;
    uint8_t seedBytes[32];

    // Statistics
    std::atomic<uint64_t> totalKeysChecked;
    std::atomic<uint64_t> bloomHits;
    std::atomic<uint64_t> verifiedMatches;
    std::chrono::time_point<std::chrono::steady_clock> startTime;

    // Thread synchronization
    std::mutex outputMutex;
    std::mutex checkpointMutex;
    std::atomic<bool>* endOfSearch;

    // GPU engines
    std::vector<GPUEngine*> gpuEngines;

    // Internal methods
    void CPUSearchThread(int threadId);
    void GPUSearchThread(int gpuIdx, int gridSize);

    void ProcessMatch(const ITEM& item, const Int& baseKey);
    void OutputMatch(const std::string& address,
                     const std::string& privateKey,
                     const uint8_t* hash160);

    void GetStartingKey(uint64_t workUnitId, uint64_t offset, Int& key, Point& pubKey);
};

#endif // BLOOM_SEARCH_H
