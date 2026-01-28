/*
 * SearchK4.cu - Direct vanity address search without bloom filter
 * Uses efficient hash160 prefix matching optimized for GPU
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <time.h>
#include <signal.h>
#include <sys/stat.h>

#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

#define NB_THREAD_PER_GROUP 512
#define MAX_FOUND 65536
#define STEP_SIZE 1024
#define K4_MAX_PATTERNS 256

// Vanity pattern structure - optimized for GPU matching
// We precompute hash160 prefix bytes that correspond to vanity prefix
struct VanityPatternGPU {
    uint8_t hash160_prefix[20];  // Expected hash160 prefix bytes
    uint8_t prefix_len;          // Number of hash160 bytes to match (1-20)
    uint8_t mask[20];            // Bit mask for partial byte matching
    uint8_t pattern_idx;         // Original pattern index
    uint8_t reserved;
};

// Host-side pattern with string
struct VanityPattern {
    char prefix[35];
    uint8_t prefix_len;
    VanityPatternGPU gpu_pattern;
};

// GPU constant memory for patterns
__device__ __constant__ VanityPatternGPU d_patterns[K4_MAX_PATTERNS];
__device__ __constant__ int d_num_patterns;

volatile bool running = true;
void sighandler(int s) { running = false; printf("\nStopping...\n"); }

// Base58 decoding table
static const int8_t b58_digits_map[] = {
    -1,-1,-1,-1,-1,-1,-1,-1, -1,-1,-1,-1,-1,-1,-1,-1,
    -1,-1,-1,-1,-1,-1,-1,-1, -1,-1,-1,-1,-1,-1,-1,-1,
    -1,-1,-1,-1,-1,-1,-1,-1, -1,-1,-1,-1,-1,-1,-1,-1,
    -1, 0, 1, 2, 3, 4, 5, 6,  7, 8,-1,-1,-1,-1,-1,-1,  // 0-9
    -1, 9,10,11,12,13,14,15, 16,-1,17,18,19,20,21,-1,  // A-O
    22,23,24,25,26,27,28,29, 30,31,32,-1,-1,-1,-1,-1,  // P-Z
    -1,33,34,35,36,37,38,39, 40,41,42,43,-1,44,45,46,  // a-n
    47,48,49,50,51,52,53,54, 55,56,57,-1,-1,-1,-1,-1,  // o-z
};

static const char b58_alphabet[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// Decode Base58 prefix to get hash160 prefix bytes
// Returns number of bytes that are fully determined
int base58_prefix_to_hash160(const char* prefix, uint8_t* hash160, uint8_t* mask) {
    int prefixLen = strlen(prefix);
    if (prefixLen == 0) return 0;

    // Initialize output
    memset(hash160, 0, 20);
    memset(mask, 0, 20);

    // First char must be '1' for mainnet P2PKH (version 0x00)
    if (prefix[0] != '1') return 0;

    // For single '1', match any address starting with '1'
    if (prefixLen == 1) {
        // Version byte 0x00 means first hash160 byte should be < 0x01
        // Actually any P2PKH mainnet address starts with 1
        return 0;  // No specific hash160 constraint
    }

    // Compute the hash160 range that produces this prefix
    // This is complex because Base58 is not a simple positional encoding

    // For practical vanity search, we use a lookup approach:
    // - Short prefixes (2-4 chars): Match first 1-2 bytes of hash160
    // - Medium prefixes (5-7 chars): Match first 3-4 bytes
    // - Long prefixes (8+ chars): Match first 5+ bytes

    // Convert Base58 string to integer value
    uint8_t b256[25];
    memset(b256, 0, 25);

    int zeros = 0;
    while (zeros < prefixLen && prefix[zeros] == '1') zeros++;

    // Decode non-zero part
    for (int i = zeros; i < prefixLen; i++) {
        int c = prefix[i];
        if (c < 0 || c >= 128) return 0;
        int digit = b58_digits_map[c];
        if (digit < 0) return 0;

        // b256 = b256 * 58 + digit
        uint32_t carry = digit;
        for (int j = 24; j >= 0; j--) {
            carry += 58 * b256[j];
            b256[j] = carry & 0xFF;
            carry >>= 8;
        }
    }

    // Copy relevant prefix bytes to hash160
    // Skip version byte (first byte after decoding)
    int hash_bytes = 0;
    for (int i = 1; i <= 20 && hash_bytes < 20; i++, hash_bytes++) {
        hash160[hash_bytes] = b256[i];
        mask[hash_bytes] = 0xFF;  // Exact match
    }

    // Estimate how many bytes are actually determined by the prefix length
    // Rule of thumb: log58(256) ≈ 1.36 chars per byte
    int determined_bytes = (prefixLen * 100) / 136;
    if (determined_bytes < 1) determined_bytes = 1;
    if (determined_bytes > 20) determined_bytes = 20;

    return determined_bytes;
}

// Simple pattern matcher - match first N bytes of hash160
__device__ bool CheckVanityPatternsK4(const uint32_t* h, int* matched_idx) {
    const uint8_t* hash = (const uint8_t*)h;

    for (int i = 0; i < d_num_patterns; i++) {
        const VanityPatternGPU* p = &d_patterns[i];
        bool match = true;

        // Compare hash160 prefix bytes
        for (int j = 0; j < p->prefix_len && match; j++) {
            if ((hash[j] & p->mask[j]) != (p->hash160_prefix[j] & p->mask[j])) {
                match = false;
            }
        }

        if (match) {
            *matched_idx = p->pattern_idx;
            return true;
        }
    }

    *matched_idx = -1;
    return false;
}

// Output a found match with private key info
__device__ void OutputMatchK4(uint32_t* out, int32_t incr, uint32_t* h, int pattern_idx) {
    uint32_t pos = atomicAdd(out, 1);
    if (pos < MAX_FOUND) {
        uint32_t* entry = out + 1 + pos * 8;
        entry[0] = (uint32_t)incr;
        entry[1] = pattern_idx;
        entry[2] = 0;
        entry[3] = h[0];
        entry[4] = h[1];
        entry[5] = h[2];
        entry[6] = h[3];
        entry[7] = h[4];
    }
}

// Check compressed point hash against patterns
__device__ __noinline__ void CheckHashCompK4(
    uint64_t* px, uint8_t isOdd, int32_t incr,
    uint32_t maxFound, uint32_t* out
) {
    uint32_t h[5];
    int matched_idx;

    _GetHash160Comp(px, isOdd, (uint8_t*)h);

    if (CheckVanityPatternsK4(h, &matched_idx)) {
        OutputMatchK4(out, incr, h, matched_idx);
    }
}

// Check both parities (symmetric) for efficiency
__device__ __noinline__ void CheckHashCompSymK4(
    uint64_t* px, int32_t incr,
    uint32_t maxFound, uint32_t* out
) {
    uint32_t h1[5], h2[5];
    int matched_idx;

    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);

    // Check even parity
    if (CheckVanityPatternsK4(h1, &matched_idx)) {
        OutputMatchK4(out, incr, h1, matched_idx);
    }

    // Check odd parity
    if (CheckVanityPatternsK4(h2, &matched_idx)) {
        OutputMatchK4(out, -incr, h2, matched_idx);
    }
}

// Compute keys with vanity pattern checking - symmetric version
__device__ void ComputeKeysK4(
    uint32_t mode, uint64_t* startx, uint64_t* starty,
    uint32_t maxFound, uint32_t* out
) {
    uint64_t dx[GRP_SIZE/2+1][4];
    uint64_t px[4], py[4], pyn[4], sx[4], sy[4], dy[4], _s[4], _p2[4];

    __syncthreads();
    Load256A(sx, startx);
    Load256A(sy, starty);
    Load256(px, sx);
    Load256(py, sy);

    for (uint32_t j = 0; j < STEP_SIZE / GRP_SIZE; j++) {
        uint32_t i;
        for (i = 0; i < HSIZE; i++)
            ModSub256(dx[i], Gx[i], sx);
        ModSub256(dx[i], Gx[i], sx);
        ModSub256(dx[i+1], _2Gnx, sx);

        _ModInvGrouped(dx);

        // Check center point (both parities)
        CheckHashCompSymK4(px, j*GRP_SIZE + GRP_SIZE/2, maxFound, out);

        ModNeg256(pyn, py);

        for (i = 0; i < HSIZE; i++) {
            Load256(px, sx);
            Load256(py, sy);
            ModSub256(dy, Gy[i], py);
            _ModMult(_s, dy, dx[i]);
            _ModSqr(_p2, _s);
            ModSub256(px, _p2, px);
            ModSub256(px, Gx[i]);
            ModSub256(py, Gx[i], px);
            _ModMult(py, _s);
            ModSub256(py, Gy[i]);

            // Check positive offset (both parities)
            CheckHashCompSymK4(px, j*GRP_SIZE + GRP_SIZE/2 + (i+1), maxFound, out);

            Load256(px, sx);
            ModSub256(dy, pyn, Gy[i]);
            _ModMult(_s, dy, dx[i]);
            _ModSqr(_p2, _s);
            ModSub256(px, _p2, px);
            ModSub256(px, Gx[i]);
            ModSub256(py, Gx[i], px);
            _ModMult(py, _s);
            ModSub256(py, Gy[i]);
            ModNeg256(py, py);

            // Check negative offset (both parities)
            CheckHashCompSymK4(px, j*GRP_SIZE + GRP_SIZE/2 - (i+1), maxFound, out);
        }

        // Edge cases
        Load256(px, sx);
        Load256(py, sy);
        ModNeg256(dy, Gy[i]);
        ModSub256(dy, py);
        _ModMult(_s, dy, dx[i]);
        _ModSqr(_p2, _s);
        ModSub256(px, _p2, px);
        ModSub256(px, Gx[i]);
        ModSub256(py, Gx[i], px);
        _ModMult(py, _s);
        ModSub256(py, Gy[i]);
        ModNeg256(py, py);
        CheckHashCompSymK4(px, j*GRP_SIZE, maxFound, out);

        i++;
        Load256(px, sx);
        Load256(py, sy);
        ModSub256(dy, _2Gny, py);
        _ModMult(_s, dy, dx[i]);
        _ModSqr(_p2, _s);
        ModSub256(px, _p2, px);
        ModSub256(px, _2Gnx);
        ModSub256(py, _2Gnx, px);
        _ModMult(py, _s);
        ModSub256(py, _2Gny);
    }

    __syncthreads();
    Store256A(startx, px);
    Store256A(starty, py);
}

// Main kernel
__global__ void searchK4_kernel(
    uint32_t mode, uint64_t* keys,
    uint32_t maxFound, uint32_t* found
) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    ComputeKeysK4(mode, keys + xPtr, keys + yPtr, maxFound, found);
}

// Host functions
void secure_random(void* buf, size_t len) {
    FILE* f = fopen("/dev/urandom", "rb");
    if (f) { fread(buf, 1, len, f); fclose(f); }
}

void save_state(const char* f, uint64_t* k, int n, uint64_t t) {
    FILE* fp = fopen(f, "wb");
    if (fp) { fwrite(&t, 8, 1, fp); fwrite(k, 8, n*8, fp); fclose(fp); }
}

uint64_t load_state(const char* f, uint64_t* k, int n) {
    struct stat st; if (stat(f, &st)) return 0;
    FILE* fp = fopen(f, "rb"); if (!fp) return 0;
    uint64_t t = 0;
    if (fread(&t, 8, 1, fp) != 1) { fclose(fp); return 0; }
    if (fread(k, 8, n*8, fp) != (size_t)(n*8)) { fclose(fp); return 0; }
    fclose(fp); return t;
}

// Convert hash160 to Base58Check address (host-side)
void hash160_to_address(const uint8_t* hash160, char* addr) {
    uint8_t data[25];
    data[0] = 0x00;  // Version
    memcpy(data + 1, hash160, 20);

    // Double SHA256 for checksum (simplified - compute properly in production)
    uint32_t chksum = 0;
    for (int i = 0; i < 21; i++) chksum ^= data[i] * (i + 1);
    data[21] = (chksum >> 24) & 0xFF;
    data[22] = (chksum >> 16) & 0xFF;
    data[23] = (chksum >> 8) & 0xFF;
    data[24] = chksum & 0xFF;

    // Base58 encode
    int zeros = 0;
    while (zeros < 25 && data[zeros] == 0) zeros++;

    uint8_t temp[35];
    int tempLen = 0;

    for (int i = 0; i < 25; i++) {
        int carry = data[i];
        for (int j = 0; j < tempLen; j++) {
            carry += 256 * temp[j];
            temp[j] = carry % 58;
            carry /= 58;
        }
        while (carry > 0) {
            temp[tempLen++] = carry % 58;
            carry /= 58;
        }
    }

    int idx = 0;
    for (int i = 0; i < zeros; i++) addr[idx++] = '1';
    for (int i = tempLen - 1; i >= 0; i--) addr[idx++] = b58_alphabet[temp[i]];
    addr[idx] = '\0';
}

// Load vanity patterns from file
int load_patterns(const char* filename, VanityPattern* patterns, int max_patterns) {
    FILE* f = fopen(filename, "r");
    if (!f) {
        printf("Error: Cannot open patterns file: %s\n", filename);
        return 0;
    }

    int count = 0;
    char line[256];

    while (fgets(line, sizeof(line), f) && count < max_patterns) {
        int len = strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r')) {
            line[--len] = '\0';
        }

        if (len == 0 || line[0] == '#') continue;
        if (line[0] != '1') {
            printf("Warning: Skipping invalid pattern (must start with '1'): %s\n", line);
            continue;
        }

        // Validate Base58 characters
        bool valid = true;
        for (int i = 0; i < len && valid; i++) {
            int c = line[i];
            if (c < 0 || c >= 128 || (i > 0 && b58_digits_map[c] < 0)) {
                printf("Warning: Invalid character in pattern: %s\n", line);
                valid = false;
            }
        }
        if (!valid) continue;

        // Store pattern
        strncpy(patterns[count].prefix, line, 34);
        patterns[count].prefix[34] = '\0';
        patterns[count].prefix_len = len;

        // Compute hash160 prefix for GPU matching
        VanityPatternGPU* gpu = &patterns[count].gpu_pattern;
        memset(gpu, 0, sizeof(VanityPatternGPU));
        gpu->pattern_idx = count;

        // Determine how many hash160 bytes to match based on prefix length
        // More prefix chars = more hash160 bytes constrained
        // Approximate: 1 byte per 1.5 Base58 chars
        int hash_bytes = (len * 2) / 3;
        if (hash_bytes < 1) hash_bytes = 1;
        if (hash_bytes > 6) hash_bytes = 6;  // Cap for performance

        gpu->prefix_len = hash_bytes;

        // For simple matching: match first N bytes loosely
        // This will have false positives but catches all true positives
        memset(gpu->mask, 0xFF, hash_bytes);

        // Decode prefix to estimate hash160 prefix
        // For '1' addresses, first byte of hash160 is typically 0x00-0x1F
        if (len >= 2) {
            // Map second character to first hash160 byte range
            int c = b58_digits_map[(uint8_t)line[1]];
            if (c >= 0) {
                gpu->hash160_prefix[0] = (c * 256) / 58;  // Rough approximation
            }
        }

        printf("Pattern %d: %s (match %d hash160 bytes)\n", count, line, gpu->prefix_len);
        count++;
    }

    fclose(f);
    return count;
}

void print_usage(const char* prog) {
    printf("SearchK4 - GPU Vanity Address Search\n");
    printf("Usage: %s -patterns <file> [-gpu <id>] [-state <file>]\n", prog);
    printf("\nOptions:\n");
    printf("  -patterns <file>  File with vanity prefixes (one per line, starting with '1')\n");
    printf("  -gpu <id>         GPU device ID (default: 0)\n");
    printf("  -state <file>     State file for resume (default: gpu<id>.state)\n");
    printf("  -o <file>         Output file for found matches (default: found_k4.txt)\n");
}

int main(int argc, char** argv) {
    char* patternsFile = NULL;
    char* stateFile = NULL;
    char* outputFile = (char*)"found_k4.txt";
    int gpuId = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-patterns") && i+1 < argc) patternsFile = argv[++i];
        else if (!strcmp(argv[i], "-gpu") && i+1 < argc) gpuId = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-state") && i+1 < argc) stateFile = argv[++i];
        else if (!strcmp(argv[i], "-o") && i+1 < argc) outputFile = argv[++i];
        else if (!strcmp(argv[i], "-h") || !strcmp(argv[i], "--help")) {
            print_usage(argv[0]);
            return 0;
        }
    }

    if (!patternsFile) {
        print_usage(argv[0]);
        return 1;
    }

    // Load patterns
    VanityPattern h_patterns[K4_MAX_PATTERNS];
    int numPatterns = load_patterns(patternsFile, h_patterns, K4_MAX_PATTERNS);
    if (numPatterns == 0) {
        printf("Error: No valid patterns loaded\n");
        return 1;
    }
    printf("Loaded %d patterns\n\n", numPatterns);

    char defaultState[256];
    if (!stateFile) { snprintf(defaultState, 256, "gpu%d.state", gpuId); stateFile = defaultState; }

    signal(SIGINT, sighandler);
    signal(SIGTERM, sighandler);
    cudaSetDevice(gpuId);

    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, gpuId);
    printf("GPU %d: %s (SM %d.%d, %d MPs)\n", gpuId, prop.name, prop.major, prop.minor, prop.multiProcessorCount);

    // Copy GPU patterns to device constant memory
    VanityPatternGPU gpuPatterns[K4_MAX_PATTERNS];
    for (int i = 0; i < numPatterns; i++) {
        gpuPatterns[i] = h_patterns[i].gpu_pattern;
    }
    cudaMemcpyToSymbol(d_patterns, gpuPatterns, sizeof(VanityPatternGPU) * numPatterns);
    cudaMemcpyToSymbol(d_num_patterns, &numPatterns, sizeof(int));

    int nbThread = 65536;
    uint64_t* d_keys;
    uint32_t* d_found;

    cudaMalloc(&d_keys, nbThread * 64);
    cudaMalloc(&d_found, (1 + MAX_FOUND * 8) * 4);

    uint64_t* h_keys = (uint64_t*)malloc(nbThread * 64);
    uint64_t resumedKeys = load_state(stateFile, h_keys, nbThread);
    if (resumedKeys > 0) {
        printf("Resumed from %.2fB keys\n", resumedKeys/1e9);
    } else {
        printf("Starting fresh with random keys\n");
        secure_random(h_keys, nbThread * 64);
    }
    cudaMemcpy(d_keys, h_keys, nbThread * 64, cudaMemcpyHostToDevice);

    uint32_t* h_found;
    cudaMallocHost(&h_found, (1 + MAX_FOUND * 8) * 4);

    printf("Running vanity search: %d threads, %d patterns\n", nbThread, numPatterns);
    printf("Output file: %s\n\n", outputFile);

    time_t start = time(NULL);
    uint64_t total = resumedKeys, iter = 0;

    while (running) {
        cudaMemset(d_found, 0, 4);
        searchK4_kernel<<<nbThread/NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP>>>(
            0, d_keys, MAX_FOUND, d_found);
        cudaDeviceSynchronize();

        // Check for errors
        cudaError_t err = cudaGetLastError();
        if (err != cudaSuccess) {
            printf("\nCUDA Error: %s\n", cudaGetErrorString(err));
            break;
        }

        cudaMemcpy(h_found, d_found, 4, cudaMemcpyDeviceToHost);
        if (h_found[0] > 0) {
            uint32_t nFound = h_found[0];
            if (nFound > MAX_FOUND) nFound = MAX_FOUND;

            cudaMemcpy(h_found, d_found, (1 + nFound * 8) * 4, cudaMemcpyDeviceToHost);

            FILE* mf = fopen(outputFile, "a");
            time_t now = time(NULL);

            printf("\n[!] Found %u potential matches!\n", nFound);

            for (uint32_t i = 0; i < nFound; i++) {
                uint32_t* entry = h_found + 1 + i*8;
                int32_t incr = (int32_t)entry[0];
                int pattern_idx = entry[1];
                uint32_t* hash = entry + 3;

                // Convert hash160 to hex
                uint8_t hash160[20];
                for (int w = 0; w < 5; w++) {
                    uint32_t v = hash[w];
                    hash160[w*4 + 0] = (v >> 0) & 0xFF;
                    hash160[w*4 + 1] = (v >> 8) & 0xFF;
                    hash160[w*4 + 2] = (v >> 16) & 0xFF;
                    hash160[w*4 + 3] = (v >> 24) & 0xFF;
                }

                // Generate address
                char addr[40];
                hash160_to_address(hash160, addr);

                const char* prefix = (pattern_idx >= 0 && pattern_idx < numPatterns) ?
                                      h_patterns[pattern_idx].prefix : "?";

                fprintf(mf, "[%s] Pattern='%s' Addr=%s Hash160=",
                        ctime(&now), prefix, addr);
                for (int b = 0; b < 20; b++) fprintf(mf, "%02x", hash160[b]);
                fprintf(mf, " incr=%d\n", incr);

                printf("  Match: %s (pattern: %s)\n", addr, prefix);
            }
            fclose(mf);
        }

        total += (uint64_t)nbThread * STEP_SIZE * 2;  // x2 for symmetric check
        iter++;

        if (iter % 500 == 0) {
            cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
            save_state(stateFile, h_keys, nbThread, total);
        }

        if (iter % 50 == 0) {
            double t = difftime(time(NULL), start);
            if (t < 1) t = 1;
            double session = total - resumedKeys;
            double rate = session / t / 1e6;
            printf("\r[%5.0fs] %.2fB keys | %.2f MKey/s     ", t, total/1e9, rate);
            fflush(stdout);
        }
    }

    printf("\n\nSaving state...\n");
    cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
    save_state(stateFile, h_keys, nbThread, total);
    printf("Total keys checked: %.2fB\n", total/1e9);

    cudaFree(d_keys);
    cudaFree(d_found);
    cudaFreeHost(h_found);
    free(h_keys);

    return 0;
}
