# Bloom Filter Bitcoin Address Search
CUDA = /usr/local/cuda
NVCC = $(CUDA)/bin/nvcc
CXX = g++
CCAP = 89

CXXFLAGS = -O2 -std=c++17 -pthread -I$(CUDA)/include
NVCCFLAGS = -O2 -std=c++17 -gencode=arch=compute_$(CCAP),code=sm_$(CCAP) --compiler-options -fPIC -I.
LDFLAGS = -L$(CUDA)/lib64 -lcudart -lpthread

all: bloom_gpu_search bloom_search test_bloom BloomSearch32K1

bloom_gpu_search: bloom_gpu_search.cu GPUGroup.h GPUMath.h GPUHash.h
	$(NVCC) $(NVCCFLAGS) -o bloom_gpu_search bloom_gpu_search.cu $(LDFLAGS)

# K1-Optimized version with three-tier bloom filter and cached endomorphism
BloomSearch32K1: src/BloomSearch32K1.cu GPUGroup.h GPUMath.h GPUHash.h
	$(NVCC) $(NVCCFLAGS) -o BloomSearch32K1 src/BloomSearch32K1.cu $(LDFLAGS)

# Original silent version
BloomSearch32Silent: src/BloomSearch32Silent.cu GPUGroup.h GPUMath.h GPUHash.h
	$(NVCC) $(NVCCFLAGS) -I src/GPU -o BloomSearch32Silent src/BloomSearch32Silent.cu $(LDFLAGS)

bloom_search: bloom_search.cpp
	$(CXX) $(CXXFLAGS) -o bloom_search bloom_search.cpp $(LDFLAGS)

test_bloom: test_bloom.cpp
	$(CXX) $(CXXFLAGS) -o test_bloom test_bloom.cpp

clean:
	rm -f bloom_gpu_search bloom_search test_bloom BloomSearch32K1 BloomSearch32Silent *.o

.PHONY: all clean
