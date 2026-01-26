#!/bin/bash

echo "=== Bitcoin Address Comparison Script ==="
echo "Candidate addresses: 27,208"
echo ""

# Extract addresses from funded database
echo "[1/4] Extracting funded addresses from database..."
if [ -f "Bitcoin_addresses_LATEST.txt.gz" ]; then
    gunzip -c Bitcoin_addresses_LATEST.txt.gz | sort -u > funded_addresses_sorted.txt
    FUNDED_COUNT=$(wc -l < funded_addresses_sorted.txt)
    echo "  ✓ Funded addresses: $FUNDED_COUNT"
else
    echo "  ✗ Error: Bitcoin_addresses_LATEST.txt.gz not found"
    exit 1
fi

# Ensure candidate addresses are sorted
echo "[2/4] Ensuring candidate addresses are sorted..."
sort -u candidate_addresses.txt > candidate_addresses_sorted.txt
CANDIDATE_COUNT=$(wc -l < candidate_addresses_sorted.txt)
echo "  ✓ Candidate addresses: $CANDIDATE_COUNT"

# Find matches using comm
echo "[3/4] Finding matches (this may take a moment)..."
comm -12 candidate_addresses_sorted.txt funded_addresses_sorted.txt > matches.txt
MATCH_COUNT=$(wc -l < matches.txt)
echo "  ✓ Matches found: $MATCH_COUNT"

# Generate detailed report
echo "[4/4] Generating detailed report..."
cat > comparison_results.md << 'REPORT'
# Bitcoin Address Comparison Results

**Date:** $(date)
**Candidate File:** privkey_address.csv
**Funded Database:** Bitcoin_addresses_LATEST.txt.gz

## Summary

- **Total candidate addresses:** CANDIDATE_COUNT
- **Total funded addresses in database:** FUNDED_COUNT
- **Matches found:** MATCH_COUNT

## Detailed Results

REPORT

if [ $MATCH_COUNT -eq 0 ]; then
    cat >> comparison_results.md << 'REPORT'
### No Matches Found

All 27,208 candidate addresses were compared against the funded Bitcoin address database.
**Result: Zero matches** - none of the candidate addresses have ever received Bitcoin.

This confirms that all candidates are:
1. Bloom filter false positives, OR
2. Addresses that have never been used, OR  
3. Generated from an incorrect keyspace

REPORT
else
    echo "### MATCHES FOUND!" >> comparison_results.md
    echo "" >> comparison_results.md
    echo "The following addresses exist in both datasets:" >> comparison_results.md
    echo '```' >> comparison_results.md
    cat matches.txt >> comparison_results.md
    echo '```' >> comparison_results.md
    echo "" >> comparison_results.md
    
    # Extract private keys for matches
    echo "### Private Keys for Matched Addresses" >> comparison_results.md
    echo "" >> comparison_results.md
    echo "| Private Key (Hex) | Address | Status |" >> comparison_results.md
    echo "|-------------------|---------|--------|" >> comparison_results.md
    
    while read -r address; do
        privkey=$(grep ",$address" privkey_address.csv | head -1 | cut -d',' -f1)
        echo "| \`$privkey\` | $address | ⚠️ FUNDED |" >> comparison_results.md
    done < matches.txt
fi

echo "  ✓ Report saved to comparison_results.md"
echo ""
echo "=== Comparison Complete ==="
echo "Matches: $MATCH_COUNT"
echo "Report: comparison_results.md"
