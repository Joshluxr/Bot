/*
 * BloomSearch.cpp - Main implementation for bloom filter-based Bitcoin address search
 *
 * This searches for Bitcoin addresses that exist in a bloom filter of known addresses.
 * Uses deterministic work units for reliable checkpoint/resume.
 */

#include "BloomSearch.h"
#include "SECP256K1.h"
#include "Int.h"
#include "Point.h"
#include "IntGroup.h"
#include "hash/sha256.h"
#include "hash/ripemd160.h"

#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <algorithm>
#include <chrono>
#include <csignal>

// ============================================================================
// BLOOM FILTER IMPLEMENTATION
// ============================================================================

// MurmurHash3 32-bit (matches GPU version)
static uint32_t murmur3_32(const uint8_t* key, int len, uint32_t seed) {
    const uint32_t c1 = 0xcc9e2d51;
    const uint32_t c2 = 0x1b873593;

    uint32_t h1 = seed;
    const int nblocks = len / 4;

    const uint32_t* blocks = (const uint32_t*)key;
    for (int i = 0; i < nblocks; i++) {
        uint32_t k1 = blocks[i];
        k1 *= c1;
        k1 = (k1 << 15) | (k1 >> 17);
        k1 *= c2;
        h1 ^= k1;
        h1 = (h1 << 13) | (h1 >> 19);
        h1 = h1 * 5 + 0xe6546b64;
    }

    const uint8_t* tail = key + nblocks * 4;
    uint32_t k1 = 0;
    switch (len & 3) {
    case 3: k1 ^= tail[2] << 16;
    case 2: k1 ^= tail[1] << 8;
    case 1: k1 ^= tail[0];
        k1 *= c1;
        k1 = (k1 << 15) | (k1 >> 17);
        k1 *= c2;
        h1 ^= k1;
    }

    h1 ^= len;
    h1 ^= h1 >> 16;
    h1 *= 0x85ebca6b;
    h1 ^= h1 >> 13;
    h1 *= 0xc2b2ae35;
    h1 ^= h1 >> 16;

    return h1;
}

bool BloomFilter::load(const std::string& filename) {
    std::ifstream f(filename, std::ios::binary);
    if (!f.good()) {
        std::cerr << "Error: Cannot open bloom filter file: " << filename << std::endl;
        return false;
    }

    // Read header (256 bytes)
    f.read((char*)&numBits, 8);
    f.read((char*)&numBytes, 8);
    f.read((char*)&numHashes, 4);
    f.read((char*)&itemCount, 4);

    for (uint32_t i = 0; i < numHashes && i < 24; i++) {
        f.read((char*)&seeds[i], 4);
    }

    // Skip to data (header is 256 bytes)
    f.seekg(256);

    // Allocate and read bloom filter data
    data = (uint8_t*)malloc(numBytes);
    if (!data) {
        std::cerr << "Error: Cannot allocate " << numBytes << " bytes for bloom filter" << std::endl;
        return false;
    }

    f.read((char*)data, numBytes);

    std::cout << "Loaded bloom filter:" << std::endl;
    std::cout << "  - Bits: " << numBits << std::endl;
    std::cout << "  - Bytes: " << numBytes << " (" << numBytes / 1024 / 1024 << " MB)" << std::endl;
    std::cout << "  - Hashes: " << numHashes << std::endl;
    std::cout << "  - Items: " << itemCount << std::endl;

    return true;
}

bool BloomFilter::check(const uint8_t* hash160) {
    for (uint32_t i = 0; i < numHashes; i++) {
        uint32_t h = murmur3_32(hash160, 20, seeds[i]);
        uint64_t bitPos = h % numBits;
        uint64_t bytePos = bitPos / 8;
        uint8_t bitMask = 1 << (bitPos % 8);
        if (!(data[bytePos] & bitMask)) {
            return false;
        }
    }
    return true;
}

// ============================================================================
// HASH160 LIST IMPLEMENTATION (for CPU verification)
// ============================================================================

