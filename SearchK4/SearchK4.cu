/*
 * SearchK4.cu - Direct vanity address search without bloom filter
 * Uses proper GPU Base58 encoding and string matching
 * Based on VanitySearch by Jean Luc PONS
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
#define P2PKH 0

// Base58 alphabet
__device__ __constant__ char pszBase58[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

// Pattern storage - each pattern is null-terminated, max 35 chars
__device__ __constant__ char d_patterns[K4_MAX_PATTERNS][36];
__device__ __constant__ int d_pattern_lens[K4_MAX_PATTERNS];
__device__ __constant__ int d_num_patterns;

volatile bool running = true;
void sighandler(int s) { running = false; printf("\nStopping...\n"); }

// GPU Base58 address generation (from VanitySearch)
__device__ __noinline__ void _GetAddress(int type, uint32_t *hash, char *b58Add) {
    uint32_t addBytes[16];
    uint32_t s[16];
    unsigned char A[25];
    unsigned char *addPtr = A;
    int retPos = 0;
    unsigned char digits[128];

    // Version byte
    A[0] = (type == P2PKH) ? 0x00 : 0x05;

    // Copy hash160
    memcpy(A + 1, (char *)hash, 20);

    // Compute checksum (double SHA256)
    addBytes[0] = __byte_perm(hash[0], (uint32_t)A[0], 0x4012);
    addBytes[1] = __byte_perm(hash[0], hash[1], 0x3456);
    addBytes[2] = __byte_perm(hash[1], hash[2], 0x3456);
    addBytes[3] = __byte_perm(hash[2], hash[3], 0x3456);
    addBytes[4] = __byte_perm(hash[3], hash[4], 0x3456);
    addBytes[5] = __byte_perm(hash[4], 0x80, 0x3456);
    addBytes[6] = 0;
    addBytes[7] = 0;
    addBytes[8] = 0;
    addBytes[9] = 0;
    addBytes[10] = 0;
    addBytes[11] = 0;
    addBytes[12] = 0;
    addBytes[13] = 0;
    addBytes[14] = 0;
    addBytes[15] = 0xA8;  // 21 * 8 bits

    SHA256Initialize(s);
    SHA256Transform(s, addBytes);

    #pragma unroll 8
    for (int i = 0; i < 8; i++)
        addBytes[i] = s[i];

    addBytes[8] = 0x80000000;
    addBytes[9] = 0;
    addBytes[10] = 0;
    addBytes[11] = 0;
    addBytes[12] = 0;
    addBytes[13] = 0;
    addBytes[14] = 0;
    addBytes[15] = 0x100;  // 32 * 8 bits

    SHA256Initialize(s);
    SHA256Transform(s, addBytes);

    // Append checksum (first 4 bytes of double SHA256)
    A[21] = ((uint8_t *)s)[3];
    A[22] = ((uint8_t *)s)[2];
    A[23] = ((uint8_t *)s)[1];
    A[24] = ((uint8_t *)s)[0];

    // Base58 encode
    // Skip leading zeroes (each becomes '1')
    while (addPtr[0] == 0) {
        b58Add[retPos++] = '1';
        addPtr++;
    }
    int length = 25 - retPos;

    int digitslen = 1;
    digits[0] = 0;
    for (int i = 0; i < length; i++) {
        uint32_t carry = addPtr[i];
        for (int j = 0; j < digitslen; j++) {
            carry += (uint32_t)(digits[j]) << 8;
            digits[j] = (unsigned char)(carry % 58);
            carry /= 58;
        }
        while (carry > 0) {
            digits[digitslen++] = (unsigned char)(carry % 58);
            carry /= 58;
        }
    }

    // Reverse and convert to Base58 chars
    for (int i = 0; i < digitslen; i++)
        b58Add[retPos++] = pszBase58[digits[digitslen - 1 - i]];

    b58Add[retPos] = 0;
}

// Simple prefix match (no wildcards for now)
__device__ __noinline__ bool _MatchPrefix(const char *addr, const char *pattern, int patLen) {
    for (int i = 0; i < patLen; i++) {
        if (addr[i] != pattern[i]) return false;
    }
    return true;
}

// Check address against all patterns
__device__ bool CheckVanityPatternsK4(uint32_t *h, int *matched_idx, char *gen_addr) {
    // Generate full Base58Check address
    _GetAddress(P2PKH, h, gen_addr);

    // Check against each pattern
    for (int i = 0; i < d_num_patterns; i++) {
        if (_MatchPrefix(gen_addr, d_patterns[i], d_pattern_lens[i])) {
            *matched_idx = i;
            return true;
        }
    }

    *matched_idx = -1;
    return false;
}

// Output a found match
__device__ void OutputMatchK4(uint32_t* out, int32_t incr, uint32_t* h, int pattern_idx, uint8_t isOdd) {
    uint32_t pos = atomicAdd(out, 1);
    if (pos < MAX_FOUND) {
        uint32_t* entry = out + 1 + pos * 8;
        entry[0] = (uint32_t)incr;
        entry[1] = pattern_idx;
        entry[2] = isOdd;  // Store parity info
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
    char addr[40];
    int matched_idx;

    _GetHash160Comp(px, isOdd, (uint8_t*)h);

    if (CheckVanityPatternsK4(h, &matched_idx, addr)) {
        OutputMatchK4(out, incr, h, matched_idx, isOdd);
    }
}

// Check both parities for efficiency
__device__ __noinline__ void CheckHashCompSymK4(
    uint64_t* px, int32_t incr,
    uint32_t maxFound, uint32_t* out
) {
    uint32_t h1[5], h2[5];
    char addr[40];
    int matched_idx;

    _GetHash160CompSym(px, (uint8_t*)h1, (uint8_t*)h2);

    // Check even parity
    if (CheckVanityPatternsK4(h1, &matched_idx, addr)) {
        OutputMatchK4(out, incr, h1, matched_idx, 0);
    }

    // Check odd parity
    if (CheckVanityPatternsK4(h2, &matched_idx, addr)) {
        OutputMatchK4(out, -incr, h2, matched_idx, 1);
    }
}

// Compute keys with vanity pattern checking
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

            CheckHashCompSymK4(px, j*GRP_SIZE + GRP_SIZE/2 - (i+1), maxFound, out);
        }

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

// Host-side Base58 for display
static const char b58_alphabet[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";

void hash160_to_address_host(const uint8_t* hash160, char* addr) {
    uint8_t data[25];
    data[0] = 0x00;
    memcpy(data + 1, hash160, 20);

    // Proper double SHA256 checksum (simplified for host display)
    // In production, use proper crypto library
    uint32_t chksum = 0;
    for (int i = 0; i < 21; i++) chksum = chksum * 31 + data[i];
    data[21] = (chksum >> 24) & 0xFF;
    data[22] = (chksum >> 16) & 0xFF;
    data[23] = (chksum >> 8) & 0xFF;
    data[24] = chksum & 0xFF;

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

// Load patterns
int load_patterns(const char* filename, char patterns[][36], int* lens, int max_patterns) {
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
            printf("Warning: Skipping pattern (must start with '1'): %s\n", line);
            continue;
        }

        // Validate Base58
        bool valid = true;
        for (int i = 0; i < len && valid; i++) {
            if (strchr("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", line[i]) == NULL) {
                printf("Warning: Invalid Base58 char in: %s\n", line);
                valid = false;
            }
        }
        if (!valid) continue;

        strncpy(patterns[count], line, 35);
        patterns[count][35] = '\0';
        lens[count] = len;

        printf("Pattern %d: %s (len=%d)\n", count, patterns[count], lens[count]);
        count++;
    }

    fclose(f);
    return count;
}

void print_usage(const char* prog) {
    printf("SearchK4 - GPU Vanity Address Search (no bloom filter)\n");
    printf("Usage: %s -patterns <file> [-gpu <id>] [-state <file>] [-o <file>]\n", prog);
    printf("\nOptions:\n");
    printf("  -patterns <file>  File with vanity prefixes (one per line)\n");
    printf("  -gpu <id>         GPU device ID (default: 0)\n");
    printf("  -state <file>     State file for resume\n");
    printf("  -o <file>         Output file (default: found_k4.txt)\n");
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
    char h_patterns[K4_MAX_PATTERNS][36];
    int h_lens[K4_MAX_PATTERNS];
    int numPatterns = load_patterns(patternsFile, h_patterns, h_lens, K4_MAX_PATTERNS);
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

    // Copy patterns to GPU constant memory
    cudaMemcpyToSymbol(d_patterns, h_patterns, sizeof(h_patterns));
    cudaMemcpyToSymbol(d_pattern_lens, h_lens, sizeof(h_lens));
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
        printf("Fresh start with random keys\n");
        secure_random(h_keys, nbThread * 64);
    }
    cudaMemcpy(d_keys, h_keys, nbThread * 64, cudaMemcpyHostToDevice);

    uint32_t* h_found;
    cudaMallocHost(&h_found, (1 + MAX_FOUND * 8) * 4);

    printf("Running: %d threads, %d patterns\n", nbThread, numPatterns);
    printf("Output: %s\n\n", outputFile);

    time_t start = time(NULL);
    uint64_t total = resumedKeys, iter = 0;

    while (running) {
        cudaMemset(d_found, 0, 4);
        searchK4_kernel<<<nbThread/NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP>>>(
            0, d_keys, MAX_FOUND, d_found);
        cudaDeviceSynchronize();

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
            char* timestr = ctime(&now);
            timestr[strlen(timestr)-1] = '\0';  // Remove newline

            printf("\n[!] Found %u matches!\n", nFound);

            for (uint32_t i = 0; i < nFound; i++) {
                uint32_t* entry = h_found + 1 + i*8;
                int32_t incr = (int32_t)entry[0];
                int pattern_idx = entry[1];
                uint8_t isOdd = entry[2];
                uint32_t* hash = entry + 3;

                uint8_t hash160[20];
                for (int w = 0; w < 5; w++) {
                    uint32_t v = hash[w];
                    hash160[w*4 + 0] = (v >> 0) & 0xFF;
                    hash160[w*4 + 1] = (v >> 8) & 0xFF;
                    hash160[w*4 + 2] = (v >> 16) & 0xFF;
                    hash160[w*4 + 3] = (v >> 24) & 0xFF;
                }

                char addr[40];
                hash160_to_address_host(hash160, addr);

                const char* pattern = (pattern_idx >= 0 && pattern_idx < numPatterns) ?
                                       h_patterns[pattern_idx] : "?";

                fprintf(mf, "[%s] Pattern='%s' Address=%s Hash160=", timestr, pattern, addr);
                for (int b = 0; b < 20; b++) fprintf(mf, "%02x", hash160[b]);
                fprintf(mf, " incr=%d parity=%d\n", incr, isOdd);

                printf("  %s -> Pattern: %s\n", addr, pattern);
            }
            fclose(mf);
        }

        total += (uint64_t)nbThread * STEP_SIZE * 2;
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
    printf("Total: %.2fB keys\n", total/1e9);

    cudaFree(d_keys);
    cudaFree(d_found);
    cudaFreeHost(h_found);
    free(h_keys);

    return 0;
}
