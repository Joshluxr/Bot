#!/bin/bash

# Helper script to check Bitcoin address comparison results on VPS

VPS_IP="65.75.200.133"
VPS_USER="root"
VPS_PASS="S910BtnGoh45RuE"

echo "=== Bitcoin Address Check - Quick Status ==="
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass..."
    apt-get update && apt-get install -y sshpass
fi

# Run remote command to check status
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no ${VPS_USER}@${VPS_IP} << 'ENDSSH'
cd /root/bitcoin_address_check 2>/dev/null || { echo "Working directory not found. Run download_and_compare_addresses.sh first."; exit 1; }

echo "Working Directory: /root/bitcoin_address_check"
echo ""
echo "=== Disk Usage ==="
du -sh . 2>/dev/null || echo "No data yet"
echo ""
echo "=== File Status ==="
ls -lh *.txt *.gz 2>/dev/null | awk '{print $9, "-", $5}'
echo ""

if [ -f "summary_report.txt" ]; then
    echo "=== Comparison Summary ==="
    cat summary_report.txt
else
    echo "No comparison results yet."
fi

if [ -f "matches.txt" ]; then
    MATCH_COUNT=$(wc -l < matches.txt)
    if [ "$MATCH_COUNT" -gt 0 ]; then
        echo ""
        echo "=== First 20 Matches ==="
        head -20 matches.txt
    fi
fi
ENDSSH

echo ""
echo "=== Access VPS ==="
echo "ssh root@$VPS_IP"
echo "cd /root/bitcoin_address_check"
echo ""
echo "To download all results locally:"
echo "sshpass -p '$VPS_PASS' scp -r root@$VPS_IP:/root/bitcoin_address_check ./bitcoin_vps_backup"
