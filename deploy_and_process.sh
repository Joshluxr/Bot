#!/bin/bash

# VPS Configuration
VPS_HOST="65.75.200.135"
VPS_USER="root"
VPS_PASS="LiA6QhucR470Ia3"
KEY_URL="$1"

if [ -z "$KEY_URL" ]; then
    echo "Usage: $0 <key_list_url>"
    exit 1
fi

echo "=== Bitcoin Key Processing Deployment ==="
echo "VPS: ${VPS_HOST}"
echo "Key URL: ${KEY_URL}"
echo

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "Installing sshpass..."
    apt-get update -qq && apt-get install -y sshpass
fi

# Create temporary script to run on VPS
cat > /tmp/vps_process.sh << 'VPSEOF'
#!/bin/bash
set -e

echo "=== Starting Bitcoin Key Processing ==="

# Download the key list
echo "Downloading key list..."
wget -q -O keys.txt "$KEY_URL" || curl -s -o keys.txt "$KEY_URL"

# Count keys
KEY_COUNT=$(grep -v '^#' keys.txt | grep -v '^$' | wc -l)
echo "Found $KEY_COUNT keys to process"

# Run the processor
echo "Processing keys..."
python3 bitcoin_key_processor.py keys.txt processed_keys.csv

# Show results
echo
echo "=== Processing Results ==="
if [ -f processed_keys.csv ]; then
    RESULT_COUNT=$(tail -n +2 processed_keys.csv | wc -l)
    echo "Successfully processed: $RESULT_COUNT keys"
    echo
    echo "First 5 results:"
    head -n 6 processed_keys.csv
    echo
    echo "Output file: processed_keys.csv ($(wc -c < processed_keys.csv) bytes)"
else
    echo "ERROR: Output file not created"
    exit 1
fi
VPSEOF

# Replace KEY_URL placeholder in the VPS script
sed -i "s|\$KEY_URL|$KEY_URL|g" /tmp/vps_process.sh

echo "Uploading processor script to VPS..."
sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no \
    /root/repo/bitcoin_key_processor.py ${VPS_USER}@${VPS_HOST}:/root/

echo "Uploading execution script to VPS..."
sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no \
    /tmp/vps_process.sh ${VPS_USER}@${VPS_HOST}:/root/

echo "Executing on VPS..."
sshpass -p "$VPS_PASS" ssh -o StrictHostKeyChecking=no \
    ${VPS_USER}@${VPS_HOST} 'bash /root/vps_process.sh'

echo
echo "Downloading results..."
sshpass -p "$VPS_PASS" scp -o StrictHostKeyChecking=no \
    ${VPS_USER}@${VPS_HOST}:/root/processed_keys.csv \
    /root/repo/processed_keys.csv

if [ -f /root/repo/processed_keys.csv ]; then
    echo
    echo "=== SUCCESS ==="
    echo "Results downloaded to: /root/repo/processed_keys.csv"
    echo "Total size: $(wc -c < /root/repo/processed_keys.csv) bytes"
    echo "Total lines: $(wc -l < /root/repo/processed_keys.csv)"
    echo
    echo "First 10 lines:"
    head -n 10 /root/repo/processed_keys.csv
else
    echo "ERROR: Failed to download results"
    exit 1
fi

# Cleanup
rm -f /tmp/vps_process.sh

echo
echo "=== COMPLETE ==="
