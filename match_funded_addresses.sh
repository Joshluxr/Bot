#!/bin/bash
set -e

# Match Funded Addresses Script
# This script downloads candidate addresses from three servers and matches them
# against the complete Bitcoin funded addresses database

WORK_DIR="/root/address_matching"
CANDIDATES_DIR="${WORK_DIR}/candidates"
DB_DIR="${WORK_DIR}/database"
RESULTS_DIR="${WORK_DIR}/results"

# URLs for candidate files
SERVER1_URL="https://tmpfiles.org/dl/21294684/server1_candidates.txt"
SERVER2_URL="https://tmpfiles.org/dl/21294681/server2_candidates.txt"
SERVER4_URL="https://tmpfiles.org/dl/21294682/server4_candidates.txt"

# URL for funded addresses database
FUNDED_DB_URL="http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz"

echo "================================================"
echo "Bitcoin Address Matching System"
echo "================================================"
echo "Starting at: $(date)"
echo ""

# Create directories
echo "[1/7] Creating working directories..."
mkdir -p "${CANDIDATES_DIR}" "${DB_DIR}" "${RESULTS_DIR}"

# Download candidate files
echo ""
echo "[2/7] Downloading candidate files..."
echo "  - Server 1 (153,690 candidates)..."
wget -q --show-progress -O "${CANDIDATES_DIR}/server1_candidates.txt" "${SERVER1_URL}" || {
    echo "ERROR: Failed to download Server 1 candidates"
    exit 1
}

echo "  - Server 2 (51,274 candidates)..."
wget -q --show-progress -O "${CANDIDATES_DIR}/server2_candidates.txt" "${SERVER2_URL}" || {
    echo "ERROR: Failed to download Server 2 candidates"
    exit 1
}

echo "  - Server 4 (57,958 candidates)..."
wget -q --show-progress -O "${CANDIDATES_DIR}/server4_candidates.txt" "${SERVER4_URL}" || {
    echo "ERROR: Failed to download Server 4 candidates"
    exit 1
}

# Verify downloads
echo ""
echo "[3/7] Verifying candidate files..."
for server in server1 server2 server4; do
    file="${CANDIDATES_DIR}/${server}_candidates.txt"
    lines=$(wc -l < "$file")
    echo "  - ${server}: ${lines} lines"
done

# Merge all candidates
echo ""
echo "[4/7] Merging candidate files..."
cat "${CANDIDATES_DIR}"/*.txt | sort -u > "${WORK_DIR}/all_candidates.txt"
TOTAL_CANDIDATES=$(wc -l < "${WORK_DIR}/all_candidates.txt")
echo "  - Total unique candidates: ${TOTAL_CANDIDATES}"

# Download and extract funded addresses database
echo ""
echo "[5/7] Downloading funded addresses database..."
echo "  - This may take a while (file is large)..."
wget -q --show-progress -O "${DB_DIR}/Bitcoin_addresses_LATEST.txt.gz" "${FUNDED_DB_URL}" || {
    echo "ERROR: Failed to download funded addresses database"
    exit 1
}

echo "  - Extracting database..."
gunzip -f "${DB_DIR}/Bitcoin_addresses_LATEST.txt.gz"
TOTAL_FUNDED=$(wc -l < "${DB_DIR}/Bitcoin_addresses_LATEST.txt")
echo "  - Total funded addresses: ${TOTAL_FUNDED}"

# Sort funded addresses for efficient lookup
echo ""
echo "[6/7] Preparing database for matching..."
echo "  - Sorting funded addresses (this may take a while)..."
sort -u "${DB_DIR}/Bitcoin_addresses_LATEST.txt" > "${DB_DIR}/funded_sorted.txt"
echo "  - Database ready"

# Perform matching
echo ""
echo "[7/7] Matching candidates against funded addresses..."
echo "  - Starting comparison..."

# Use comm to find matches (both files must be sorted)
comm -12 "${WORK_DIR}/all_candidates.txt" "${DB_DIR}/funded_sorted.txt" > "${RESULTS_DIR}/matches.txt"

MATCHES=$(wc -l < "${RESULTS_DIR}/matches.txt")

# Generate detailed report
echo ""
echo "================================================"
echo "MATCHING COMPLETE"
echo "================================================"
echo "Timestamp: $(date)"
echo "Total candidates checked: ${TOTAL_CANDIDATES}"
echo "Total funded addresses: ${TOTAL_FUNDED}"
echo "MATCHES FOUND: ${MATCHES}"
echo ""

if [ "$MATCHES" -gt 0 ]; then
    echo "Matched addresses saved to: ${RESULTS_DIR}/matches.txt"
    echo ""
    echo "First 20 matches:"
    head -20 "${RESULTS_DIR}/matches.txt"
    echo ""

    # Create detailed report per server
    echo "Generating per-server match reports..."
    for server in server1 server2 server4; do
        comm -12 <(sort -u "${CANDIDATES_DIR}/${server}_candidates.txt") "${DB_DIR}/funded_sorted.txt" > "${RESULTS_DIR}/${server}_matches.txt"
        server_matches=$(wc -l < "${RESULTS_DIR}/${server}_matches.txt")
        echo "  - ${server}: ${server_matches} matches"
    done
else
    echo "No matches found."
fi

# Generate summary report
cat > "${RESULTS_DIR}/SUMMARY_REPORT.txt" << EOF
Bitcoin Address Matching Report
================================
Generated: $(date)

Input Statistics:
-----------------
Server 1 Candidates: $(wc -l < "${CANDIDATES_DIR}/server1_candidates.txt")
Server 2 Candidates: $(wc -l < "${CANDIDATES_DIR}/server2_candidates.txt")
Server 4 Candidates: $(wc -l < "${CANDIDATES_DIR}/server4_candidates.txt")
Total Unique Candidates: ${TOTAL_CANDIDATES}
Total Funded Addresses in DB: ${TOTAL_FUNDED}

Results:
--------
Total Matches Found: ${MATCHES}

Per-Server Breakdown:
---------------------
Server 1 Matches: $(wc -l < "${RESULTS_DIR}/server1_matches.txt" 2>/dev/null || echo "0")
Server 2 Matches: $(wc -l < "${RESULTS_DIR}/server2_matches.txt" 2>/dev/null || echo "0")
Server 4 Matches: $(wc -l < "${RESULTS_DIR}/server4_matches.txt" 2>/dev/null || echo "0")

Output Files:
-------------
All Matches: ${RESULTS_DIR}/matches.txt
Server 1 Matches: ${RESULTS_DIR}/server1_matches.txt
Server 2 Matches: ${RESULTS_DIR}/server2_matches.txt
Server 4 Matches: ${RESULTS_DIR}/server4_matches.txt
Summary Report: ${RESULTS_DIR}/SUMMARY_REPORT.txt

Working Directory: ${WORK_DIR}
EOF

echo ""
echo "Summary report saved to: ${RESULTS_DIR}/SUMMARY_REPORT.txt"
echo ""
echo "All results available in: ${RESULTS_DIR}/"
echo "================================================"
