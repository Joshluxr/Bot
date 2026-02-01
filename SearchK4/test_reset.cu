#include <stdio.h>
#include <cuda.h>
#include <cuda_runtime.h>
#include <stdint.h>
#include <string.h>

#include "GPUGroup.h"
#include "GPUMath.h"
#include "GPUHash.h"

__global__ void test_kernel() {
    if (threadIdx.x == 0 && blockIdx.x == 0) {
        printf("Kernel running OK, Gx[0][0] = %lu\n", Gx[0][0]);
    }
}

int main() {
    printf("=== Reset Test ===\n");
    
    // Check initial state
    size_t stackSize;
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("Initial stack: %zu bytes\n", stackSize);
    
    // Reset the device to destroy the context
    printf("Resetting device...\n"); fflush(stdout);
    cudaDeviceReset();
    
    // Now set the stack size
    cudaError_t err = cudaDeviceSetLimit(cudaLimitStackSize, 128 * 1024);
    printf("cudaDeviceSetLimit after reset: %s\n", cudaGetErrorString(err));
    
    cudaDeviceGetLimit(&stackSize, cudaLimitStackSize);
    printf("Stack after reset+set: %zu bytes\n", stackSize);
    
    // Launch kernel
    test_kernel<<<1, 64>>>();
    cudaDeviceSynchronize();
    
    err = cudaGetLastError();
    printf("Kernel result: %s\n", cudaGetErrorString(err));
    
    return 0;
}
