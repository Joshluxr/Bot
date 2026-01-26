# K3 New Range Deployment Guide

## Overview
This guide explains how to save Server 2's current progress and deploy 4 new search ranges.

## Step 1: Save Server 2's Current Progress

**When Server 2 is accessible**, run this script to backup its current state:

```bash
./save_server2_progress.sh
```

This will:
- Create a timestamped backup directory on Server 2
- Save `config.txt` (exact range positions)
- Save `continue_*.txt` files (per-GPU progress)
- Save all result and candidate files
- Download everything locally to `/root/repo/server2_backups/`

**Your current progress will be preserved and can be resumed anytime!**

## Step 2: Deploy New Ranges

### Available Ranges

**Range 1:**
- Start: `11494219353108143562991068411194509532350831987680500254629221506744305000000000`
- End:   `11494219353108143562991068411194509532350831987680500254629221556744305000000000`
- Size:  50 billion keys

**Range 2:**
- Start: `81979563453356770746037359084754162925559246477171714229960496311613000000000`
- End:   `81979563453356770746037359084754162925559246477171714229961496311613000000000`
- Size:  1 trillion keys

### Deployment Commands

**Deploy Range 1 to Server 2:**
```bash
./deploy_new_ranges.sh server2 range1
```

**Deploy Range 2 to Server 1:**
```bash
./deploy_new_ranges.sh server1 range2
```

**Or split ranges across both servers:**
```bash
# Server 1 runs range1
./deploy_new_ranges.sh server1 range1

# Server 2 runs range2
./deploy_new_ranges.sh server2 range2
```

## Step 3: Start Searches

After deployment, start the search on each server:

**For Server 1:**
```bash
ssh root@5.161.93.179
cd K3_range1  # or whichever range you deployed
./start_search.sh
```

**For Server 2:**
```bash
ssh root@5.78.98.156
cd K3_range2  # or whichever range you deployed
./start_search.sh
```

## Step 4: Monitor Progress

**View live search logs:**
```bash
# Server 1
ssh root@5.161.93.179 'tail -f K3_range1/search.log'

# Server 2
ssh root@5.78.98.156 'tail -f K3_range2/search.log'
```

**Check for results:**
```bash
# Server 1
ssh root@5.161.93.179 'cat K3_range1/result_range1.txt'

# Server 2
ssh root@5.78.98.156 'cat K3_range2/result_range2.txt'
```

## Step 5: Resume Original Server 2 Range (Later)

When you want to resume Server 2's original search:

1. Stop current search (if running)
2. Restore backup files:
```bash
# Find your backup
ls /root/repo/server2_backups/

# Upload back to server
BACKUP_DIR="K3_backup_20260123_XXXXXX"  # Use actual directory name
scp -r /root/repo/server2_backups/$BACKUP_DIR/* root@5.78.98.156:~/K3/

# Resume search
ssh root@5.78.98.156 'cd K3 && ./K3_OpenCL --continue'
```

## Directory Structure

After deployment, your servers will have:

```
Server 1 or 2:
~/
├── K3/                    # Original search (preserved)
├── K3_range1/            # New range 1 search
│   ├── K3_OpenCL         # Executable
│   ├── bloom.bin         # Bloom filter
│   ├── config.txt        # Range configuration
│   ├── start_search.sh   # Launch script
│   └── search.log        # Search output
└── K3_range2/            # New range 2 search
    └── (same structure)
```

## Additional Ranges

You mentioned wanting 4 ranges total. Currently we have 2 configured:
- Range 1: 50 billion key range
- Range 2: 1 trillion key range

**To add more ranges:**
1. Provide the start/end decimal values for ranges 3 and 4
2. I'll create `range3_config.txt` and `range4_config.txt`
3. Deploy using the same script: `./deploy_new_ranges.sh <server> <range>`

## Quick Reference

| Task | Command |
|------|---------|
| Save Server 2 progress | `./save_server2_progress.sh` |
| Deploy range to server | `./deploy_new_ranges.sh <server> <range>` |
| Start search | `ssh <server> 'cd K3_<range> && ./start_search.sh'` |
| View logs | `ssh <server> 'tail -f K3_<range>/search.log'` |
| Check results | `ssh <server> 'cat K3_<range>/result_*.txt'` |
| List all ranges on server | `ssh <server> 'ls -d K3*'` |

## Notes

- Each range runs independently in its own directory
- Bloom filter is shared (copied to each range directory)
- All ranges can run simultaneously (resource permitting)
- Progress is automatically saved via `continue_*.txt` files
- Original Server 2 search is safely backed up before starting new ranges

## Need Help?

- Check if server is accessible: `ssh <server> 'uptime'`
- View all K3 processes: `ssh <server> 'ps aux | grep K3'`
- Stop a range: `ssh <server> 'pkill -f K3_range1'` (adjust range name)
