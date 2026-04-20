#!/bin/bash
#
# Continuous BloomSearch Runner with Crash Recovery
# Automatically restarts on crash and resumes from checkpoint
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLOOM_FILE="$SCRIPT_DIR/btc_addresses.bloom"
CHECKPOINT_FILE="$SCRIPT_DIR/checkpoint.json"
FOUND_FILE="$SCRIPT_DIR/found_matches.txt"
LOG_FILE="$SCRIPT_DIR/search.log"
PID_FILE="$SCRIPT_DIR/search.pid"
VANITYSEARCH="/workspace/Bot/vanitysearch_analysis/VanitySearch"
TEMP_OUTPUT="$SCRIPT_DIR/vanity_temp.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') | $1" | tee -a "$LOG_FILE"
}

# Initialize or load checkpoint
init_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        log "${GREEN}Loading checkpoint...${NC}"
        KEYS_CHECKED=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE')).get('keys_checked', 0))")
        BLOOM_MATCHES=$(python3 -c "import json; print(json.load(open('$CHECKPOINT_FILE')).get('bloom_matches', 0))")
        log "Resuming from: $KEYS_CHECKED keys checked, $BLOOM_MATCHES matches"
    else
        KEYS_CHECKED=0
        BLOOM_MATCHES=0
        log "${YELLOW}Starting fresh search${NC}"
    fi
    START_TIME=$(date -Iseconds)
}

# Save checkpoint
save_checkpoint() {
    python3 << PYEOF
import json
from datetime import datetime
checkpoint = {
    'keys_checked': ,
    'bloom_matches': ,
    'start_time': '',
    'last_update': datetime.now().isoformat()
}
with open('', 'w') as f:
    json.dump(checkpoint, f, indent=2)
PYEOF
}

# Check bloom filter for matches
check_bloom() {
    local addr="$1"
    local privkey="$2"
    local hex="$3"
    
    result=$(echo "$addr" | python3 "$SCRIPT_DIR/bloom_verifier.py" "$BLOOM_FILE" 2>/dev/null | grep -c "MATCH" || true)
    
    if [ "$result" -gt 0 ]; then
        ((BLOOM_MATCHES++))
        log "${RED}!!! BLOOM MATCH FOUND !!!${NC}"
        log "Address: $addr"
        log "PrivKey: $privkey"
        echo "$(date -Iseconds) | $addr | $privkey | $hex" >> "$FOUND_FILE"
        
        # Send notification (if configured)
        # curl -X POST "webhook_url" -d "Found: $addr"
    fi
}

# Parse VanitySearch output
parse_output() {
    if [ -f "$TEMP_OUTPUT" ]; then
        while IFS= read -r line; do
            if [[ "$line" == PubAddress:* ]]; then
                addr=$(echo "$line" | awk '{print $2}')
            elif [[ "$line" == *"Priv (WIF):"* ]]; then
                privkey=$(echo "$line" | awk '{print $3}')
            elif [[ "$line" == *"Priv (HEX):"* ]]; then
                hex=$(echo "$line" | awk '{print $3}')
                if [ -n "$addr" ] && [ -n "$privkey" ]; then
                    check_bloom "$addr" "$privkey" "$hex"
                    ((KEYS_CHECKED++))
                fi
            fi
        done < "$TEMP_OUTPUT"
        rm -f "$TEMP_OUTPUT"
    fi
}

# Main search loop
run_search() {
    log "${BLUE}========================================${NC}"
    log "${BLUE}BloomSearch Continuous Runner${NC}"
    log "${BLUE}========================================${NC}"
    log "Bloom filter: $BLOOM_FILE"
    log "VanitySearch: $VANITYSEARCH"
    log "Output file: $FOUND_FILE"
    log ""
    
    # Check prerequisites
    if [ ! -f "$BLOOM_FILE" ]; then
        log "${RED}ERROR: Bloom filter not found!${NC}"
        exit 1
    fi
    
    if [ ! -f "$VANITYSEARCH" ]; then
        log "${RED}ERROR: VanitySearch not found!${NC}"
        exit 1
    fi
    
    init_checkpoint
    
    # Save PID for monitoring
    echo $$ > "$PID_FILE"
    
    BATCH_COUNT=0
    LAST_SAVE=$(date +%s)
    
    cd /workspace/Bot/vanitysearch_analysis
    
    log "${GREEN}Starting GPU search on all GPUs...${NC}"
    log "Press Ctrl+C to stop gracefully"
    log ""
    
    # Trap for graceful shutdown
    trap 'log "Shutting down..."; save_checkpoint; exit 0' SIGINT SIGTERM
    
    while true; do
        # Run VanitySearch batch - search for common prefix to generate keys
        # Using short prefix "1" to maximize key generation
        timeout 30 ./VanitySearch -gpu -gpuId 0,1,2,3 -o "$TEMP_OUTPUT" -t 0 -stop 1 2>/dev/null || true
        
        # Parse results and check bloom filter
        parse_output
        
        ((BATCH_COUNT++))
        
        # Save checkpoint every 10 seconds
        NOW=$(date +%s)
        if [ $((NOW - LAST_SAVE)) -ge 10 ]; then
            save_checkpoint
            LAST_SAVE=$NOW
            
            # Calculate rate
            ELAPSED=$((NOW - $(date -d "$START_TIME" +%s)))
            if [ $ELAPSED -gt 0 ]; then
                RATE=$((KEYS_CHECKED / ELAPSED))
            else
                RATE=0
            fi
            
            log "Batch $BATCH_COUNT | Keys: $KEYS_CHECKED | Matches: $BLOOM_MATCHES | Rate: $RATE keys/s"
        fi
    done
}

# Wrapper with auto-restart
main() {
    while true; do
        log "${GREEN}Starting search process...${NC}"
        run_search || {
            log "${RED}Search crashed! Restarting in 5 seconds...${NC}"
            sleep 5
        }
    done
}

main
