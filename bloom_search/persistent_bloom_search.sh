#!/bin/bash
#
# Persistent GPU Bloom Filter Search with Auto-Restart
# Runs forever until manually stopped, auto-restarts on crash
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEARCH_BIN="$SCRIPT_DIR/bloom_gpu_search"
PREFIX_FILE="/root/bloom_v2.prefix32"
BLOOM_FILE="/root/bloom_v2.bloom"
LOG_FILE="$SCRIPT_DIR/search.log"
STATS_FILE="$SCRIPT_DIR/search_stats.json"
PID_FILE="$SCRIPT_DIR/search.pid"
FOUND_FILE="$SCRIPT_DIR/FOUND_MATCHES.txt"

# Configuration
GPU_IDS="0,1,2,3,4,5,6,7"
RUN_TIME=300  # 5 minutes per batch, then checkpoint
MAX_RESTARTS_PER_HOUR=10

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Stats tracking
TOTAL_KEYS=0
TOTAL_PREFIX_HITS=0
TOTAL_BLOOM_PASSES=0
SESSION_START=$(date +%s)
BATCH_COUNT=0
RESTART_COUNT=0
LAST_RESTART_HOUR=$(date +%H)
RESTARTS_THIS_HOUR=0

log() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') | $1"
    echo -e "$msg" | tee -a "$LOG_FILE"
}

log_stats() {
    local msg="$(date '+%Y-%m-%d %H:%M:%S') | [STATS] $1"
    echo -e "${CYAN}$msg${NC}" | tee -a "$LOG_FILE"
}

# Load stats from previous session
load_stats() {
    if [ -f "$STATS_FILE" ]; then
        log "${GREEN}Loading previous session stats...${NC}"
        TOTAL_KEYS=$(python3 -c "import json; print(json.load(open('$STATS_FILE')).get('total_keys', 0))" 2>/dev/null || echo 0)
        TOTAL_PREFIX_HITS=$(python3 -c "import json; print(json.load(open('$STATS_FILE')).get('total_prefix_hits', 0))" 2>/dev/null || echo 0)
        TOTAL_BLOOM_PASSES=$(python3 -c "import json; print(json.load(open('$STATS_FILE')).get('total_bloom_passes', 0))" 2>/dev/null || echo 0)
        BATCH_COUNT=$(python3 -c "import json; print(json.load(open('$STATS_FILE')).get('batch_count', 0))" 2>/dev/null || echo 0)
        log "Resumed: ${TOTAL_KEYS} keys, ${TOTAL_PREFIX_HITS} prefix hits, ${TOTAL_BLOOM_PASSES} bloom passes"
    else
        log "${YELLOW}Starting fresh session${NC}"
    fi
}

# Save stats for persistence
save_stats() {
    local now=$(date +%s)
    local elapsed=$((now - SESSION_START))
    local rate=0
    if [ $elapsed -gt 0 ]; then
        rate=$((TOTAL_KEYS / elapsed))
    fi

    python3 << PYEOF
import json
from datetime import datetime
stats = {
    'total_keys': $TOTAL_KEYS,
    'total_prefix_hits': $TOTAL_PREFIX_HITS,
    'total_bloom_passes': $TOTAL_BLOOM_PASSES,
    'batch_count': $BATCH_COUNT,
    'restart_count': $RESTART_COUNT,
    'session_start': $SESSION_START,
    'last_update': datetime.now().isoformat(),
    'elapsed_seconds': $elapsed,
    'average_rate_keys_per_sec': $rate
}
with open('$STATS_FILE', 'w') as f:
    json.dump(stats, f, indent=2)
PYEOF
}

# Parse output from bloom_gpu_search
parse_output() {
    local output="$1"

    # Extract stats from output
    # Format: "Total keys checked: 54703500000000"
    local keys=$(echo "$output" | grep "Total keys checked:" | awk '{print $4}' | tr -d ',')
    local prefix=$(echo "$output" | grep "Prefix bitmap hits:" | awk '{print $4}' | tr -d ',')
    local bloom=$(echo "$output" | grep "Bloom filter passes:" | awk '{print $4}' | tr -d ',')

    if [ -n "$keys" ] && [ "$keys" -gt 0 ] 2>/dev/null; then
        TOTAL_KEYS=$((TOTAL_KEYS + keys))
    fi
    if [ -n "$prefix" ] && [ "$prefix" -gt 0 ] 2>/dev/null; then
        TOTAL_PREFIX_HITS=$((TOTAL_PREFIX_HITS + prefix))
    fi
    if [ -n "$bloom" ] && [ "$bloom" -gt 0 ] 2>/dev/null; then
        TOTAL_BLOOM_PASSES=$((TOTAL_BLOOM_PASSES + bloom))
        # Log potential matches
        log "${RED}!!! ${bloom} BLOOM FILTER PASSES THIS BATCH !!!${NC}"
        echo "$(date -Iseconds) | Bloom passes: $bloom | Total keys: $TOTAL_KEYS" >> "$FOUND_FILE"
    fi
}

