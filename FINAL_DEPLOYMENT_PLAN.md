# Server 2: Save Progress & Deploy 4 New Ranges - COMPLETE PLAN

## Executive Summary

**Goal**: Save Server 2's current K3 search progress and start 4 new independent range searches

**Strategy**: Copy K3 files to separate folders (K3_range1-4), preserving original search

**Server 2 Access**:
- Primary: `root@5.78.98.156` (currently timeout)
- Alternate: `root@173.180.134.131 -p 35952` (requires SSH key setup)

---

## The 4 New Ranges

```
Range 1: 11494219353108143562991068411194509532350831987680500254629221556744305000000000
Range 2: 11494219353108143562991068411194509532350831987680500254629221506744305000000000
Range 3: 81979563453356770746037359084754162925559246477171714229961496311613000000000
Range 4: 81979563453356770746037359084754162925559246477171714229960496311613000000000
```

**Note**:
- Ranges 1 & 2 differ at position: ...556... vs ...506...
- Ranges 3 & 4 differ at position: ...961... vs ...960...

---

## Quick Start (Once SSH Access is Working)

### Single Command Deployment

```bash
./save_and_deploy_server2.sh
```

This one script does **everything**:
1. ✅ Auto-detects working Server 2 connection
2. ✅ Backs up original K3 search progress
3. ✅ Deploys all 4 new ranges in separate folders
4. ✅ Downloads backup locally
5. ✅ Provides start commands

---

## What Gets Created on Server 2

### Before:
```
~/K3/                 # Original search
  ├── K3_OpenCL
  ├── bloom.bin
  ├── config.txt      # Current range
  ├── continue_*.txt  # Current progress
  └── results...
```

### After:
```
~/K3/                           # Original (untouched)
~/K3_backup_original_YYYYMMDD/  # Complete backup of original
~/K3_range1/                    # New Range 1 search
  ├── K3_OpenCL
  ├── bloom.bin
  ├── config.txt
  ├── start_search.sh
  └── search.log (when running)
~/K3_range2/                    # New Range 2 search
~/K3_range3/                    # New Range 3 search
~/K3_range4/                    # New Range 4 search
```

---

## Step-by-Step Manual Process

If you prefer to do it manually or the automated script doesn't work:

### 1. Setup SSH Access (if needed)

```bash
# Add your SSH key to vast.ai dashboard, then test:
ssh -p 35952 root@173.180.134.131 "hostname"
```

### 2. Backup Original Search

```bash
SERVER="root@173.180.134.131"
PORT=35952
BACKUP="K3_backup_original_$(date +%Y%m%d_%H%M%S)"

# Create backup
ssh -p $PORT $SERVER "mkdir -p ~/$BACKUP"
ssh -p $PORT $SERVER "cd K3 && cp config.txt continue_*.txt result*.txt candidates*.txt ~/$BACKUP/ 2>/dev/null"

# Download locally
scp -r -P $PORT $SERVER:~/$BACKUP /root/repo/server2_backups/
```

### 3. Deploy Each Range

```bash
for i in 1 2 3 4; do
    ssh -p $PORT $SERVER "mkdir -p ~/K3_range${i}"
    ssh -p $PORT $SERVER "cp ~/K3/K3_OpenCL ~/K3_range${i}/"
    ssh -p $PORT $SERVER "cp ~/K3/bloom.bin ~/K3_range${i}/"
    scp -P $PORT /root/repo/new_ranges/range${i}_config.txt $SERVER:~/K3_range${i}/config.txt
done
```

### 4. Start All Searches

```bash
ssh -p $PORT $SERVER << 'EOF'
cd ~/K3_range1 && nohup ./K3_OpenCL > search.log 2>&1 &
cd ~/K3_range2 && nohup ./K3_OpenCL > search.log 2>&1 &
cd ~/K3_range3 && nohup ./K3_OpenCL > search.log 2>&1 &
cd ~/K3_range4 && nohup ./K3_OpenCL > search.log 2>&1 &
ps aux | grep K3_OpenCL
EOF
```