bool Hash160List::load(const std::string& filename) {
    std::ifstream f(filename, std::ios::binary | std::ios::ate);
    if (!f.good()) {
        std::cerr << "Error: Cannot open sorted hash160 file: " << filename << std::endl;
        return false;
    }

    size_t fileSize = f.tellg();
    count = fileSize / 20;

    f.seekg(0);

    data = (uint8_t*)malloc(fileSize);
    if (!data) {
        std::cerr << "Error: Cannot allocate " << fileSize << " bytes for hash160 list" << std::endl;
        return false;
    }

    f.read((char*)data, fileSize);

    std::cout << "Loaded sorted hash160 list:" << std::endl;
    std::cout << "  - Count: " << count << std::endl;
    std::cout << "  - Size: " << fileSize / 1024 / 1024 << " MB" << std::endl;

    return true;
}

bool Hash160List::contains(const uint8_t* hash160) {
    // Binary search
    int64_t left = 0;
    int64_t right = count - 1;

    while (left <= right) {
        int64_t mid = (left + right) / 2;
        int cmp = memcmp(data + mid * 20, hash160, 20);

        if (cmp == 0) {
            return true;
        } else if (cmp < 0) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }

    return false;
}

// ============================================================================
// BLOOM SEARCH IMPLEMENTATION
// ============================================================================

BloomSearch::BloomSearch(
    Secp256K1* secp,
    const std::string& bloomFile,
    const std::string& sortedFile,
    const std::string& checkpointFile,
    bool compressed,
    bool uncompressed,
    const std::string& seed,
    const std::string& outputFile)
    : secp(secp),
      checkpoint(checkpointFile),
      searchCompressed(compressed),
      searchUncompressed(uncompressed),
      outputFile(outputFile),
      totalKeysChecked(0),
      bloomHits(0),
      verifiedMatches(0),
      endOfSearch(nullptr)
{
    // Load bloom filter
    if (!bloom.load(bloomFile)) {
        throw std::runtime_error("Failed to load bloom filter");
    }

    // Load sorted hash160 list for CPU verification
    if (!hashList.load(sortedFile)) {
        throw std::runtime_error("Failed to load hash160 list");
    }

    // Derive seed bytes
    if (seed.empty()) {
        // Generate random seed
        for (int i = 0; i < 32; i++) {
            seedBytes[i] = rand() & 0xFF;
        }
    } else {
        // Derive from provided seed using SHA256
        sha256((uint8_t*)seed.c_str(), seed.length(), seedBytes);
    }

    // Initialize work unit generator
    workGen.initialize(seedBytes);

    // Load or initialize checkpoint
    if (checkpoint.exists()) {
        if (checkpoint.load()) {
            std::cout << "Resuming from checkpoint..." << std::endl;
            checkpoint.printStatus();
            workGen.setCurrentUnitId(checkpoint.getNextUncompletedUnit());
        }
    } else {
        uint8_t seedHash[32];
        sha256(seedBytes, 32, seedHash);
        checkpoint.initialize(seedHash);
    }

    startTime = std::chrono::steady_clock::now();
}

BloomSearch::~BloomSearch() {
    for (auto engine : gpuEngines) {
        delete engine;
    }
}

void BloomSearch::GetStartingKey(uint64_t workUnitId, uint64_t offset, Int& key, Point& pubKey) {
    // Get the base key for this work unit
    WorkUnit wu = workGen.getWorkUnit(workUnitId);

    // Set the key from work unit bytes
    key.SetInt32(0);
    for (int i = 0; i < 32; i++) {
        key.bits64[3 - i / 8] |= ((uint64_t)wu.startKey[i]) << ((7 - i % 8) * 8);
    }

    // Add offset
    Int off;
    off.SetInt64(offset);
    key.Add(&off);

    // Compute public key
    pubKey = secp->ComputePublicKey(&key);
}

