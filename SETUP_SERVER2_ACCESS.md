# Server 2 SSH Access Setup Guide

## Server 2 Connection Details

Server 2 is hosted on vast.ai and has two potential access points:

**Primary**: `root@5.78.98.156` (standard SSH port 22)
**Alternate**: `root@173.180.134.131 -p 35952` (custom port)

## Setup SSH Key Access

The vast.ai server requires SSH key authentication. To set this up:

### Option 1: Add your SSH public key to vast.ai

1. Generate an SSH key if you don't have one:
   ```bash
   ssh-keygen -t ed25519 -C "server2-access"
   ```

2. Copy your public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

3. Add the public key to your vast.ai instance through their web interface

4. Test connection:
   ```bash
   ssh -p 35952 root@173.180.134.131
   ```

### Option 2: Use existing vast.ai SSH key

If you already have SSH access configured through vast.ai, the connection should work automatically.

## Once SSH Access is Working

Run the all-in-one script to save Server 2's progress and deploy 4 new ranges:

```bash
./save_and_deploy_server2.sh
```

This script will:
1. ✅ Automatically detect which Server 2 address works
2. ✅ Save all current progress to a timestamped backup
3. ✅ Create 4 new range directories (K3_range1 through K3_range4)
4. ✅ Copy K3 executable and bloom filter to each
5. ✅ Upload configurations for all 4 ranges
6. ✅ Create start scripts for each range
7. ✅ Download backup locally to `/root/repo/server2_backups/`

## Manual Connection Test

To test which connection method works:

```bash
# Test primary address
ssh -o ConnectTimeout=5 root@5.78.98.156 "hostname"

# Test alternate address
ssh -p 35952 -o ConnectTimeout=5 root@173.180.134.131 "hostname"
```

## The 4 New Ranges

After deployment, Server 2 will have:

```
~/K3/              # Original search (backed up, preserved)
~/K3_backup_*/     # Timestamped backup of original search
~/K3_range1/       # Range 1: 11494219...556744305000000000
~/K3_range2/       # Range 2: 11494219...506744305000000000
~/K3_range3/       # Range 3: 81979563...961496311613000000000
~/K3_range4/       # Range 4: 81979563...960496311613000000000
```

## Starting the Searches

Once deployed, start all 4 ranges:

```bash
# If using port 35952
ssh -p 35952 root@173.180.134.131 << 'EOF'
cd K3_range1 && ./start_search.sh
cd ~/K3_range2 && ./start_search.sh
cd ~/K3_range3 && ./start_search.sh
cd ~/K3_range4 && ./start_search.sh
EOF

# Monitor all ranges
ssh -p 35952 root@173.180.134.131 'tail -f K3_range*/search.log'
```

## Resuming Original Search Later

To resume Server 2's original search:

```bash
# Find your backup
ls /root/repo/server2_backups/

# Restore from backup
BACKUP="K3_backup_original_20260123_XXXXXX"  # Use actual name
scp -r -p 35952 /root/repo/server2_backups/$BACKUP/* root@173.180.134.131:~/K3/

# Resume original search
ssh -p 35952 root@173.180.134.131 'cd K3 && ./K3_OpenCL --continue'
```

## Troubleshooting

**"Permission denied (publickey)"**
- Your SSH key is not configured in vast.ai
- Add your public key through the vast.ai web interface

**"Connection timed out"**
- The vast.ai instance may be stopped/hibernated
- Check your vast.ai dashboard to ensure the instance is running

**"Connection refused"**
- Wrong port number
- Try the alternate address/port combination
