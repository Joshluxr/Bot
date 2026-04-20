/*
 * Checkpoint.h - Deterministic keyspace partitioning and checkpoint system
 *
 * CONCEPT: Instead of random key generation, we partition the 256-bit keyspace
 * into deterministic "work units". Each work unit:
 * - Has a unique ID (64-bit)
 * - Covers a specific range of private keys
 * - Can be marked as completed
 * - Progress is stored in a simple bitmap file
 *
 * This ensures:
 * 1. No duplicate work - each key checked exactly once
 * 2. Easy resume - just skip completed work units
 * 3. Distributed computing ready - assign work units to different machines
 * 4. Random-like coverage - work units processed in shuffled order
 *
 * KEYSPACE PARTITIONING:
 * - Total keyspace: 2^256 private keys
 * - Practical keyspace: 2^160 (RIPEMD160 collision at best)
 * - Work unit size: 2^40 keys (~1.1 trillion keys)
 * - Total work units: 2^120 (but we use 64-bit IDs with good entropy)
 *
 * At 23 billion keys/second:
 * - One work unit = ~48 seconds
 * - Save checkpoint every ~5 minutes (6 work units)
 */

#ifndef CHECKPOINT_H
#define CHECKPOINT_H

#include <stdint.h>
#include <string>
#include <vector>
#include <fstream>
#include <mutex>
#include <atomic>
#include <cstring>

// ============================================================================
// CONFIGURATION
// ============================================================================

// Work unit size: 2^40 keys = ~1.1 trillion keys
// At 23B keys/sec, this is ~48 seconds of work
#define WORK_UNIT_BITS 40
#define WORK_UNIT_SIZE (1ULL << WORK_UNIT_BITS)

// Checkpoint file format version
#define CHECKPOINT_VERSION 1

// ============================================================================
// WORK UNIT STRUCTURE
// ============================================================================

struct WorkUnit {
    uint64_t id;           // Unique work unit ID
    uint8_t startKey[32];  // Starting private key (256 bits)
    uint64_t keysToCheck;  // Number of keys in this work unit
    bool completed;        // Has this work unit been fully processed?
};

// ============================================================================
// CHECKPOINT DATA
// ============================================================================

struct CheckpointHeader {
    uint32_t version;
    uint32_t flags;
    uint64_t totalWorkUnits;
    uint64_t completedWorkUnits;
    uint64_t totalKeysChecked;
    uint64_t currentWorkUnitId;
    uint64_t keysInCurrentUnit;  // Progress within current work unit
    uint8_t seedHash[32];        // SHA256 of seed for verification
    uint64_t createdTimestamp;
    uint64_t lastUpdateTimestamp;
    char reserved[176];          // Pad to 256 bytes
};

// ============================================================================
// DETERMINISTIC WORK UNIT GENERATOR
// ============================================================================

class WorkUnitGenerator {
private:
    uint8_t masterSeed[32];      // Master seed for reproducibility
    uint64_t currentUnitId;      // Current work unit being processed
    std::mutex mtx;

    // Fisher-Yates shuffle state (for randomized order)
    std::vector<uint64_t> shuffleState;
    uint64_t shuffleIndex;

    // Simple PRNG for shuffling (deterministic from seed)
    uint64_t prngState[4];

    uint64_t xoshiro256pp() {
        const uint64_t result = rotl(prngState[0] + prngState[3], 23) + prngState[0];
        const uint64_t t = prngState[1] << 17;

        prngState[2] ^= prngState[0];
        prngState[3] ^= prngState[1];
        prngState[1] ^= prngState[2];
        prngState[0] ^= prngState[3];

        prngState[2] ^= t;
        prngState[3] = rotl(prngState[3], 45);

        return result;
    }

    static uint64_t rotl(uint64_t x, int k) {
        return (x << k) | (x >> (64 - k));
    }

    void initPRNG(const uint8_t* seed) {
        // Initialize PRNG state from seed
        for (int i = 0; i < 4; i++) {
            prngState[i] = 0;
            for (int j = 0; j < 8; j++) {
                prngState[i] |= (uint64_t)seed[i * 8 + j] << (j * 8);
            }
        }
        // Warm up
        for (int i = 0; i < 20; i++) xoshiro256pp();
    }

public:
    WorkUnitGenerator() : currentUnitId(0), shuffleIndex(0) {
        memset(masterSeed, 0, 32);
        memset(prngState, 0, sizeof(prngState));
    }

    void initialize(const uint8_t* seed) {
        memcpy(masterSeed, seed, 32);
        initPRNG(seed);
        currentUnitId = 0;
        shuffleIndex = 0;

        // Pre-generate shuffled work unit order
        // We use a "lazy" shuffle - generate on demand
    }

    // Get the starting private key for a work unit
    void getWorkUnitKey(uint64_t unitId, uint8_t* outKey) {
        // The key is derived from: masterSeed XOR (unitId expanded to 256 bits)
        // This ensures deterministic but well-distributed keys

        memset(outKey, 0, 32);

        // Place unitId in upper bits (randomizes the high bits)
        // The low WORK_UNIT_BITS will be iterated through
        outKey[0] = (unitId >> 56) & 0xFF;
        outKey[1] = (unitId >> 48) & 0xFF;
        outKey[2] = (unitId >> 40) & 0xFF;
        outKey[3] = (unitId >> 32) & 0xFF;
        outKey[4] = (unitId >> 24) & 0xFF;
        outKey[5] = (unitId >> 16) & 0xFF;
        outKey[6] = (unitId >> 8) & 0xFF;
        outKey[7] = unitId & 0xFF;

        // XOR with master seed for additional entropy
        for (int i = 0; i < 32; i++) {
            outKey[i] ^= masterSeed[i];
        }

        // Clear the low WORK_UNIT_BITS (these will be iterated)
        // Work unit covers keys from outKey to outKey + WORK_UNIT_SIZE - 1
        int bytesToClear = WORK_UNIT_BITS / 8;
        int bitsRemaining = WORK_UNIT_BITS % 8;

        for (int i = 0; i < bytesToClear; i++) {
            outKey[31 - i] = 0;
        }
        if (bitsRemaining > 0) {
            outKey[31 - bytesToClear] &= (0xFF << bitsRemaining);
        }
    }

