#!/bin/bash
# Complete script to save Server 2's progress and deploy 4 new ranges

# Server 2 connection (use whichever works)
SERVER2_PRIMARY="root@5.78.98.156"
SERVER2_ALTERNATE="root@173.180.134.131"
SERVER2_PORT="35952"

# Try to determine which connection works
echo "=== Checking Server 2 Connectivity ==="
if ssh -o ConnectTimeout=5 "$SERVER2_PRIMARY" "echo 'Connected'" 2>/dev/null; then
    SERVER2="$SERVER2_PRIMARY"
    SSH_OPTS=""
    echo "✓ Connected via primary address: $SERVER2_PRIMARY"
elif ssh -p "$SERVER2_PORT" -o ConnectTimeout=5 "$SERVER2_ALTERNATE" "echo 'Connected'" 2>/dev/null; then
    SERVER2="$SERVER2_ALTERNATE"
    SSH_OPTS="-p $SERVER2_PORT"
    echo "✓ Connected via alternate address: $SERVER2_ALTERNATE:$SERVER2_PORT"
else
    echo "✗ Error: Cannot connect to Server 2"
    echo "Please ensure SSH access is configured for one of:"
    echo "  - $SERVER2_PRIMARY"
    echo "  - $SERVER2_ALTERNATE -p $SERVER2_PORT"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="K3_backup_original_${TIMESTAMP}"

echo ""
echo "=== Step 1: Saving Server 2's Current Progress ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Create backup directory
echo "1. Creating backup directory: $BACKUP_DIR"
ssh $SSH_OPTS $SERVER2 "mkdir -p ~/$BACKUP_DIR"

# Save current config
echo "2. Saving config.txt (exact range positions)..."
ssh $SSH_OPTS $SERVER2 "cd K3 && cp config.txt ~/$BACKUP_DIR/ 2>/dev/null || echo 'Warning: config.txt not found'"

# Save continue files (exact GPU positions)
echo "3. Saving continue files (per-GPU progress)..."
ssh $SSH_OPTS $SERVER2 "cd K3 && cp continue_*.txt ~/$BACKUP_DIR/ 2>/dev/null || echo 'Info: No continue files found'"

# Save results
echo "4. Saving all result and candidate files..."
ssh $SSH_OPTS $SERVER2 "cd K3 && cp result*.txt ~/$BACKUP_DIR/ 2>/dev/null || true"
ssh $SSH_OPTS $SERVER2 "cd K3 && cp candidates*.txt ~/$BACKUP_DIR/ 2>/dev/null || true"
ssh $SSH_OPTS $SERVER2 "cd K3 && cp *_compressed.txt ~/$BACKUP_DIR/ 2>/dev/null || true"

# Save bloom filter info
echo "5. Documenting bloom filter..."
ssh $SSH_OPTS $SERVER2 "cd K3 && ls -lh bloom*.bin > ~/$BACKUP_DIR/bloom_info.txt 2>/dev/null || true"

# Save recent logs
echo "6. Saving recent search logs..."
ssh $SSH_OPTS $SERVER2 "cd K3 && tail -500 nohup.out > ~/$BACKUP_DIR/last_search_output.txt 2>/dev/null || tail -500 search.log > ~/$BACKUP_DIR/last_search_output.txt 2>/dev/null || true"

# List all processes
echo "7. Documenting running processes..."
ssh $SSH_OPTS $SERVER2 "ps aux | grep K3 > ~/$BACKUP_DIR/running_processes.txt"

# Create summary
echo "8. Creating backup summary..."
ssh $SSH_OPTS $SERVER2 "cat > ~/$BACKUP_DIR/README.txt << 'EOFREADME'
Server 2 K3 Search Progress Backup
===================================
Created: $TIMESTAMP

This backup contains the complete state of Server 2's original K3 search.

IMPORTANT FILES:
- config.txt: Original range start/end positions
- continue_*.txt: Exact per-GPU progress (can resume from here)
- result*.txt: Any matched keys found
- candidates*.txt: Bloom filter candidates
- last_search_output.txt: Recent search output logs
- running_processes.txt: Processes that were running at backup time

