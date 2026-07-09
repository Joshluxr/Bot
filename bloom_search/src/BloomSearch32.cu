/*
 * BloomSearch32.cu - Search with 32-bit prefix table (512MB) + bloom filter
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

#include "GPU/GPUGroup.h"
#include "GPU/GPUMath.h"
#include "GPU/GPUHash.h"
#include "GPU/GPUBloomPrefix32.h"

#define NB_THREAD_PER_GROUP 512
#define MAX_FOUND 65536
#define SEARCH_COMPRESSED 0
#define P2PKH 0
#define STEP_SIZE 1024

volatile bool running = true;
void sighandler(int s) { running = false; printf("\nStopping...\n"); }

#define CHECK_BLOOM32(_h, incr, endo, mode) \
    CheckPointBloomPrefix32(_h, incr, endo, mode, prefixTable32, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out, P2PKH)

__device__ __noinline__ void CheckHashComp32(
    uint64_t* px, uint8_t isOdd, int32_t incr,
    const uint8_t* __restrict__ prefixTable32,
    const uint32_t* __restrict__ bloomFilter, uint64_t bloomBits,
    const uint32_t* __restrict__ bloomSeeds, int bloomHashes,
    uint32_t maxFound, uint32_t* out
) {
    uint32_t h[5];
    _GetHash160Comp(px, isOdd, (uint8_t*)h);
    CHECK_BLOOM32(h, incr, 0, true);
}

__device__ void ComputeKeys32(
    uint32_t mode, uint64_t* startx, uint64_t* starty,
    const uint8_t* __restrict__ prefixTable32,
    const uint32_t* __restrict__ bloomFilter, uint64_t bloomBits,
    const uint32_t* __restrict__ bloomSeeds, int bloomHashes,
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
        
        CheckHashComp32(px, (uint8_t)(py[0] & 1), j*GRP_SIZE + GRP_SIZE/2,
            prefixTable32, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);
        
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
            CheckHashComp32(px, (uint8_t)(py[0] & 1), j*GRP_SIZE + GRP_SIZE/2 + (i+1),
                prefixTable32, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);

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
            CheckHashComp32(px, (uint8_t)(py[0] & 1), j*GRP_SIZE + GRP_SIZE/2 - (i+1),
                prefixTable32, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);
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
        CheckHashComp32(px, (uint8_t)(py[0] & 1), j*GRP_SIZE,
            prefixTable32, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, out);

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

__global__ void bloom_kernel_32(
    uint32_t mode, uint64_t* keys,
    const uint8_t* __restrict__ prefixTable32,
    const uint32_t* __restrict__ bloomFilter, uint64_t bloomBits,
    const uint32_t* __restrict__ bloomSeeds, int bloomHashes,
    uint32_t maxFound, uint32_t* found
) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    ComputeKeys32(mode, keys + xPtr, keys + yPtr,
        prefixTable32, bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, found);
}

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

int main(int argc, char** argv) {
    char* bloomFile = NULL;
    char* seedsFile = NULL;
    char* prefixFile = NULL;
    char* stateFile = NULL;
    uint64_t bloomBits = 0;
    int gpuId = 0;
    int numHashes = 8;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-bloom") && i+1 < argc) bloomFile = argv[++i];
        else if (!strcmp(argv[i], "-seeds") && i+1 < argc) seedsFile = argv[++i];
        else if (!strcmp(argv[i], "-prefix") && i+1 < argc) prefixFile = argv[++i];
        else if (!strcmp(argv[i], "-bits") && i+1 < argc) bloomBits = strtoull(argv[++i], NULL, 10);
        else if (!strcmp(argv[i], "-gpu") && i+1 < argc) gpuId = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-hashes") && i+1 < argc) numHashes = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-state") && i+1 < argc) stateFile = argv[++i];
    }

    if (!bloomFile || !seedsFile || !prefixFile || !bloomBits) {
        printf("Usage: %s -bloom <file> -seeds <file> -prefix <file> -bits <n> [-gpu <id>] [-state <file>]\n", argv[0]);
        return 1;
    }

    char defaultState[256];
    if (!stateFile) { snprintf(defaultState, 256, "/root/gpu%d.state", gpuId); stateFile = defaultState; }

    signal(SIGINT, sighandler);
    signal(SIGTERM, sighandler);
    cudaSetDevice(gpuId);
    
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, gpuId);
    printf("GPU %d: %s (SM %d.%d)\n", gpuId, prop.name, prop.major, prop.minor);

    // Check prefix file size
    struct stat st;
    stat(prefixFile, &st);
    size_t prefixSize = st.st_size;
    printf("Loading: prefix32 (%.0f MB) + bloom (%.1f MB)\n", prefixSize/1e6, (bloomBits+7)/8/1e6);

    // Load 32-bit prefix table (512MB)
    uint8_t* h_prefix = (uint8_t*)malloc(prefixSize);
    FILE* f = fopen(prefixFile, "rb");
    fread(h_prefix, 1, prefixSize, f);
    fclose(f);

    // Load bloom filter
    uint64_t bloomBytes = (bloomBits + 7) / 8;
    uint32_t* h_bloom = (uint32_t*)malloc(bloomBytes);
    f = fopen(bloomFile, "rb");
    fread(h_bloom, 1, bloomBytes, f);
    fclose(f);

    // Load seeds
    uint32_t* h_seeds = (uint32_t*)malloc(numHashes * 4);
    f = fopen(seedsFile, "rb");
    fread(h_seeds, 4, numHashes, f);
    fclose(f);

    int nbThread = 65536;
    uint8_t* d_prefix;
    uint32_t* d_bloom;
    uint32_t* d_seeds;
    uint64_t* d_keys;
    uint32_t* d_found;
    
    cudaMalloc(&d_prefix, prefixSize);
    cudaMalloc(&d_bloom, bloomBytes);
    cudaMalloc(&d_seeds, numHashes * 4);
    cudaMalloc(&d_keys, nbThread * 64);
    cudaMalloc(&d_found, (1 + MAX_FOUND * 8) * 4);
    
    cudaMemcpy(d_prefix, h_prefix, prefixSize, cudaMemcpyHostToDevice);
    cudaMemcpy(d_bloom, h_bloom, bloomBytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_seeds, h_seeds, numHashes * 4, cudaMemcpyHostToDevice);

    uint64_t* h_keys = (uint64_t*)malloc(nbThread * 64);
    uint64_t resumedKeys = load_state(stateFile, h_keys, nbThread);
    if (resumedKeys > 0) {
        printf("Resumed: %.2fB keys\n", resumedKeys/1e9);
    } else {
        printf("Fresh start\n");
        secure_random(h_keys, nbThread * 64);
    }
    cudaMemcpy(d_keys, h_keys, nbThread * 64, cudaMemcpyHostToDevice);

    uint32_t* h_found;
    cudaMallocHost(&h_found, (1 + MAX_FOUND * 8) * 4);

    printf("Starting search (%d threads)...\n", nbThread);
    
    time_t start = time(NULL);
    uint64_t total = resumedKeys, iter = 0;

    while (running) {
        cudaMemset(d_found, 0, 4);
        bloom_kernel_32<<<nbThread/NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP>>>(
            SEARCH_COMPRESSED, d_keys, d_prefix, d_bloom, bloomBits, d_seeds, numHashes, MAX_FOUND, d_found);
        cudaDeviceSynchronize();

        cudaMemcpy(h_found, d_found, 4, cudaMemcpyDeviceToHost);
        if (h_found[0] > 0) {
            cudaMemcpy(h_found, d_found, (1 + h_found[0] * 8) * 4, cudaMemcpyDeviceToHost);
            FILE* mf = fopen("matches.txt", "a");
            for (uint32_t i = 0; i < h_found[0] && i < 100; i++) {
                uint32_t* hash = h_found + 3 + i*8;
                fprintf(mf, "GPU%d: ", gpuId);
                // Print as big-endian hex (Bitcoin format)
                for (int w = 0; w < 5; w++) {
                    fprintf(mf, "%08x", __builtin_bswap32(hash[w]));
                }
                fprintf(mf, "\n");
            }
            fclose(mf);
            printf("\n[!] %u potential matches - check matches.txt\n", h_found[0]);
        }

        total += nbThread * 1024;
        iter++;
        
        if (iter % 500 == 0) {
            cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
            save_state(stateFile, h_keys, nbThread, total);
        }
        
        if (iter % 50 == 0) {
            double t = difftime(time(NULL), start);
            double session = total - resumedKeys;
            printf("\r[%.0fs] %.2fB keys | %.2f MKey/s     ", t, total/1e9, session/t/1e6);
            fflush(stdout);
        }
    }

    printf("\nSaving state...\n");
    cudaMemcpy(h_keys, d_keys, nbThread * 64, cudaMemcpyDeviceToHost);
    save_state(stateFile, h_keys, nbThread, total);
    printf("Total: %.2fB keys\n", total/1e9);
    return 0;
}
