CUDA_PATH ?= /usr/local/cuda
NVCC = $(CUDA_PATH)/bin/nvcc

# Auto-detect compute capability if not specified
CCAP ?= $(shell nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '.')

# Default to sm_89 (RTX 4090) if detection fails
ifeq ($(CCAP),)
    CCAP = 89
endif

NVCC_FLAGS = -O3 -std=c++14 \
    -gencode=arch=compute_$(CCAP),code=sm_$(CCAP) \
    --ptxas-options=-v \
    -I. \
    -lineinfo

LDFLAGS = -lcuda

TARGET = SearchK4
SRCS = SearchK4.cu
HEADERS = GPUGroup.h GPUMath.h GPUHash.h

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SRCS) $(HEADERS)
	@echo "Building for compute capability $(CCAP)..."
	$(NVCC) $(NVCC_FLAGS) -o $@ $(SRCS) $(LDFLAGS)

clean:
	rm -f $(TARGET)

# Test with sample patterns
test: $(TARGET)
	@echo "Creating test patterns..."
	@echo "1Feex" > test_patterns.txt
	@echo "1A1zP" >> test_patterns.txt
	@echo "1Test" >> test_patterns.txt
	timeout 30 ./$(TARGET) -patterns test_patterns.txt -gpu 0 || true
	@rm -f test_patterns.txt
