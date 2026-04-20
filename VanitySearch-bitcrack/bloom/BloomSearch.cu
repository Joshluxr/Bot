/*
 * BloomSearch.cu - GPU bloom filter search for Bitcoin addresses
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <time.h>
#include <signal.h>

#include "GPU/GPUGroup.h"
#include "GPU/GPUMath.h"
#include "GPU/GPUHash.h"
#include "GPU/GPUBloom.h"
#include "GPU/GPUComputeBloom.h"

#define NB_THREAD_PER_GROUP 512
#define MAX_FOUND 65536

volatile bool running = true;
void sighandler(int s) { running = false; printf("\nStopping...\n"); }

__global__ void bloom_kernel(
    uint32_t mode, uint64_t* keys,
    uint8_t* bloomFilter, uint64_t bloomBits,
    uint32_t* bloomSeeds, int bloomHashes,
    uint32_t maxFound, uint32_t* found
) {
    int xPtr = (blockIdx.x * blockDim.x) * 8;
    int yPtr = xPtr + 4 * NB_THREAD_PER_GROUP;
    ComputeKeysBloom(mode, keys + xPtr, keys + yPtr,
        bloomFilter, bloomBits, bloomSeeds, bloomHashes, maxFound, found);
}

int main(int argc, char** argv) {
    char* bloomFile = NULL;
    char* seedsFile = NULL;
    uint64_t bloomBits = 0;
    int gpuId = 0;
    int numHashes = 20;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-bloom") && i+1 < argc) bloomFile = argv[++i];
        else if (!strcmp(argv[i], "-seeds") && i+1 < argc) seedsFile = argv[++i];
        else if (!strcmp(argv[i], "-bits") && i+1 < argc) bloomBits = strtoull(argv[++i], NULL, 10);
        else if (!strcmp(argv[i], "-gpu") && i+1 < argc) gpuId = atoi(argv[++i]);
        else if (!strcmp(argv[i], "-hashes") && i+1 < argc) numHashes = atoi(argv[++i]);
    }

    if (!bloomFile || !seedsFile || !bloomBits) {
        printf("Usage: %s -bloom <file> -seeds <file> -bits <n> [-gpu <id>]\n", argv[0]);
        return 1;
    }

    signal(SIGINT, sighandler);
    cudaSetDevice(gpuId);
    
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, gpuId);
    printf("GPU %d: %s (SM %d.%d)\n", gpuId, prop.name, prop.major, prop.minor);

    uint64_t bloomBytes = (bloomBits + 7) / 8;
    printf("Loading bloom: %llu bits (%.1f MB)\n", (unsigned long long)bloomBits, bloomBytes/1e6);

    uint8_t* h_bloom = (uint8_t*)malloc(bloomBytes);
    FILE* f = fopen(bloomFile, "rb");
    fread(h_bloom, 1, bloomBytes, f);
    fclose(f);

    uint32_t* h_seeds = (uint32_t*)malloc(numHashes * 4);
    f = fopen(seedsFile, "rb");
    fread(h_seeds, 4, numHashes, f);
    fclose(f);

    int nbThread = 65536;
    uint8_t* d_bloom; uint32_t* d_seeds; uint64_t* d_keys; uint32_t* d_found;
    
    cudaMalloc(&d_bloom, bloomBytes);
    cudaMalloc(&d_seeds, numHashes * 4);
    cudaMalloc(&d_keys, nbThread * 64);
    cudaMalloc(&d_found, (1 + MAX_FOUND * 8) * 4);
    
    cudaMemcpy(d_bloom, h_bloom, bloomBytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_seeds, h_seeds, numHashes * 4, cudaMemcpyHostToDevice);

    uint64_t* h_keys = (uint64_t*)malloc(nbThread * 64);
    srand(time(NULL) ^ gpuId);
    for (int i = 0; i < nbThread * 8; i++)
        h_keys[i] = ((uint64_t)rand() << 32) | rand();
    cudaMemcpy(d_keys, h_keys, nbThread * 64, cudaMemcpyHostToDevice);

    uint32_t* h_found;
    cudaMallocHost(&h_found, (1 + MAX_FOUND * 8) * 4);

    printf("Starting search (%d threads, %d keys/iter)...\n", nbThread, nbThread * 1024);
    
    time_t start = time(NULL);
    uint64_t total = 0, iter = 0;

    while (running) {
        cudaMemset(d_found, 0, 4);
        bloom_kernel<<<nbThread/NB_THREAD_PER_GROUP, NB_THREAD_PER_GROUP>>>(
            0, d_keys, d_bloom, bloomBits, d_seeds, numHashes, MAX_FOUND, d_found);
        cudaDeviceSynchronize();

        cudaMemcpy(h_found, d_found, 4, cudaMemcpyDeviceToHost);
        if (h_found[0] > 0) {
            printf("\n*** %u POTENTIAL MATCHES ***\n", h_found[0]);
            cudaMemcpy(h_found, d_found, (1 + h_found[0] * 8) * 4, cudaMemcpyDeviceToHost);
            FILE* mf = fopen("matches.txt", "a");
            for (uint32_t i = 0; i < h_found[0] && i < 100; i++) {
                uint8_t* hash = (uint8_t*)(h_found + 1 + i*8 + 2);
                printf("  ");
                for (int j = 0; j < 20; j++) printf("%02x", hash[j]);
                printf("\n");
                if (mf) {
                    for (int j = 0; j < 20; j++) fprintf(mf, "%02x", hash[j]);
                    fprintf(mf, "\n");
                }
            }
            if (mf) fclose(mf);
        }

        total += nbThread * 1024;
        if (++iter % 50 == 0) {
            double t = difftime(time(NULL), start);
            printf("\r[%.0fs] %.2fB keys | %.2f MKey/s     ", t, total/1e9, total/t/1e6);
            fflush(stdout);
        }
    }

    printf("\nTotal: %.2f billion keys\n", total/1e9);
    return 0;
}
