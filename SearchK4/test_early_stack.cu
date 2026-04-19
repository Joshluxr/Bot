#include <stdio.h>
#include <cuda.h>
#include <cuda_runtime.h>

// Set stack size using __attribute__((constructor)) before anything else
__attribute__((constructor))
static void init_cuda_stack() {
    cudaError_t err = cudaDeviceSetLimit(cudaLimitStackSize, 128 * 1024);
    size_t stackSize;
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("[constructor] Stack set to %zu bytes (err=%s)\n", stackSize, cudaGetErrorString(err));
}

#include <stdint.h>
#include <string.h>

// Now include GPU headers that have __device__ __constant__ arrays
#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

__global__ void test_kernel() {
    if (threadIdx.x == 0 && blockIdx.x == 0) {
        printf("Kernel running, Gx[0][0] = %lu\n", Gx[0][0]);
    }
}

int main() {
    printf("=== Early Stack Test ===\n");
    
    size_t stackSize;
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("Stack in main(): %zu bytes\n", stackSize);
    
    // Try setting again
    cudaError_t err = cudaDeviceSetLimit(cudaLimitStackSize, 128 * 1024);
    printf("cudaDeviceSetLimit in main: %s\n", cudaGetErrorString(err));
    
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("Stack after set: %zu bytes\n", stackSize);
    
    test_kernel<<<1, 64>>>();
    cudaDeviceSynchronize();
    
    err = cudaGetLastError();
    printf("Kernel result: %s\n", cudaGetErrorString(err));
    
    return 0;
}
