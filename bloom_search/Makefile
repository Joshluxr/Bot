# BloomSearch Makefile
# Bitcoin address collision finder using bloom filters

# Compiler settings
CXX = g++
NVCC = nvcc

CXXFLAGS = -O3 -march=native -std=c++17 -pthread
NVCCFLAGS = -O3 -arch=sm_89 -std=c++17

# Include paths (adjust for your VanitySearch location)
VANITYSEARCH_DIR = ../vanitysearch_analysis
INCLUDES = -I$(VANITYSEARCH_DIR) -I$(VANITYSEARCH_DIR)/hash

# Libraries
LIBS = -lpthread -lcrypto

# CUDA libraries (if using GPU)
CUDA_LIBS = -lcudart

# Source files
SRCS = BloomSearch.cpp

# Object files from VanitySearch
VANITY_OBJS = $(VANITYSEARCH_DIR)/Int.o \
              $(VANITYSEARCH_DIR)/IntMod.o \
              $(VANITYSEARCH_DIR)/IntGroup.o \
              $(VANITYSEARCH_DIR)/Point.o \
              $(VANITYSEARCH_DIR)/SECP256K1.o \
              $(VANITYSEARCH_DIR)/Random.o \
              $(VANITYSEARCH_DIR)/hash/ripemd160.o \
              $(VANITYSEARCH_DIR)/hash/sha256.o \
              $(VANITYSEARCH_DIR)/hash/sha512.o \
              $(VANITYSEARCH_DIR)/Base58.o

# Targets
all: BloomSearch

BloomSearch: $(SRCS) $(VANITY_OBJS)
	$(CXX) $(CXXFLAGS) $(INCLUDES) -o $@ $(SRCS) $(VANITY_OBJS) $(LIBS)

# Build VanitySearch object files if they don't exist
$(VANITYSEARCH_DIR)/%.o: $(VANITYSEARCH_DIR)/%.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

# GPU version (requires CUDA)
BloomSearchGPU: $(SRCS) GPU/GPUEngine.cu $(VANITY_OBJS)
	$(NVCC) $(NVCCFLAGS) $(INCLUDES) -o $@ $(SRCS) GPU/GPUEngine.cu $(VANITY_OBJS) $(LIBS) $(CUDA_LIBS)

clean:
	rm -f BloomSearch BloomSearchGPU *.o

# Build bloom filter
bloom: build_bloom_filter.py
	python3 build_bloom_filter.py --download -o targets.bloom --test

# Help
help:
	@echo "BloomSearch - Bitcoin address collision finder"
	@echo ""
	@echo "Targets:"
	@echo "  all       - Build CPU version"
	@echo "  bloom     - Download addresses and build bloom filter"
	@echo "  clean     - Remove build artifacts"
	@echo ""
	@echo "Usage:"
	@echo "  1. make bloom     # Download 55M addresses and create bloom filter"
	@echo "  2. make           # Build BloomSearch"
	@echo "  3. ./BloomSearch -bloom targets.bloom -sorted targets.sorted -t 8"

.PHONY: all clean bloom help
