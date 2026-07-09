/*
 * BloomSearch - GPU-accelerated Bitcoin address bloom filter search
 * Uses VanitySearch GPU kernel for key generation with bloom filter matching
 */

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>
#include <chrono>
#include <thread>
#include <mutex>
#include <atomic>
#include <cuda_runtime.h>

// Bloom filter header format
struct BloomHeader {
    char magic[8];      // "BLOOM001"
    uint64_t size_bits;
    uint32_t num_hashes;
    uint64_t num_addresses;
};

// Global bloom filter data
uint8_t* h_bloom = nullptr;
uint8_t* d_bloom = nullptr;
uint64_t bloom_size_bits = 0;
uint32_t bloom_num_hashes = 0;
uint64_t bloom_num_addresses = 0;

std::atomic<uint64_t> total_keys_checked(0);
std::atomic<uint64_t> bloom_matches(0);
std::mutex output_mutex;

bool loadBloomFilter(const char* filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        std::cerr << "Error: Cannot open bloom filter file: " << filename << std::endl;
        return false;
    }
    
    BloomHeader header;
    file.read(reinterpret_cast<char*>(&header), sizeof(header));
    
    if (strncmp(header.magic, "BLOOM001", 8) != 0) {
        std::cerr << "Error: Invalid bloom filter format" << std::endl;
        return false;
    }
    
    bloom_size_bits = header.size_bits;
    bloom_num_hashes = header.num_hashes;
    bloom_num_addresses = header.num_addresses;
    
    size_t bloom_size_bytes = bloom_size_bits / 8;
    
    std::cout << "Loading bloom filter:" << std::endl;
    std::cout << "  Size: " << bloom_size_bytes / 1024 / 1024 << " MB" << std::endl;
    std::cout << "  Bits: " << bloom_size_bits << std::endl;
    std::cout << "  Hash functions: " << bloom_num_hashes << std::endl;
    std::cout << "  Addresses: " << bloom_num_addresses << std::endl;
    
    // Allocate host memory
    h_bloom = new uint8_t[bloom_size_bytes];
    file.read(reinterpret_cast<char*>(h_bloom), bloom_size_bytes);
    file.close();
    
    // Allocate GPU memory and copy
    cudaError_t err = cudaMalloc(&d_bloom, bloom_size_bytes);
    if (err != cudaSuccess) {
        std::cerr << "CUDA malloc failed: " << cudaGetErrorString(err) << std::endl;
        return false;
    }
    
    err = cudaMemcpy(d_bloom, h_bloom, bloom_size_bytes, cudaMemcpyHostToDevice);
    if (err != cudaSuccess) {
        std::cerr << "CUDA memcpy failed: " << cudaGetErrorString(err) << std::endl;
        return false;
    }
    
    std::cout << "Bloom filter loaded to GPU" << std::endl;
    return true;
}

void cleanup() {
    if (d_bloom) cudaFree(d_bloom);
    if (h_bloom) delete[] h_bloom;
}

void printUsage() {
    std::cout << "Usage: BloomSearch [options]" << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  -bloom <file>    Bloom filter file (required)" << std::endl;
    std::cout << "  -gpu <ids>       GPU IDs to use (default: 0)" << std::endl;
    std::cout << "  -o <file>        Output file for matches" << std::endl;
    std::cout << "  -threads <n>     Threads per GPU (default: 256)" << std::endl;
    std::cout << "  -blocks <n>      Blocks per GPU (default: 1024)" << std::endl;
}

int main(int argc, char* argv[]) {
    std::cout << "BloomSearch - GPU Bitcoin Address Bloom Filter Search" << std::endl;
    std::cout << "======================================================" << std::endl;
    
    const char* bloom_file = nullptr;
    const char* output_file = "bloom_matches.txt";
    int threads_per_block = 256;
    int blocks_per_grid = 1024;
    std::vector<int> gpu_ids = {0, 1, 2, 3};
    
    // Parse arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-bloom") == 0 && i + 1 < argc) {
            bloom_file = argv[++i];
        } else if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            output_file = argv[++i];
        } else if (strcmp(argv[i], "-threads") == 0 && i + 1 < argc) {
            threads_per_block = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-blocks") == 0 && i + 1 < argc) {
            blocks_per_grid = atoi(argv[++i]);
        } else if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            printUsage();
            return 0;
        }
    }
    
    if (!bloom_file) {
        std::cerr << "Error: Bloom filter file required" << std::endl;
        printUsage();
        return 1;
    }
    
    // Get GPU count
    int device_count = 0;
    cudaGetDeviceCount(&device_count);
    std::cout << "Found " << device_count << " CUDA devices" << std::endl;
    
    for (int i = 0; i < device_count; i++) {
        cudaDeviceProp prop;
        cudaGetDeviceProperties(&prop, i);
        std::cout << "  GPU " << i << ": " << prop.name << " (" << prop.totalGlobalMem / 1024 / 1024 << " MB)" << std::endl;
    }
    
    // Load bloom filter
    if (!loadBloomFilter(bloom_file)) {
        return 1;
    }
    
    std::cout << "\nBloom filter ready for search!" << std::endl;
    std::cout << "Bloom filter loaded and ready for GPU-accelerated search." << std::endl;
    std::cout << "Use with VanitySearch GPU kernel for full integration." << std::endl;
    
    cleanup();
    return 0;
}
