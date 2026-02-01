#include <stdio.h>
#include <cuda.h>
#include <cuda_runtime.h>

__global__ void simple_kernel() {
    printf("Hello from thread %d\n", threadIdx.x);
}

int main() {
    printf("CUDA Init Test\n");
    
    cudaError_t err;
    
    // Get device count
    int deviceCount;
    err = cudaGetDeviceCount(&deviceCount);
    printf("Device count: %d (err=%s)\n", deviceCount, cudaGetErrorString(err));
    
    // Get device properties
    cudaDeviceProp prop;
    err = cudaGetDeviceProperties(&prop, 0);
    printf("Device 0: %s\n", prop.name);
    printf("  Compute capability: %d.%d\n", prop.major, prop.minor);
    printf("  Total global memory: %.1f GB\n", prop.totalGlobalMem / 1e9);
    printf("  Max threads per block: %d\n", prop.maxThreadsPerBlock);
    
    // Set device
    err = cudaSetDevice(0);
    printf("cudaSetDevice(0): %s\n", cudaGetErrorString(err));
    
    // Try to set stack size before any allocation
    size_t stackSize = 64 * 1024;
    err = cudaDeviceSetLimit(cudaLimitStackSize, stackSize);
    printf("cudaDeviceSetLimit(stack, 64KB): %s\n", cudaGetErrorString(err));
    
    size_t actualStack;
    cudaDeviceGetLimit(&actualStack, cudaLimitStackSize);
    printf("Actual stack size: %zu bytes\n", actualStack);
    
    // Launch simple kernel
    printf("Launching simple kernel...\n"); fflush(stdout);
    simple_kernel<<<1, 1>>>();
    err = cudaDeviceSynchronize();
    printf("cudaDeviceSynchronize: %s\n", cudaGetErrorString(err));
    
    // Check for any errors
    err = cudaGetLastError();
    printf("cudaGetLastError: %s\n", cudaGetErrorString(err));
    
    return 0;
}