TO RESUME THIS SEARCH LATER:
1. Stop any new searches in K3_range* directories
2. Copy all files from this backup back to ~/K3/
3. Run: cd ~/K3 && ./K3_OpenCL --continue
4. The search will resume from the exact last position saved

Original search safely preserved!
EOFREADME
"

# Download backup locally
echo "9. Downloading backup to local machine..."
mkdir -p /root/repo/server2_backups
if [ -n "$SSH_OPTS" ]; then
    scp -r $SSH_OPTS $SERVER2:~/$BACKUP_DIR /root/repo/server2_backups/
else
    scp -r $SERVER2:~/$BACKUP_DIR /root/repo/server2_backups/
fi

echo ""
echo "=== Step 2: Deploying 4 New Ranges ==="
echo ""

# Copy K3 executable and bloom filter to new range directories
for i in 1 2 3 4; do
    RANGE_DIR="K3_range${i}"
    echo "Setting up $RANGE_DIR..."

    # Create directory
    ssh $SSH_OPTS $SERVER2 "mkdir -p ~/$RANGE_DIR"

    # Copy executable
    ssh $SSH_OPTS $SERVER2 "cp ~/K3/K3_OpenCL ~/$RANGE_DIR/ && chmod +x ~/$RANGE_DIR/K3_OpenCL"

    # Copy bloom filter
    ssh $SSH_OPTS $SERVER2 "cp ~/K3/bloom.bin ~/$RANGE_DIR/"

    # Upload config
    if [ -n "$SSH_OPTS" ]; then
        scp $SSH_OPTS "/root/repo/new_ranges/range${i}_config.txt" "$SERVER2:~/$RANGE_DIR/config.txt"
    else
        scp "/root/repo/new_ranges/range${i}_config.txt" "$SERVER2:~/$RANGE_DIR/config.txt"
    fi

    # Create start script
    ssh $SSH_OPTS $SERVER2 "cat > ~/$RANGE_DIR/start_search.sh << 'EOFSTART'
#!/bin/bash
cd ~/K3_range${i}
nohup ./K3_OpenCL > search.log 2>&1 &
echo \"K3 range ${i} search started\"
echo \"PID: \$!\"
echo \"View logs: tail -f ~/K3_range${i}/search.log\"
EOFSTART
"
    ssh $SSH_OPTS $SERVER2 "chmod +x ~/$RANGE_DIR/start_search.sh"

    echo "  ✓ $RANGE_DIR ready"
done

echo ""
echo "=== Complete! ==="
echo ""
echo "BACKUP LOCATION:"
echo "  Remote: $SERVER2:~/$BACKUP_DIR"
echo "  Local:  /root/repo/server2_backups/$BACKUP_DIR"
echo ""
echo "NEW RANGES DEPLOYED:"
echo "  ~/K3_range1 - Range 1"
echo "  ~/K3_range2 - Range 2"
echo "  ~/K3_range3 - Range 3"
echo "  ~/K3_range4 - Range 4"
echo ""
echo "TO START ALL 4 NEW SEARCHES:"
if [ -n "$SSH_OPTS" ]; then
    echo "  ssh $SSH_OPTS $SERVER2 'cd K3_range1 && ./start_search.sh'"
    echo "  ssh $SSH_OPTS $SERVER2 'cd K3_range2 && ./start_search.sh'"
    echo "  ssh $SSH_OPTS $SERVER2 'cd K3_range3 && ./start_search.sh'"
    echo "  ssh $SSH_OPTS $SERVER2 'cd K3_range4 && ./start_search.sh'"
else
    echo "  ssh $SERVER2 'cd K3_range1 && ./start_search.sh'"
    echo "  ssh $SERVER2 'cd K3_range2 && ./start_search.sh'"
    echo "  ssh $SERVER2 'cd K3_range3 && ./start_search.sh'"
    echo "  ssh $SERVER2 'cd K3_range4 && ./start_search.sh'"
fi
echo ""
echo "TO MONITOR ALL RANGES:"
if [ -n "$SSH_OPTS" ]; then
    echo "  ssh $SSH_OPTS $SERVER2 'tail -f K3_range*/search.log'"
else
    echo "  ssh $SERVER2 'tail -f K3_range*/search.log'"
fi
echo ""
echo "Original K3 directory preserved - can resume anytime from backup!"
echo ""
