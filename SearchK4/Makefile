CUDA_PATH ?= /usr/local/cuda
NVCC = $(CUDA_PATH)/bin/nvcc

# Auto-detect compute capability if not specified
CCAP ?= $(shell nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')

# Default to sm_89 (RTX 4090/5090) if detection fails
ifeq ($(CCAP),)
    CCAP = 89
endif

NVCC_FLAGS = -O3 -std=c++14 \
    -gencode=arch=compute_$(CCAP),code=sm_$(CCAP) \
    --ptxas-options=-v \
    -maxrregcount=64 \
    -I. \
    -lineinfo

LDFLAGS = -lcuda

HEADERS = GPUGroup.h GPUMath.h GPUHash.h CPUGroup.h

.PHONY: all clean fast

# Build the fast version by default
all: searchk4_fast

# Fast version (recommended)
searchk4_fast: SearchK4_fast.cu $(HEADERS)
	@echo "Building SearchK4_fast for compute capability $(CCAP)..."
	$(NVCC) $(NVCC_FLAGS) -o $@ SearchK4_fast.cu $(LDFLAGS)

# Original version
searchk4: SearchK4.cu $(HEADERS)
	@echo "Building SearchK4 for compute capability $(CCAP)..."
	$(NVCC) $(NVCC_FLAGS) -o $@ SearchK4.cu $(LDFLAGS)

clean:
	rm -f searchk4_fast searchk4 *.state

# Test with sample patterns
test: searchk4_fast
	@echo "Creating test patterns..."
	@echo "1A" > test_patterns.txt
	@echo "1AB" >> test_patterns.txt
	@echo "1Feex" >> test_patterns.txt
	timeout 30 ./searchk4_fast -patterns test_patterns.txt -startx 0x1 -gpu 0 || true
	@rm -f test_patterns.txt *.state