void BloomSearch::CPUSearchThread(int threadId) {
    IntGroup* grp = new IntGroup(GRP_SIZE / 2 + 1);

    Int key;
    Point startP;
    Point pts[GRP_SIZE];
    Int dx[GRP_SIZE / 2 + 1];

    uint8_t hash160[20];

    Point Gn[GRP_SIZE / 2];
    Point _2Gn;

    // Precompute multiples of G
    Point G = secp->G;
    Gn[0] = G;
    for (int i = 1; i < GRP_SIZE / 2; i++) {
        Gn[i] = secp->AddDirect(Gn[i - 1], G);
    }
    _2Gn = secp->DoubleDirect(Gn[GRP_SIZE / 2 - 1]);

    grp->Set(dx);

    while (!*endOfSearch) {
        // Get next work unit
        WorkUnit wu = workGen.getNextWorkUnit();

        // Set starting key
        key.SetInt32(0);
        for (int i = 0; i < 32; i++) {
            key.bits64[3 - i / 8] |= ((uint64_t)wu.startKey[i]) << ((7 - i % 8) * 8);
        }

        // Add thread offset
        Int threadOff;
        threadOff.SetInt64((int64_t)threadId * (WORK_UNIT_SIZE / 8));  // Divide work among threads
        key.Add(&threadOff);

        // Compute starting point
        Int km(&key);
        km.Add((uint64_t)GRP_SIZE / 2);
        startP = secp->ComputePublicKey(&km);

        uint64_t keysInUnit = 0;
        uint64_t keysPerThread = WORK_UNIT_SIZE / 8;  // 8 CPU threads

        while (keysInUnit < keysPerThread && !*endOfSearch) {
            // Fill group with delta-x values
            int hLength = GRP_SIZE / 2 - 1;
            for (int i = 0; i < hLength; i++) {
                dx[i].ModSub(&Gn[i].x, &startP.x);
            }
            dx[hLength].ModSub(&Gn[hLength].x, &startP.x);
            dx[hLength + 1].ModSub(&_2Gn.x, &startP.x);

            // Batch modular inversion
            grp->ModInv();

            // Center point
            pts[GRP_SIZE / 2] = startP;

            // Compute all points
            Int dy, dyn, _s, _p;
            Point pp, pn;

            for (int i = 0; i < hLength; i++) {
                pp = startP;
                pn = startP;

                // P = startP + (i+1)*G
                dy.ModSub(&Gn[i].y, &pp.y);
                _s.ModMulK1(&dy, &dx[i]);
                _p.ModSquareK1(&_s);

                pp.x.ModNeg();
                pp.x.ModAdd(&_p);
                pp.x.ModSub(&Gn[i].x);

                pp.y.ModSub(&Gn[i].x, &pp.x);
                pp.y.ModMulK1(&_s);
                pp.y.ModSub(&Gn[i].y);

                // P = startP - (i+1)*G
                dyn.Set(&Gn[i].y);
                dyn.ModNeg();
                dyn.ModSub(&pn.y);

                _s.ModMulK1(&dyn, &dx[i]);
                _p.ModSquareK1(&_s);

                pn.x.ModNeg();
                pn.x.ModAdd(&_p);
                pn.x.ModSub(&Gn[i].x);

                pn.y.ModSub(&Gn[i].x, &pn.x);
                pn.y.ModMulK1(&_s);
                pn.y.ModAdd(&Gn[i].y);

                pts[GRP_SIZE / 2 + (i + 1)] = pp;
                pts[GRP_SIZE / 2 - (i + 1)] = pn;
            }

            // First point
            pn = startP;
            dyn.Set(&Gn[hLength].y);
            dyn.ModNeg();
            dyn.ModSub(&pn.y);

            _s.ModMulK1(&dyn, &dx[hLength]);
            _p.ModSquareK1(&_s);

            pn.x.ModNeg();
            pn.x.ModAdd(&_p);
            pn.x.ModSub(&Gn[hLength].x);

            pn.y.ModSub(&Gn[hLength].x, &pn.x);
            pn.y.ModMulK1(&_s);
            pn.y.ModAdd(&Gn[hLength].y);

            pts[0] = pn;

            // Check all points against bloom filter
            for (int i = 0; i < GRP_SIZE; i++) {
                Int privKey(&key);
                privKey.Add((int64_t)(i - GRP_SIZE / 2));

                if (searchCompressed) {
                    secp->GetHash160(P2PKH, true, pts[i], hash160);

                    if (bloom.check(hash160)) {
                        bloomHits++;
                        // Verify with sorted list
                        if (hashList.contains(hash160)) {
                            verifiedMatches++;
                            // Output match
                            std::string addr = secp->GetAddress(P2PKH, true, pts[i]);
                            OutputMatch(addr, privKey.GetBase16(), hash160);
                        }
                    }
                }

                if (searchUncompressed) {
                    secp->GetHash160(P2PKH, false, pts[i], hash160);

                    if (bloom.check(hash160)) {
                        bloomHits++;
                        if (hashList.contains(hash160)) {
                            verifiedMatches++;
                            std::string addr = secp->GetAddress(P2PKH, false, pts[i]);
                            OutputMatch(addr, privKey.GetBase16(), hash160);
                        }
                    }
                }

                totalKeysChecked++;
            }

            // Update starting point
            pp = startP;
            dy.ModSub(&_2Gn.y, &pp.y);
            _s.ModMulK1(&dy, &dx[hLength + 1]);
            _p.ModSquareK1(&_s);

            pp.x.ModNeg();
            pp.x.ModAdd(&_p);
            pp.x.ModSub(&_2Gn.x);

            pp.y.ModSub(&_2Gn.x, &pp.x);
            pp.y.ModMulK1(&_s);
            pp.y.ModSub(&_2Gn.y);

            startP = pp;
            key.Add((uint64_t)GRP_SIZE);
            keysInUnit += GRP_SIZE;
        }

        // Mark work unit completed
        checkpoint.completeWorkUnit(wu.id, keysInUnit);
    }

    delete grp;
}

