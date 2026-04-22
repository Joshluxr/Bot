#!/bin/bash
#
# Auto Checkpoint Sync - Periodically uploads GPU states to VPS
# Run alongside gpu_only_search.sh to ensure progress is never lost
#
# Usage: ./auto_checkpoint_sync.sh <vps_server> [interval_minutes]
# Example: ./auto_checkpoint_sync.sh root@your-vps.com 30

VPS_SERVER="${1:-}"
SYNC_INTERVAL="${2:-30}"  # Default: sync every 30 minutes
CHECKPOINT_DIR="/root/bloom_checkpoints"
STATE_DIR="/root"
LOG_FILE="/root/checkpoint_sync.log"

if [ -z "$VPS_SERVER" ]; then
    echo "Usage: $0 <vps_server> [interval_minutes]"
    echo "Example: $0 root@your-vps.com 30"
    exit 1
fi

# Get unique server identifier
SERVER_NAME="${HOSTNAME:-$(hostname)}"
if [ "$SERVER_NAME" = "localhost" ] || [ -z "$SERVER_NAME" ]; then
    SERVER_NAME="gpu-$(cat /etc/machine-id 2>/dev/null | head -c 8 || echo $$)"
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" | tee -a "$LOG_FILE"
}

upload_state() {
    local gpu=$1
    local state_file="$STATE_DIR/gpu${gpu}.state"

    if [ ! -f "$state_file" ]; then
        return 1
    fi

    # Get total keys from state file (first 8 bytes, little endian)
    local total_keys=$(od -An -tu8 -N8 "$state_file" 2>/dev/null | tr -d ' ')
    local keys_human=$(python3 -c "print(f'{$total_keys/1e12:.2f}T')" 2>/dev/null || echo "?")

    # Upload
    local remote_file="$CHECKPOINT_DIR/${SERVER_NAME}_gpu${gpu}.state"
    ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$VPS_SERVER" "mkdir -p $CHECKPOINT_DIR" 2>/dev/null

    if scp -o StrictHostKeyChecking=no -o ConnectTimeout=30 "$state_file" "${VPS_SERVER}:${remote_file}" 2>/dev/null; then
        log "GPU $gpu: Uploaded $keys_human keys to $remote_file"
        return 0
    else
        log "GPU $gpu: Upload FAILED"
        return 1
    fi
}

update_metadata() {
    # Create/update metadata on VPS
    local metadata_file="$CHECKPOINT_DIR/checkpoints.json"
    local temp_metadata="/tmp/checkpoints_$$.json"

    # Download existing metadata
    ssh -o StrictHostKeyChecking=no "$VPS_SERVER" "cat $metadata_file 2>/dev/null" > "$temp_metadata" 2>/dev/null || echo "{}" > "$temp_metadata"

    # Update with Python
    python3 << PYEOF
import json
import os
from datetime import datetime

metadata_file = "$temp_metadata"
server_name = "$SERVER_NAME"
state_dir = "$STATE_DIR"

try:
    with open(metadata_file) as f:
        metadata = json.load(f)
except:
    metadata = {}

for gpu in range(8):
    state_file = f"{state_dir}/gpu{gpu}.state"
    if not os.path.exists(state_file):
        continue

    with open(state_file, 'rb') as f:
        total_keys = int.from_bytes(f.read(8), 'little')

    key = f"{server_name}_gpu{gpu}"
    metadata[key] = {
        'hostname': server_name,
        'gpu_id': gpu,
        'total_keys': total_keys,
        'total_keys_human': f"{total_keys/1e12:.2f}T",
        'uploaded': datetime.now().isoformat()
    }

with open(metadata_file, 'w') as f:
    json.dump(metadata, f, indent=2)
PYEOF

    # Upload metadata
    scp -o StrictHostKeyChecking=no "$temp_metadata" "${VPS_SERVER}:${metadata_file}" 2>/dev/null
    rm -f "$temp_metadata"
}

sync_all() {
    log "Starting checkpoint sync to $VPS_SERVER..."

    local success=0
    local total=0

    for gpu in 0 1 2 3 4 5 6 7; do
        if [ -f "$STATE_DIR/gpu${gpu}.state" ]; then
            total=$((total + 1))
            if upload_state $gpu; then
                success=$((success + 1))
            fi
        fi
    done

    if [ $total -gt 0 ]; then
        update_metadata
        log "Sync complete: $success/$total GPUs uploaded"
    else
        log "No state files found"
    fi
}

# Main loop
log "========================================"
log "  Auto Checkpoint Sync Started"
log "  Server: $SERVER_NAME"
log "  VPS: $VPS_SERVER"
log "  Interval: ${SYNC_INTERVAL}m"
log "========================================"

# Initial sync
sync_all

while true; do
    sleep $((SYNC_INTERVAL * 60))
    sync_all
done
