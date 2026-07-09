#!/bin/bash
# BloomSearch Runner - Runs VanitySearch and checks results against bloom filter

BLOOM_FILE="/workspace/bloom_search/btc_addresses.bloom"
VANITYSEARCH="/workspace/Bot/vanitysearch_analysis/VanitySearch"
OUTPUT_FILE="/workspace/bloom_search/found_matches.txt"
TEMP_FILE="/workspace/bloom_search/vanity_output.txt"

echo "=== BloomSearch GPU Runner ==="
echo "Bloom filter: $BLOOM_FILE"
echo "VanitySearch: $VANITYSEARCH"
echo ""

# Check files exist
if [ ! -f "$BLOOM_FILE" ]; then
    echo "ERROR: Bloom filter not found!"
    exit 1
fi

if [ ! -f "$VANITYSEARCH" ]; then
    echo "ERROR: VanitySearch not found!"
    exit 1
fi

# Run VanitySearch in random mode and check results
echo "Starting VanitySearch in continuous random mode..."
echo "Press Ctrl+C to stop"
echo ""

# Use 1 prefix (essentially random searching)
# The output will be checked against bloom filter
cd /workspace/Bot/vanitysearch_analysis

while true; do
    # Run VanitySearch for a batch
    timeout 60 ./VanitySearch -gpu -gpuId 0,1,2,3 -o "$TEMP_FILE" -t 0 -stop 1B 2>/dev/null
    
    if [ -f "$TEMP_FILE" ]; then
        # Extract addresses and check against bloom filter
        grep "PubAddress:" "$TEMP_FILE" | awk '{print $2}' | while read addr; do
            echo "$addr" | python3 /workspace/bloom_search/bloom_verifier.py "$BLOOM_FILE" 2>/dev/null | grep MATCH && echo "$addr" >> "$OUTPUT_FILE"
        done
        rm -f "$TEMP_FILE"
    fi
done