void BloomSearch::OutputMatch(
    const std::string& address,
    const std::string& privateKey,
    const uint8_t* hash160)
{
    std::lock_guard<std::mutex> lock(outputMutex);

    // Print to console
    std::cout << "\n*** MATCH FOUND ***" << std::endl;
    std::cout << "Address: " << address << std::endl;
    std::cout << "Private Key: " << privateKey << std::endl;
    std::cout << "Hash160: ";
    for (int i = 0; i < 20; i++) {
        printf("%02x", hash160[i]);
    }
    std::cout << std::endl;

    // Append to output file
    if (!outputFile.empty()) {
        std::ofstream f(outputFile, std::ios::app);
        f << address << "," << privateKey << std::endl;
        f.close();
    }
}

void BloomSearch::PrintStats() {
    auto now = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(now - startTime).count();

    uint64_t keys = totalKeysChecked.load();
    double rate = keys / elapsed;

    std::cout << "\r"
              << "Keys: " << keys / 1e9 << "B | "
              << "Rate: " << rate / 1e9 << " Gkeys/s | "
              << "Bloom hits: " << bloomHits.load() << " | "
              << "Matches: " << verifiedMatches.load() << " | "
              << "Work units: " << checkpoint.getCompletedWorkUnits()
              << std::flush;
}

void BloomSearch::SaveCheckpoint() {
    std::lock_guard<std::mutex> lock(checkpointMutex);
    checkpoint.save();
    std::cout << "\nCheckpoint saved." << std::endl;
}

bool BloomSearch::LoadCheckpoint() {
    return checkpoint.load();
}

void BloomSearch::Search(
    int numCPUThreads,
    std::vector<int>& gpuIds,
    std::vector<int>& gridSizes,
    bool& shouldExit)
{
    endOfSearch = (std::atomic<bool>*)&shouldExit;

    std::vector<std::thread> threads;

    // Start CPU threads
    for (int i = 0; i < numCPUThreads; i++) {
        threads.push_back(std::thread(&BloomSearch::CPUSearchThread, this, i));
    }

    // TODO: Start GPU threads (requires CUDA implementation)
    // For now, GPU support would need additional CUDA kernel integration

    // Statistics and checkpoint thread
    std::thread statsThread([this, &shouldExit]() {
        int saveCounter = 0;
        while (!shouldExit) {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            PrintStats();

            saveCounter++;
            if (saveCounter >= 300) {  // Save every 5 minutes
                SaveCheckpoint();
                saveCounter = 0;
            }
        }
    });

    // Wait for all threads
    for (auto& t : threads) {
        t.join();
    }

    statsThread.join();

    // Final checkpoint save
    SaveCheckpoint();
    std::cout << "\nSearch complete." << std::endl;
    PrintStats();
    std::cout << std::endl;
}

