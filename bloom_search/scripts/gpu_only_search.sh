#\!/bin/bash
# GPU-Only Bloom Filter Search
# Uses all 8 GPUs, no CPU to save for system tasks

BLOOM_FILE="/root/bloom_v2.bloom"
PREFIX_FILE="/root/bloom_v2.prefix32"
SEEDS_FILE="/root/bloom_v2.seeds"
BLOOM_BITS=335098344
BLOOM_HASHES=8
LOG_FILE="/root/gpu_search.log"
PID_FILE="/root/gpu_search.pid"

GPU_RUN_TIME=300

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" >> "$LOG_FILE"; }

cleanup() {
    log "Stopping GPU search..."
    pkill -f BloomSearch32Silent
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

start_gpu_search() {
    local gpu=$1
    cd /root/VanitySearch
    while true; do
        timeout ${GPU_RUN_TIME} ./BloomSearch32Silent \
            -bloom "$BLOOM_FILE" -seeds "$SEEDS_FILE" -prefix "$PREFIX_FILE" \
            -bits "$BLOOM_BITS" -hashes "$BLOOM_HASHES" -gpu $gpu \
            -state "/root/gpu${gpu}.state" >> "$LOG_FILE" 2>&1
        sleep 1
    done
}

main() {
    echo $$ > "$PID_FILE"
    log "========================================"
    log "  GPU-Only Bloom Filter Search         "
    log "  8x RTX 4080 SUPER (~20 GKey/s total) "
    log "========================================"
    
    # Start GPU searches (8 GPUs)
    for gpu in 0 1 2 3 4 5 6 7; do
        start_gpu_search $gpu &
        log "Started GPU $gpu"
    done
    
    # Wait forever
    wait
}

# Check if already running
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        echo "Already running with PID $old_pid"
        exit 1
    fi
    rm -f "$PID_FILE"
fi

main
