# Server 2: 4 New Ranges - READY TO LAUNCH! ✅

## Summary

✅ **Original search backed up** to `/root/repo/server2_backups/K3_backup_original_20260123_223401`
✅ **All 4 range scripts created and uploaded** to Server 2
✅ **Ready to start** 4 new independent range searches

---

## Current Status

### Server 2 Current State
- **4 GPUs** currently running original search ranges
- **463.86T keys** searched so far
- **State files backed up** (exact positions saved)
- **All bloom filters and executables** already in place

### Backup Location
- **Remote**: `root@173.180.134.131:35952/~/K3_backup_original_20260123_223401`
- **Local**: `/root/repo/server2_backups/K3_backup_original_20260123_223401`
- **Size**: 129MB (includes all state files, logs, and scripts)

---

## The 4 New Ranges

Each range will run on its own dedicated GPU:

```
Range 1 → GPU 0: 11494219353108143562991068411194509532350831987680500254629221556744305000000000
Range 2 → GPU 1: 11494219353108143562991068411194509532350831987680500254629221506744305000000000
Range 3 → GPU 2: 81979563453356770746037359084754162925559246477171714229961496311613000000000
Range 4 → GPU 3: 81979563453356770746037359084754162925559246477171714229960496311613000000000
```

---

## Launch Commands

### Option 1: Launch All 4 Ranges at Once (Recommended)

```bash
ssh terragon-server2 './launch_all_4_ranges.sh'
```

This will:
1. Stop current searches
2. Start all 4 new ranges simultaneously
3. Show running processes
4. Display monitoring commands

### Option 2: Launch Ranges Individually

```bash
# Stop current searches first
ssh terragon-server2 'pkill -f BloomSearch32K3'

# Launch each range
ssh terragon-server2 './launch_range1.sh'
ssh terragon-server2 './launch_range2.sh'
ssh terragon-server2 './launch_range3.sh'
ssh terragon-server2 './launch_range4.sh'
```

---

## Monitoring

### View All Range Logs Simultaneously

```bash
ssh terragon-server2 'tail -f /root/range*_search.log'
```

### View Individual Range Logs

```bash
# Range 1
ssh terragon-server2 'tail -f /root/range1_search.log'

# Range 2
ssh terragon-server2 'tail -f /root/range2_search.log'

# Range 3
ssh terragon-server2 'tail -f /root/range3_search.log'

# Range 4
ssh terragon-server2 'tail -f /root/range4_search.log'
```

### Check Running Processes

```bash
ssh terragon-server2 'ps aux | grep BloomSearch32K3 | grep -v grep'
```

### Check Progress and Candidates

```bash
# View last 50 lines of each log
ssh terragon-server2 'tail -50 /root/range*_search.log'

# Search for actual matches (not just candidates)
ssh terragon-server2 'grep -i "MATCH\|FOUND\|SUCCESS" /root/range*_search.log'
```

---

## File Locations on Server 2

```
~/launch_all_4_ranges.sh    - Master launch script (all 4 ranges)
~/launch_range1.sh           - Individual range 1 launcher
~/launch_range2.sh           - Individual range 2 launcher
~/launch_range3.sh           - Individual range 3 launcher
~/launch_range4.sh           - Individual range 4 launcher

~/launch_k3_4gpu.sh          - Original launch script (backed up)

~/K3_backup_original_*/      - Complete backup of original search

/root/range1_search.log      - Range 1 output log
/root/range2_search.log      - Range 2 output log
/root/range3_search.log      - Range 3 output log
/root/range4_search.log      - Range 4 output log

/tmp/range1.state            - Range 1 state (auto-created)
/tmp/range2.state            - Range 2 state (auto-created)
/tmp/range3.state            - Range 3 state (auto-created)
/tmp/range4.state            - Range 4 state (auto-created)

/workspace/k3/BloomSearch32K3  - K3 executable
/root/bloom_55m.prefix32       - Bloom filter prefix
/root/bloom_k3_standard.bloom  - Bloom filter data
/root/bloom_k3_standard.seeds  - Bloom filter seeds
```

---

## Management Commands

### Stop All New Range Searches

```bash
ssh terragon-server2 'pkill -f BloomSearch32K3'
```

### Stop Individual Range

```bash
# Find PIDs
ssh terragon-server2 'ps aux | grep "gpu 0"'  # Range 1
ssh terragon-server2 'ps aux | grep "gpu 1"'  # Range 2
ssh terragon-server2 'ps aux | grep "gpu 3"'  # Range 3
ssh terragon-server2 'ps aux | grep "gpu 4"'  # Range 4

# Kill specific PID
ssh terragon-server2 'kill <PID>'
```

### Resume Original Search (From Backup)

```bash
# Stop new ranges
ssh terragon-server2 'pkill -f BloomSearch32K3'

# Restore state files
ssh terragon-server2 'cp ~/K3_backup_original_20260123_223401/gpu*.state /tmp/'

# Launch original search
ssh terragon-server2 './launch_k3_4gpu.sh'
```

---

## Expected Output

When ranges are running, you should see output like:

```
[K3 CANDIDATE UNCOMP] tid=XXXXX meta=XXXXX hash160=XXXXX...
[K3 XXXXs] XXX.XXT keys | X.XX GKey/s | XXXXX candidates
```

Each GPU should process at approximately:
- **5-6 GKey/s** per GPU
- **~20-24 GKey/s total** across all 4 GPUs

---

## Important Notes

1. **Original search is preserved**: All state files backed up with exact positions
2. **State files are critical**: They contain the exact current position of each search
3. **Independent ranges**: Each range runs on its own GPU with its own state file
4. **No data loss**: Original search can be resumed anytime from backup
5. **Bloom filters shared**: All ranges use the same bloom filter files (no extra memory needed)

---

## Quick Reference

| Action | Command |
|--------|---------|
| Launch all 4 ranges | `ssh terragon-server2 './launch_all_4_ranges.sh'` |
| Monitor all logs | `ssh terragon-server2 'tail -f /root/range*_search.log'` |
| Check processes | `ssh terragon-server2 'ps aux \| grep BloomSearch32K3'` |
| Stop all searches | `ssh terragon-server2 'pkill -f BloomSearch32K3'` |
| Resume original | `ssh terragon-server2 './launch_k3_4gpu.sh'` |

---

## Next Steps

**You're ready to deploy!** Just run:

```bash
ssh terragon-server2 './launch_all_4_ranges.sh'
```

Then monitor progress with:

```bash
ssh terragon-server2 'tail -f /root/range*_search.log'
```

Your original search is safely backed up and can be resumed anytime. All 4 new ranges will search their specific target keys independently!