# Check if binary exists and is built
check_binary() {
    if [ ! -f "$SEARCH_BIN" ]; then
        log "${YELLOW}Binary not found, attempting to build...${NC}"
        cd "$SCRIPT_DIR"
        make -f Makefile bloom_gpu_search 2>&1 | tee -a "$LOG_FILE"
        if [ ! -f "$SEARCH_BIN" ]; then
            log "${RED}ERROR: Failed to build bloom_gpu_search${NC}"
            return 1
        fi
    fi
    return 0
}

# Check if filter files exist
check_filters() {
    if [ ! -f "$PREFIX_FILE" ]; then
        log "${RED}ERROR: Prefix bitmap not found: $PREFIX_FILE${NC}"
        return 1
    fi
    if [ ! -f "$BLOOM_FILE" ]; then
        log "${RED}ERROR: Bloom filter not found: $BLOOM_FILE${NC}"
        return 1
    fi
    return 0
}

# Run a single search batch
run_batch() {
    local batch_num=$1
    log_stats "Starting batch #$batch_num (${RUN_TIME}s runtime)"

    # Run the search
    local output
    output=$("$SEARCH_BIN" "$PREFIX_FILE" "$BLOOM_FILE" -g "$GPU_IDS" -t "$RUN_TIME" 2>&1)
    local exit_code=$?

    # Log raw output for debugging
    echo "$output" >> "$LOG_FILE"

    if [ $exit_code -ne 0 ]; then
        log "${RED}Batch #$batch_num exited with code $exit_code${NC}"
        return 1
    fi

    # Parse and accumulate stats
    parse_output "$output"

    # Calculate session rate
    local now=$(date +%s)
    local elapsed=$((now - SESSION_START))
    local rate=0
    if [ $elapsed -gt 0 ] && [ $TOTAL_KEYS -gt 0 ]; then
        rate=$(python3 -c "print(f'{$TOTAL_KEYS / $elapsed / 1e9:.2f}')")
    fi

    log_stats "Batch #$batch_num complete | Total: ${TOTAL_KEYS} keys | Prefix: ${TOTAL_PREFIX_HITS} | Bloom: ${TOTAL_BLOOM_PASSES} | Rate: ${rate} GKey/s"

    return 0
}

# Check restart rate limit
check_restart_limit() {
    local current_hour=$(date +%H)
    if [ "$current_hour" != "$LAST_RESTART_HOUR" ]; then
        LAST_RESTART_HOUR=$current_hour
        RESTARTS_THIS_HOUR=0
    fi

    if [ $RESTARTS_THIS_HOUR -ge $MAX_RESTARTS_PER_HOUR ]; then
        log "${RED}ERROR: Too many restarts this hour ($RESTARTS_THIS_HOUR). Waiting for next hour...${NC}"
        sleep 3600
        RESTARTS_THIS_HOUR=0
    fi
}

# Main search loop
main_loop() {
    log "${BLUE}========================================${NC}"
    log "${BLUE}  Persistent GPU Bloom Filter Search   ${NC}"
    log "${BLUE}========================================${NC}"
    log "Binary: $SEARCH_BIN"
    log "Prefix: $PREFIX_FILE"
    log "Bloom:  $BLOOM_FILE"
    log "GPUs:   $GPU_IDS"
    log "Batch:  ${RUN_TIME}s per batch"
    log ""

    # Check prerequisites
    check_binary || exit 1
    check_filters || exit 1

    # Load previous stats
    load_stats

    # Save PID
    echo $$ > "$PID_FILE"

    # Trap for graceful shutdown
    trap 'log "${YELLOW}Received shutdown signal...${NC}"; save_stats; log "Stats saved. Goodbye!"; exit 0' SIGINT SIGTERM

    log "${GREEN}Starting infinite search loop...${NC}"
    log "Press Ctrl+C to stop gracefully"
    log ""

    while true; do
        BATCH_COUNT=$((BATCH_COUNT + 1))

        if run_batch $BATCH_COUNT; then
            # Success - save stats
            save_stats
        else
            # Failure - increment restart counter and retry
            RESTART_COUNT=$((RESTART_COUNT + 1))
            RESTARTS_THIS_HOUR=$((RESTARTS_THIS_HOUR + 1))
            log "${RED}Batch failed. Restart #$RESTART_COUNT${NC}"

            check_restart_limit

            log "${YELLOW}Restarting in 10 seconds...${NC}"
            sleep 10

            # Re-check binary in case it was corrupted
            check_binary || {
                log "${RED}Binary check failed after restart. Waiting 60s...${NC}"
                sleep 60
            }
        fi

        # Brief pause between batches
        sleep 2
    done
}

# Entry point
main() {
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local old_pid=$(cat "$PID_FILE")
        if kill -0 "$old_pid" 2>/dev/null; then
            log "${YELLOW}Search already running with PID $old_pid${NC}"
            log "Use 'kill $old_pid' to stop it first"
            exit 1
        else
            log "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi

    main_loop
}

main "$@"
