#!/bin/bash
# Script to save Server 2's current progress before starting new ranges

SERVER="root@5.78.98.156"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="K3_backup_${TIMESTAMP}"

echo "=== Saving Server 2 Progress ==="
echo "Timestamp: $TIMESTAMP"
echo ""

# Create backup directory on server
ssh $SERVER "cd ~ && mkdir -p $BACKUP_DIR"

# Save current configuration
echo "1. Saving config.txt..."
ssh $SERVER "cd K3 && cp config.txt ~/$BACKUP_DIR/"

# Save continue files (track exact position per GPU)
echo "2. Saving continue files..."
ssh $SERVER "cd K3 && cp continue_*.txt ~/$BACKUP_DIR/ 2>/dev/null || true"

# Save any result files
echo "3. Saving result files..."
ssh $SERVER "cd K3 && cp result*.txt ~/$BACKUP_DIR/ 2>/dev/null || true"
ssh $SERVER "cd K3 && cp candidates*.txt ~/$BACKUP_DIR/ 2>/dev/null || true"

# Save bloom filter info
echo "4. Saving bloom filter info..."
ssh $SERVER "cd K3 && ls -lh bloom*.bin > ~/$BACKUP_DIR/bloom_info.txt"

# Save current search statistics
echo "5. Saving search statistics..."
ssh $SERVER "cd K3 && tail -100 nohup.out > ~/$BACKUP_DIR/last_search_output.txt 2>/dev/null || true"

# Create a summary file
echo "6. Creating summary..."
ssh $SERVER "cat > ~/$BACKUP_DIR/RANGE_INFO.txt << 'EOFINFO'
Server 2 K3 Search Progress Backup
Created: $TIMESTAMP

This backup contains the exact state of Server 2's K3 search to allow resumption later.

Files included:
- config.txt: Main configuration with range start/end
- continue_*.txt: Per-GPU progress tracking
- result*.txt: Any found matches
- candidates*.txt: Bloom filter candidates
- bloom_info.txt: Bloom filter file information
- last_search_output.txt: Recent search output

To resume this search:
1. Copy these files back to K3/ directory
2. Run: ./K3_OpenCL --continue
3. The search will resume from the last saved position

Range being searched: See config.txt for exact values
EOFINFO
"

# Download backup locally
echo "7. Downloading backup to local machine..."
mkdir -p /root/repo/server2_backups
scp -r $SERVER:~/$BACKUP_DIR /root/repo/server2_backups/

echo ""
echo "=== Backup Complete ==="
echo "Remote backup: ~/$BACKUP_DIR on Server 2"
echo "Local backup: /root/repo/server2_backups/$BACKUP_DIR"
echo ""
echo "Current range preserved. Ready to start new ranges!"
