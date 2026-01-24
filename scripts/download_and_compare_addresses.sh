#!/bin/bash

# Bitcoin Address Download and Comparison Script
# This script runs directly on the VPS to download and compare addresses

set -e

WORK_DIR="/root/bitcoin_address_check"
LOG_FILE="$WORK_DIR/comparison.log"

# Create work directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo "[ERROR] $1" | tee -a "$LOG_FILE"
}

log "=== Bitcoin Address Comparison Script Started ==="
log "Working directory: $WORK_DIR"

# Check available disk space
AVAILABLE_SPACE=$(df -BG "$WORK_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
log "Available disk space: ${AVAILABLE_SPACE}GB"

if [ "$AVAILABLE_SPACE" -lt 50 ]; then
    log "Warning: Less than 50GB available. This may not be enough."
fi

# Download candidate address parts
log "=== Downloading candidate address parts ==="
download_part() {
    local url=$1
    local output=$2
    local part_name=$(basename "$output")

    if [ -f "$output" ]; then
        log "Part $part_name already exists, skipping download"
        return 0
    fi

    log "Downloading $part_name..."
    if wget -c -O "$output" "$url" 2>&1 | tail -5 | tee -a "$LOG_FILE"; then
        log "Successfully downloaded $part_name ($(du -h "$output" | cut -f1))"
        return 0
    else
        error "Failed to download $part_name"
        return 1
    fi
}

# Download all parts (fixed URL for part_ad)
download_part "https://files.catbox.moe/jptd8v.gz" "part_aa.gz"
download_part "https://files.catbox.moe/6trl8g.gz" "part_ab.gz"
download_part "https://files.catbox.moe/1mrk4j.gz" "part_ac.gz"
download_part "https://files.catbox.moe/vk43zp.gz" "part_ad.gz"
download_part "https://files.catbox.moe/96zj24.gz" "part_ae.gz"
download_part "https://files.catbox.moe/h544ay.gz" "part_af.gz"

# Download funded addresses
log "=== Downloading Bitcoin funded addresses ==="
if [ ! -f "Bitcoin_addresses_LATEST.txt.gz" ]; then
    log "Downloading Bitcoin_addresses_LATEST.txt.gz..."
    wget -c -O Bitcoin_addresses_LATEST.txt.gz http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz 2>&1 | tail -10 | tee -a "$LOG_FILE"
    log "Successfully downloaded funded addresses ($(du -h Bitcoin_addresses_LATEST.txt.gz | cut -f1))"
else
    log "Bitcoin_addresses_LATEST.txt.gz already exists, skipping download"
fi

# Decompress candidate parts
log "=== Decompressing candidate address parts ==="
for part in part_aa.gz part_ab.gz part_ac.gz part_ad.gz part_ae.gz part_af.gz; do
    if [ -f "$part" ]; then
        decompressed="${part%.gz}"
        if [ ! -f "$decompressed" ]; then
            log "Decompressing $part..."
            gunzip -k "$part"
            log "Decompressed $part ($(du -h "$decompressed" | cut -f1))"
        else
            log "$decompressed already exists, skipping decompression"
        fi
    fi
done

# Combine all candidate parts
log "=== Combining candidate address parts ==="
if [ ! -f "all_candidates_full.txt" ]; then
    log "Combining all parts into all_candidates_full.txt..."
    cat part_aa part_ab part_ac part_ad part_ae part_af > all_candidates_full.txt
    CANDIDATE_COUNT=$(wc -l < all_candidates_full.txt)
    log "Combined file created: all_candidates_full.txt"
    log "Total candidate addresses: $CANDIDATE_COUNT"
    log "File size: $(du -h all_candidates_full.txt | cut -f1)"
else
    CANDIDATE_COUNT=$(wc -l < all_candidates_full.txt)
    log "all_candidates_full.txt already exists ($CANDIDATE_COUNT addresses)"
fi

# Decompress funded addresses
log "=== Decompressing funded addresses ==="
if [ ! -f "Bitcoin_addresses_LATEST.txt" ]; then
    log "Decompressing Bitcoin_addresses_LATEST.txt.gz..."
    gunzip -k Bitcoin_addresses_LATEST.txt.gz
    FUNDED_COUNT=$(wc -l < Bitcoin_addresses_LATEST.txt)
    log "Decompressed funded addresses"
    log "Total funded addresses: $FUNDED_COUNT"
    log "File size: $(du -h Bitcoin_addresses_LATEST.txt | cut -f1)"
else
    FUNDED_COUNT=$(wc -l < Bitcoin_addresses_LATEST.txt)
    log "Bitcoin_addresses_LATEST.txt already exists ($FUNDED_COUNT addresses)"
fi

# Sort and prepare files for comparison
log "=== Preparing files for comparison ==="

if [ ! -f "all_candidates_sorted.txt" ]; then
    log "Sorting candidate addresses..."
    sort -u all_candidates_full.txt > all_candidates_sorted.txt
    SORTED_CANDIDATE_COUNT=$(wc -l < all_candidates_sorted.txt)
    log "Sorted candidates: $SORTED_CANDIDATE_COUNT unique addresses"
else
    SORTED_CANDIDATE_COUNT=$(wc -l < all_candidates_sorted.txt)
    log "all_candidates_sorted.txt already exists ($SORTED_CANDIDATE_COUNT addresses)"
fi

if [ ! -f "Bitcoin_addresses_sorted.txt" ]; then
    log "Sorting funded addresses..."
    sort -u Bitcoin_addresses_LATEST.txt > Bitcoin_addresses_sorted.txt
    SORTED_FUNDED_COUNT=$(wc -l < Bitcoin_addresses_sorted.txt)
    log "Sorted funded: $SORTED_FUNDED_COUNT unique addresses"
else
    SORTED_FUNDED_COUNT=$(wc -l < Bitcoin_addresses_sorted.txt)
    log "Bitcoin_addresses_sorted.txt already exists ($SORTED_FUNDED_COUNT addresses)"
fi

# Find matches
log "=== Finding matching addresses ==="
log "This may take a while for large files..."

comm -12 all_candidates_sorted.txt Bitcoin_addresses_sorted.txt > matches.txt
MATCH_COUNT=$(wc -l < matches.txt)

log "=== COMPARISON COMPLETE ==="
log "Candidate addresses: $SORTED_CANDIDATE_COUNT"
log "Funded addresses: $SORTED_FUNDED_COUNT"
log "MATCHES FOUND: $MATCH_COUNT"

if [ "$MATCH_COUNT" -gt 0 ]; then
    log "Matches saved to: $WORK_DIR/matches.txt"
    log "First 10 matches:"
    head -10 matches.txt | tee -a "$LOG_FILE"
else
    log "No matches found between candidate and funded addresses"
fi

# Create summary report
cat > summary_report.txt << EOF
Bitcoin Address Comparison Summary
Generated: $(date)
=====================================

Files Processed:
- Candidate addresses: all_candidates_full.txt ($CANDIDATE_COUNT total, $SORTED_CANDIDATE_COUNT unique)
- Funded addresses: Bitcoin_addresses_LATEST.txt ($FUNDED_COUNT total, $SORTED_FUNDED_COUNT unique)

Results:
- Matches found: $MATCH_COUNT

Output files:
- matches.txt: List of matching addresses
- comparison.log: Detailed execution log

Working directory: $WORK_DIR
EOF

log "Summary report saved to: $WORK_DIR/summary_report.txt"
log "All done!"
