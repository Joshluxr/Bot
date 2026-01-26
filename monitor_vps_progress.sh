#!/bin/bash
# Monitor the progress of address matching on the VPS

VPS_IP="65.75.200.134"
VPS_PASSWORD="Q9qk4Hl6R2YGpw7"

echo "================================================"
echo "VPS Address Matching Monitor"
echo "================================================"
echo ""

run_ssh() {
    sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no root@${VPS_IP} "$@"
}

echo "Checking VPS status..."
echo ""

# Check if process is running
echo "[Process Status]"
if run_ssh "ps aux | grep -E '(match_addresses|match_funded)' | grep -v grep"; then
    echo "✓ Matching process is running"
else
    echo "⚠ No matching process found (may have completed or not started)"
fi

echo ""
echo "[Latest Log Output]"
echo "---"
run_ssh "tail -30 /root/matching_output.log 2>/dev/null || tail -30 /root/matching_log.txt 2>/dev/null || echo 'No log file found yet'"
echo "---"

echo ""
echo "[Results Status]"
run_ssh "ls -lh /root/address_matching/results/ 2>/dev/null || echo 'Results directory not created yet'"

echo ""
echo "[Disk Usage]"
run_ssh "df -h /root | tail -1"

echo ""
echo "[Memory Usage]"
run_ssh "free -h | grep Mem"

echo ""
echo "================================================"
echo "Commands:"
echo "  Watch live: sshpass -p '${VPS_PASSWORD}' ssh root@${VPS_IP} 'tail -f /root/matching_output.log'"
echo "  View results: sshpass -p '${VPS_PASSWORD}' ssh root@${VPS_IP} 'cat /root/address_matching/results/REPORT.txt'"
echo "  Download results: sshpass -p '${VPS_PASSWORD}' scp -r root@${VPS_IP}:/root/address_matching/results/ ./"
echo "================================================"