// ============================================================================
// SIGNAL HANDLER
// ============================================================================

static bool g_shouldExit = false;

void signalHandler(int signum) {
    std::cout << "\nInterrupt received, saving checkpoint and exiting..." << std::endl;
    g_shouldExit = true;
}

// ============================================================================
// MAIN
// ============================================================================

void printUsage() {
    std::cout << "BloomSearch - Bitcoin address collision finder\n\n";
    std::cout << "Usage: BloomSearch [options]\n\n";
    std::cout << "Options:\n";
    std::cout << "  -bloom <file>       Bloom filter file (required)\n";
    std::cout << "  -sorted <file>      Sorted hash160 file for verification (required)\n";
    std::cout << "  -checkpoint <file>  Checkpoint file (default: checkpoint.dat)\n";
    std::cout << "  -o <file>           Output file for matches\n";
    std::cout << "  -t <threads>        Number of CPU threads (default: 4)\n";
    std::cout << "  -gpu                Enable GPU (not yet implemented)\n";
    std::cout << "  -gpuId <ids>        GPU IDs to use (comma separated)\n";
    std::cout << "  -g <gridSize>       GPU grid size\n";
    std::cout << "  -seed <string>      Seed for deterministic key generation\n";
    std::cout << "  -compressed         Search compressed keys only\n";
    std::cout << "  -uncompressed       Search uncompressed keys only\n";
    std::cout << "  -h                  Show this help\n";
}

int main(int argc, char* argv[]) {
    std::string bloomFile;
    std::string sortedFile;
    std::string checkpointFile = "checkpoint.dat";
    std::string outputFile = "matches.txt";
    std::string seed;
    int numThreads = 4;
    bool useGPU = false;
    bool searchCompressed = true;
    bool searchUncompressed = true;
    std::vector<int> gpuIds;
    std::vector<int> gridSizes;

    // Parse arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "-bloom" && i + 1 < argc) {
            bloomFile = argv[++i];
        } else if (arg == "-sorted" && i + 1 < argc) {
            sortedFile = argv[++i];
        } else if (arg == "-checkpoint" && i + 1 < argc) {
            checkpointFile = argv[++i];
        } else if (arg == "-o" && i + 1 < argc) {
            outputFile = argv[++i];
        } else if (arg == "-t" && i + 1 < argc) {
            numThreads = std::stoi(argv[++i]);
        } else if (arg == "-seed" && i + 1 < argc) {
            seed = argv[++i];
        } else if (arg == "-gpu") {
            useGPU = true;
        } else if (arg == "-gpuId" && i + 1 < argc) {
            std::string ids = argv[++i];
            std::stringstream ss(ids);
            std::string id;
            while (std::getline(ss, id, ',')) {
                gpuIds.push_back(std::stoi(id));
            }
        } else if (arg == "-g" && i + 1 < argc) {
            gridSizes.push_back(std::stoi(argv[++i]));
        } else if (arg == "-compressed") {
            searchUncompressed = false;
        } else if (arg == "-uncompressed") {
            searchCompressed = false;
        } else if (arg == "-h" || arg == "--help") {
            printUsage();
            return 0;
        }
    }

    if (bloomFile.empty() || sortedFile.empty()) {
        std::cerr << "Error: -bloom and -sorted are required\n";
        printUsage();
        return 1;
    }

    // Setup signal handler
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    // Initialize secp256k1
    Secp256K1* secp = new Secp256K1();
    secp->Init();

    try {
        BloomSearch search(
            secp,
            bloomFile,
            sortedFile,
            checkpointFile,
            searchCompressed,
            searchUncompressed,
            seed,
            outputFile
        );

        search.Search(numThreads, gpuIds, gridSizes, g_shouldExit);
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    delete secp;
    return 0;
}
