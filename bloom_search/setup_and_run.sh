#!/bin/bash
#
# BloomSearch Setup and Run Script
#
# This script:
# 1. Downloads the Bitcoin address list (55M+ addresses)
# 2. Builds the bloom filter (~200 MB)
# 3. Compiles BloomSearch
# 4. Runs the search
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}BloomSearch Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Step 1: Check dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 is required but not installed.${NC}"
    exit 1
fi

if ! command -v g++ &> /dev/null; then
    echo -e "${RED}g++ is required but not installed.${NC}"
    exit 1
fi

# Step 2: Download and build bloom filter
BLOOM_FILE="targets.bloom"
SORTED_FILE="targets.sorted"
ADDRESS_FILE="Bitcoin_addresses_LATEST.txt"

if [ ! -f "$BLOOM_FILE" ] || [ ! -f "$SORTED_FILE" ]; then
    echo -e "\n${YELLOW}Building bloom filter from Bitcoin addresses...${NC}"
    echo "This will:"
    echo "  - Download ~1.4 GB of address data"
    echo "  - Create a ~200 MB bloom filter"
    echo "  - Create a ~1.1 GB sorted hash160 file"
    echo ""

    # Download if needed
    if [ ! -f "$ADDRESS_FILE" ]; then
        echo "Downloading address list..."
        curl -L "http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz" | gunzip > "$ADDRESS_FILE"
    fi

    # Build bloom filter
    python3 build_bloom_filter.py \
        --input "$ADDRESS_FILE" \
        --output "$BLOOM_FILE" \
        --fp-rate 1e-7 \
        --test

    echo -e "${GREEN}Bloom filter built successfully!${NC}"
else
    echo -e "${GREEN}Bloom filter already exists.${NC}"
fi

# Step 3: Build VanitySearch dependencies
echo -e "\n${YELLOW}Building VanitySearch dependencies...${NC}"

VANITY_DIR="../vanitysearch_analysis"
if [ -d "$VANITY_DIR" ]; then
    cd "$VANITY_DIR"

    # Build object files
    for src in Int.cpp IntMod.cpp IntGroup.cpp Point.cpp SECP256K1.cpp Random.cpp Base58.cpp; do
        obj="${src%.cpp}.o"
        if [ ! -f "$obj" ] || [ "$src" -nt "$obj" ]; then
            echo "Compiling $src..."
            g++ -O3 -march=native -std=c++17 -c "$src" -o "$obj"
        fi
    done

    # Build hash functions
    cd hash
    for src in ripemd160.cpp sha256.cpp sha512.cpp; do
        obj="${src%.cpp}.o"
        if [ ! -f "$obj" ] || [ "$src" -nt "$obj" ]; then
            echo "Compiling hash/$src..."
            g++ -O3 -march=native -std=c++17 -c "$src" -o "$obj"
        fi
    done

    cd "$SCRIPT_DIR"
    echo -e "${GREEN}Dependencies built.${NC}"
else
    echo -e "${RED}VanitySearch directory not found at $VANITY_DIR${NC}"
    exit 1
fi

# Step 4: Build BloomSearch
echo -e "\n${YELLOW}Building BloomSearch...${NC}"
make clean 2>/dev/null || true
make

echo -e "${GREEN}BloomSearch built successfully!${NC}"

# Step 5: Run
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Ready to run!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Usage:"
echo "  ./BloomSearch -bloom $BLOOM_FILE -sorted $SORTED_FILE -t 8"
echo ""
echo "Options:"
echo "  -t <threads>     Number of CPU threads"
echo "  -seed <string>   Seed for deterministic search (for resume)"
echo "  -o <file>        Output file for matches"
echo "  -checkpoint <f>  Checkpoint file"
echo "  -compressed      Search compressed keys only"
echo "  -uncompressed    Search uncompressed keys only"
echo ""
echo "Example:"
echo "  ./BloomSearch -bloom $BLOOM_FILE -sorted $SORTED_FILE -t 16 -seed 'my_seed' -o found.txt"
echo ""

# Ask to run
read -p "Run now with 8 CPU threads? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${YELLOW}Starting BloomSearch...${NC}"
    ./BloomSearch -bloom "$BLOOM_FILE" -sorted "$SORTED_FILE" -t 8 -o matches.txt
fi