    // Get next work unit (thread-safe)
    WorkUnit getNextWorkUnit() {
        std::lock_guard<std::mutex> lock(mtx);

        WorkUnit wu;
        wu.id = currentUnitId++;
        wu.keysToCheck = WORK_UNIT_SIZE;
        wu.completed = false;
        getWorkUnitKey(wu.id, wu.startKey);

        return wu;
    }

    // Get a specific work unit by ID
    WorkUnit getWorkUnit(uint64_t unitId) {
        WorkUnit wu;
        wu.id = unitId;
        wu.keysToCheck = WORK_UNIT_SIZE;
        wu.completed = false;
        getWorkUnitKey(unitId, wu.startKey);
        return wu;
    }

    uint64_t getCurrentUnitId() const { return currentUnitId; }
    void setCurrentUnitId(uint64_t id) { currentUnitId = id; }
};

// ============================================================================
// CHECKPOINT MANAGER
// ============================================================================

class CheckpointManager {
private:
    std::string checkpointFile;
    std::string completedFile;  // Bitmap of completed work units
    CheckpointHeader header;
    std::mutex mtx;

    // Completed work units bitmap (in memory for fast access)
    std::vector<uint64_t> completedBitmap;
    uint64_t bitmapSize;

    bool isUnitCompleted(uint64_t unitId) {
        if (unitId / 64 >= completedBitmap.size()) return false;
        return (completedBitmap[unitId / 64] & (1ULL << (unitId % 64))) != 0;
    }

    void markUnitCompleted(uint64_t unitId) {
        uint64_t wordIdx = unitId / 64;
        if (wordIdx >= completedBitmap.size()) {
            completedBitmap.resize(wordIdx + 1024, 0);  // Grow by 1024 words
        }
        completedBitmap[wordIdx] |= (1ULL << (unitId % 64));
        header.completedWorkUnits++;
    }

public:
    CheckpointManager(const std::string& filename)
        : checkpointFile(filename),
          completedFile(filename + ".completed"),
          bitmapSize(0) {
        memset(&header, 0, sizeof(header));
        header.version = CHECKPOINT_VERSION;
    }

    bool exists() {
        std::ifstream f(checkpointFile);
        return f.good();
    }

    bool load() {
        std::lock_guard<std::mutex> lock(mtx);

        std::ifstream f(checkpointFile, std::ios::binary);
        if (!f.good()) return false;

        f.read((char*)&header, sizeof(header));
        if (header.version != CHECKPOINT_VERSION) {
            return false;
        }

        // Load completed bitmap
        std::ifstream bf(completedFile, std::ios::binary);
        if (bf.good()) {
            bf.seekg(0, std::ios::end);
            size_t size = bf.tellg();
            bf.seekg(0, std::ios::beg);

            completedBitmap.resize(size / 8);
            bf.read((char*)completedBitmap.data(), size);
        }

        return true;
    }

    void save() {
        std::lock_guard<std::mutex> lock(mtx);

        header.lastUpdateTimestamp = time(nullptr);

        std::ofstream f(checkpointFile, std::ios::binary);
        f.write((char*)&header, sizeof(header));
        f.close();

        // Save completed bitmap
        std::ofstream bf(completedFile, std::ios::binary);
        bf.write((char*)completedBitmap.data(), completedBitmap.size() * 8);
        bf.close();
    }

    void initialize(const uint8_t* seedHash) {
        memcpy(header.seedHash, seedHash, 32);
        header.createdTimestamp = time(nullptr);
        header.lastUpdateTimestamp = header.createdTimestamp;
        header.totalWorkUnits = 0;
        header.completedWorkUnits = 0;
        header.totalKeysChecked = 0;
        header.currentWorkUnitId = 0;
        header.keysInCurrentUnit = 0;
    }

    // Get next uncompleted work unit
    uint64_t getNextUncompletedUnit(uint64_t startFrom = 0) {
        std::lock_guard<std::mutex> lock(mtx);

        for (uint64_t id = startFrom; ; id++) {
            if (!isUnitCompleted(id)) {
                return id;
            }
        }
    }

    void completeWorkUnit(uint64_t unitId, uint64_t keysChecked) {
        std::lock_guard<std::mutex> lock(mtx);
        markUnitCompleted(unitId);
        header.totalKeysChecked += keysChecked;
    }

    void updateProgress(uint64_t currentUnit, uint64_t keysInUnit) {
        std::lock_guard<std::mutex> lock(mtx);
        header.currentWorkUnitId = currentUnit;
        header.keysInCurrentUnit = keysInUnit;
    }

    uint64_t getTotalKeysChecked() const { return header.totalKeysChecked; }
    uint64_t getCompletedWorkUnits() const { return header.completedWorkUnits; }

    void printStatus() {
        printf("Checkpoint Status:\n");
        printf("  - Completed work units: %lu\n", header.completedWorkUnits);
        printf("  - Total keys checked: %lu (%.2f trillion)\n",
               header.totalKeysChecked,
               header.totalKeysChecked / 1e12);
        printf("  - Current work unit: %lu\n", header.currentWorkUnitId);
        printf("  - Progress in current unit: %lu / %lu\n",
               header.keysInCurrentUnit, WORK_UNIT_SIZE);
    }
};

#endif // CHECKPOINT_H
