// Test stack size requirements
#include <stdio.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>

#define GRP_SIZE 1024
#define NB_THREAD_PER_GROUP 64

__global__ void test_stack() {
    // Allocate the same as ComputeKeysK4
    uint64_t dx[GRP_SIZE/2+1][4];  // 16416 bytes
    uint64_t px[4], py[4], pyn[4], sx[4], sy[4], dy[4], _s[4], _p2[4];  // 256 bytes
    // Total: ~16.7 KB per thread
    
    // Just write to arrays to prevent optimization
    dx[0][0] = threadIdx.x;
    dx[512][0] = blockIdx.x;
    px[0] = 1;
    
    if (threadIdx.x == 0 && blockIdx.x == 0) {
        printf("Thread 0 stack test: dx[0]=%lu, dx[512]=%lu, px[0]=%lu\n", 
               dx[0][0], dx[512][0], px[0]);
    }
}

int main() {
    printf("Testing stack requirements\n");
    
    size_t stackSize;
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("Current stack size limit: %zu bytes per thread\n", stackSize);
    
    // Set very large stack
    cudaDeviceSetLimit(cudaLimitStackSize, 128 * 1024);  // 128KB
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("New stack size limit: %zu bytes per thread\n", stackSize);
    
    printf("Launching test...\n"); fflush(stdout);
    test_stack<<<1, 64>>>();
    cudaDeviceSynchronize();
    
    cudaError_t err = cudaGetLastError();
    if (err != cudaSuccess) {
        printf("CUDA Error: %s\n", cudaGetErrorString(err));
    } else {
        printf("Test complete!\n");
    }
    
    return 0;
}
