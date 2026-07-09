#include <cmath>
/*
 * Test bloom filter and prefix bitmap functionality
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

// MurmurHash3-like hash (same as in build_filters.py)
uint32_t murmurhash3(const uint8_t *data, int len, uint32_t seed) {
    uint32_t h = seed;
    for (int i = 0; i < len; i += 4) {
        uint32_t k = 0;
        for (int j = 0; j < 4 && i + j < len; j++) {
            k |= ((uint32_t)data[i + j]) << (j * 8);
        }
        k *= 0xcc9e2d51;
        k = (k << 15) | (k >> 17);
        k *= 0x1b873593;
        h ^= k;
        h = (h << 13) | (h >> 19);
        h = h * 5 + 0xe6546b64;
    }
    h ^= len;
    h ^= h >> 16;
    h *= 0x85ebca6b;
    h ^= h >> 13;
    h *= 0xc2b2ae35;
    h ^= h >> 16;
    return h;
}

// Simple bloom filter for testing
class BloomFilter {
public:
    uint8_t *bits;
    uint64_t size;
    uint32_t numHashes;
    
    BloomFilter(uint64_t sz, uint32_t nh) : size(sz), numHashes(nh) {
        bits = (uint8_t *)calloc((size + 7) / 8, 1);
    }
    
    void add(const uint8_t *data, int len) {
        for (uint32_t i = 0; i < numHashes; i++) {
            uint64_t h = murmurhash3(data, len, i * 0x9e3779b9) % size;
            bits[h / 8] |= (1 << (h % 8));
        }
    }
    
    bool contains(const uint8_t *data, int len) {
        for (uint32_t i = 0; i < numHashes; i++) {
            uint64_t h = murmurhash3(data, len, i * 0x9e3779b9) % size;
            if (!(bits[h / 8] & (1 << (h % 8)))) return false;
        }
        return true;
    }
};

int main() {
    printf("Testing bloom filter and prefix bitmap...\n\n");
    
    // Test bloom filter
    const int NUM_ITEMS = 1000000;  // 1M items
    const double FP_RATE = 0.003;   // 0.3%
    
    // Calculate optimal size
    uint64_t bloomSize = (uint64_t)(-NUM_ITEMS * log(FP_RATE) / (log(2) * log(2)));
    bloomSize = ((bloomSize + 63) / 64) * 64;
    uint32_t numHashes = (uint32_t)((bloomSize / NUM_ITEMS) * log(2));
    if (numHashes < 1) numHashes = 1;
    if (numHashes > 16) numHashes = 16;
    
    printf("Bloom filter config:\n");
    printf("  Items: %d\n", NUM_ITEMS);
    printf("  Size: %lu bits (%.2f MB)\n", bloomSize, bloomSize / 8.0 / 1024 / 1024);
    printf("  Hashes: %u\n", numHashes);
    printf("  Expected FP rate: %.4f%%\n\n", FP_RATE * 100);
    
    BloomFilter bloom(bloomSize, numHashes);
    
    // Add random items
    printf("Adding %d random items...\n", NUM_ITEMS);
    srand(12345);
    
    uint8_t **items = (uint8_t **)malloc(NUM_ITEMS * sizeof(uint8_t *));
    for (int i = 0; i < NUM_ITEMS; i++) {
        items[i] = (uint8_t *)malloc(20);
        for (int j = 0; j < 20; j++) {
            items[i][j] = rand() & 0xff;
        }
        bloom.add(items[i], 20);
    }
    
    // Verify all items are found
    printf("Verifying all items are found...\n");
    int misses = 0;
    for (int i = 0; i < NUM_ITEMS; i++) {
        if (!bloom.contains(items[i], 20)) misses++;
    }
    printf("  Misses: %d (should be 0)\n\n", misses);
    
    // Test false positive rate
    printf("Testing false positive rate with %d random queries...\n", NUM_ITEMS);
    int falsePositives = 0;
    for (int i = 0; i < NUM_ITEMS; i++) {
        uint8_t query[20];
        for (int j = 0; j < 20; j++) {
            query[j] = rand() & 0xff;
        }
        if (bloom.contains(query, 20)) falsePositives++;
    }
    double actualFP = 100.0 * falsePositives / NUM_ITEMS;
    printf("  False positives: %d (%.4f%%)\n", falsePositives, actualFP);
    printf("  Expected: %.4f%%\n\n", FP_RATE * 100);
    
    // Test prefix bitmap concept
    printf("Testing 32-bit prefix bitmap...\n");
    uint8_t *prefixBitmap = (uint8_t *)calloc(512 * 1024 * 1024, 1);  // 512 MB
    
    // Set bits for our items
    for (int i = 0; i < NUM_ITEMS; i++) {
        uint32_t prefix = ((uint32_t)items[i][0] << 24) | 
                         ((uint32_t)items[i][1] << 16) |
                         ((uint32_t)items[i][2] << 8) |
                         ((uint32_t)items[i][3]);
        prefixBitmap[prefix / 8] |= (1 << (prefix % 8));
    }
    
    // Count bits set
    uint64_t bitsSet = 0;
    for (size_t i = 0; i < 512 * 1024 * 1024; i++) {
        bitsSet += __builtin_popcount(prefixBitmap[i]);
    }
    double coverage = 100.0 * bitsSet / (512.0 * 1024 * 1024 * 8);
    
    printf("  Bits set: %lu\n", bitsSet);
    printf("  Coverage: %.6f%%\n", coverage);
    printf("  Rejection rate: %.6f%%\n\n", 100 - coverage);
    
    // Test rejection
    printf("Testing prefix rejection with random queries...\n");
    int prefixPasses = 0;
    for (int i = 0; i < NUM_ITEMS; i++) {
        uint8_t query[20];
        for (int j = 0; j < 20; j++) {
            query[j] = rand() & 0xff;
        }
        uint32_t prefix = ((uint32_t)query[0] << 24) | 
                         ((uint32_t)query[1] << 16) |
                         ((uint32_t)query[2] << 8) |
                         ((uint32_t)query[3]);
        if (prefixBitmap[prefix / 8] & (1 << (prefix % 8))) {
            prefixPasses++;
        }
    }
    printf("  Prefix passes: %d (%.4f%%)\n", prefixPasses, 100.0 * prefixPasses / NUM_ITEMS);
    printf("  Expected ~%.4f%% based on coverage\n\n", coverage);
    
    // Clean up
    for (int i = 0; i < NUM_ITEMS; i++) free(items[i]);
    free(items);
    free(prefixBitmap);
    
    printf("Tests complete!\n");
    return 0;
}
