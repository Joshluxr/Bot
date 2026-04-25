CUDA_PATH ?= /usr/local/cuda
NVCC = $(CUDA_PATH)/bin/nvcc

# Auto-detect compute capability if nvidia-smi is available.
CCAP ?= $(shell sh -c 'if command -v nvidia-smi >/dev/null 2>&1; then nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d .; fi')

# Default to sm_120 (Blackwell / RTX 5090) if detection fails.
# Override with: make CCAP=89 (Ada), CCAP=86 (Ampere), CCAP=75 (Turing).
ifeq ($(CCAP),)
    CCAP = 120
endif

NVCC_FLAGS = -O3 -std=c++14 \
    -gencode=arch=compute_$(CCAP),code=sm_$(CCAP) \
    --ptxas-options=-v \
    -maxrregcount=128 \
    -I. \
    -lineinfo

LDFLAGS = -lcuda

HEADERS = GPUGroup.h GPUMath.h GPUHash.h CPUGroup.h ripemd160.h

.PHONY: all clean fast legacy test smoke help

all: searchk4_fast

help:
	@echo "Targets:"
	@echo "  make searchk4_fast   Build the maintained fast implementation"
	@echo "  make searchk4        Build the legacy/reference implementation"
	@echo "  make smoke           End-to-end test: Puzzle #1 direct-mode match"
	@echo "  make test            Short prefix-mode smoke test"
	@echo "  make clean           Remove built binaries and state files"

# ripemd160.c is pure C99. nvcc compiles it via its embedded host toolchain
# with -x c. If that ever fails, fall back to: gcc -O3 -c ripemd160.c
ripemd160.o: ripemd160.c ripemd160.h
	$(NVCC) -O3 -std=c++14 -c -o $@ -x c $<

searchk4_fast: SearchK4_fast.cu $(HEADERS) ripemd160.o
	@echo "Building searchk4_fast for compute capability $(CCAP)..."
	$(NVCC) $(NVCC_FLAGS) -o $@ SearchK4_fast.cu ripemd160.o $(LDFLAGS)

# Historical/reference build. The maintained path is searchk4_fast.
searchk4: SearchK4.cu $(HEADERS)
	@echo "Building legacy/reference searchk4 for compute capability $(CCAP)..."
	$(NVCC) $(NVCC_FLAGS) -o $@ SearchK4.cu $(LDFLAGS)

clean:
	rm -f searchk4_fast searchk4 ripemd160.o *.state found_k4*.txt found_k4_gpu*.txt

# End-to-end smoke test using Puzzle #1 (key = 1). Exercises: key derivation,
# Jacobian scalar multiply, strided memory layout, hash160 computation,
# direct-match comparison, private-key reconstruction, host-side RIPEMD-160
# verification, WIF formatting. Look for "verified=yes" in the output file.
smoke: searchk4_fast
	@echo "Smoke test: Puzzle #1 (key=1, expected uncompressed: 1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm)"
	@echo "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm" > _smoke_patterns.txt
	timeout 30 ./searchk4_fast -patterns _smoke_patterns.txt -direct -bits 1 -threads 64 -o _smoke_found.txt || true
	@rm -f _smoke_patterns.txt *.state
	@echo
	@echo "--- matches (expect verified=yes, NO 'UNVERIFIED' lines) ---"
	@grep -E "Pattern=|PrivKey|verified=|UNVERIFIED" _smoke_found.txt 2>/dev/null || true
	@rm -f _smoke_found.txt

# Short prefix-mode smoke test, kept from the ChatGPT baseline.
test: searchk4_fast
	@echo "Creating test patterns..."
	@echo "1A" > test_patterns.txt
	@echo "1AB" >> test_patterns.txt
	@echo "1Feex" >> test_patterns.txt
	timeout 30 ./searchk4_fast -patterns test_patterns.txt -startx 0x1 -threads 1024 -gpu 0 || true
	@rm -f test_patterns.txt *.state found_k4*.txt found_k4_gpu*.txt