---

## Monitoring & Management

### Check All Searches

```bash
# View all running K3 processes
ssh -p 35952 root@173.180.134.131 'ps aux | grep K3_OpenCL'

# Monitor all logs simultaneously
ssh -p 35952 root@173.180.134.131 'tail -f K3_range*/search.log'

# Check for results in all ranges
ssh -p 35952 root@173.180.134.131 'cat K3_range*/result*.txt'
```

### Check Individual Range

```bash
# Range 1
ssh -p 35952 root@173.180.134.131 'tail -100 K3_range1/search.log'

# Range 2
ssh -p 35952 root@173.180.134.131 'tail -100 K3_range2/search.log'

# And so on...
```

### Stop All New Searches

```bash
ssh -p 35952 root@173.180.134.131 'pkill -f K3_range'
```

### Stop Individual Range

```bash
ssh -p 35952 root@173.180.134.131 'pkill -f K3_range1'
```

---

## Resume Original Search Later

When you want to go back to the original search:

```bash
# 1. Stop new searches
ssh -p 35952 root@173.180.134.131 'pkill -f K3_range'

# 2. Restore from backup
BACKUP_DIR="K3_backup_original_20260123_XXXXXX"  # Use actual timestamp
scp -r -P 35952 /root/repo/server2_backups/$BACKUP_DIR/* root@173.180.134.131:~/K3/

# 3. Resume with --continue flag
ssh -p 35952 root@173.180.134.131 'cd ~/K3 && nohup ./K3_OpenCL --continue > search.log 2>&1 &'
```

---

## Files Created

All ready to use:

```
✅ save_and_deploy_server2.sh        - All-in-one automated script
✅ new_ranges/range1_config.txt      - Range 1 configuration
✅ new_ranges/range2_config.txt      - Range 2 configuration
✅ new_ranges/range3_config.txt      - Range 3 configuration
✅ new_ranges/range4_config.txt      - Range 4 configuration
✅ SETUP_SERVER2_ACCESS.md           - SSH access setup guide
✅ FINAL_DEPLOYMENT_PLAN.md          - This comprehensive guide
```

---

## FAQ

**Q: Will the original search be lost?**
A: No! It's backed up before any changes and can be resumed anytime.

**Q: Can all 4 ranges run simultaneously?**
A: Yes! Each runs in its own directory with its own process.

**Q: How much GPU memory will this use?**
A: Each range loads one bloom filter copy (~same memory as current). Should work fine.

**Q: What if I want to run only 2 ranges instead of 4?**
A: Just deploy the ranges you want. You don't have to deploy all 4.

**Q: How do I know which range found a match?**
A: Check the `result*.txt` file in each K3_range* directory.

**Q: Can I add more ranges later?**
A: Yes! Just create range5_config.txt and deploy to K3_range5.

---

## Troubleshooting

**Connection Issues**
- Ensure vast.ai instance is running (check dashboard)
- Verify SSH key is added to vast.ai
- Try alternate connection: `ssh root@5.78.98.156` vs `ssh -p 35952 root@173.180.134.131`

**Script Fails**
- Check SSH access first: `ssh -p 35952 root@173.180.134.131 "ls ~/K3"`
- Run manual steps if automated script has issues
- Verify all config files exist: `ls /root/repo/new_ranges/`

**Searches Not Starting**
- Check K3_OpenCL exists: `ssh -p 35952 root@173.180.134.131 "ls -l ~/K3_range*/K3_OpenCL"`
- Check bloom filter exists: `ssh -p 35952 root@173.180.134.131 "ls -lh ~/K3_range*/bloom.bin"`
- Check logs: `ssh -p 35952 root@173.180.134.131 "cat ~/K3_range1/search.log"`

---

## Next Steps

1. **Setup SSH Access** to Server 2 (see SETUP_SERVER2_ACCESS.md)
2. **Run**: `./save_and_deploy_server2.sh`
3. **Verify**: All 4 ranges are running
4. **Monitor**: Watch for results

Your original search is safe, and 4 new ranges will be searching!
