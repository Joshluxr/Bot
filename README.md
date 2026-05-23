# SearchK4 - GPU-Accelerated Cryptographic Key Search

## Overview

SearchK4 is a GPU-accelerated tool for searching secp256k1 private keys by comparing hash160 values against a bloom filter of target Bitcoin addresses. It uses CUDA to achieve billions of keys per second on modern NVIDIA GPUs.

## Infrastructure

| Component | Details |
|-----------|---------|
| Platform | vast.ai (cloud GPU rental) |
| Current Server | `ssh8.vast.ai:20911` (previously `74.48.78.46:40271`) |
| GPUs | 8× NVIDIA RTX 5080 |
| Cost | ~$1.186/hr |
| Combined Throughput | ~13.2 GKey/s |
| Per-GPU Throughput | ~1.59–1.77 GKey/s |

## Directory Structure (on vast.ai server)

```
/root/searchk4_hybrid/SearchK4_optimized/
├── searchk4_fast              # Main binary
├── combined_patterns.txt      # 3,493 target addresses (hash160)
├── launch_range7.sh           # Launch script for range 7
├── hourly_progress_r7.sh      # Hourly progress logger
├── range7_progress.log        # Hourly progress log file
├── gpu{0-7}_r7.log            # Per-GPU runtime logs
├── gpu{0-7}_r7_found.txt      # Match output files (empty = no match)
└── gpu{0-7}_r7.state          # State files for resume (~40MB each)
```

## How It Works

1. **Range Splitting**: A decimal key range is divided equally among 8 GPUs
2. **Hex Conversion**: Decimal sub-ranges are converted to 256-bit hexadecimal
3. **Parallel Search**: Each GPU iterates through its sub-range computing secp256k1 public keys
4. **Hash160 Comparison**: Each derived hash160 is checked against a bloom filter of target addresses
5. **State Checkpointing**: Progress is saved atomically to `.state` files for crash recovery
6. **Hourly Logging**: A background script appends progress snapshots every hour

## Command-Line Usage

```bash
./searchk4_fast \
  -patterns combined_patterns.txt \
  -direct \
  -startx 0xHEX_START \
  -endx 0xHEX_END \
  -gpu GPU_INDEX \
  -o gpu${i}_found.txt \
  -state gpu${i}.state
```

### Flags (SINGLE DASH only)

| Flag | Description |
|------|-------------|
| `-patterns` | Path to patterns file (hash160 addresses) |
| `-direct` | Direct key iteration mode |
| `-startx` | Start of hex range (0x-prefixed) |
| `-endx` | End of hex range (0x-prefixed) |
| `-gpu` | GPU index (0-7) |
| `-o` | Output file for matches |
| `-state` | State file path for resume capability |

**⚠️ IMPORTANT**: Use single-dash flags (`-gpu`), NOT double-dash (`--gpu`). Double-dash will fail with "Unknown or incomplete option" error.

## Resuming from State Files

If processes die (server restart, OOM, etc.), resume from state files:

```bash
for i in {0..7}; do
  nohup ./searchk4_fast \
    -patterns combined_patterns.txt \
    -direct \
    -state gpu${i}_r7.state \
    -endx ${END_HEX[$i]} \
    -gpu $i \
    -o gpu${i}_r7_found.txt \
    > gpu${i}_r7.log 2>&1 &
  sleep 0.5
done
```

State files are ~40MB each and contain the current position. They allow seamless resume without re-scanning already-checked keys.

## Checking for Matches

```bash
# Quick check - any non-empty found file = MATCH
for i in {0..7}; do
  [ -s gpu${i}_r7_found.txt ] && echo "GPU $i: MATCH!" && cat gpu${i}_r7_found.txt || echo "GPU $i: no match"
done
```

## Monitoring Status

```bash
# Per-GPU coverage and speed
for i in {0..7}; do
  COVERED=$(grep "Covered:" gpu${i}_r7.log | tail -1 | sed 's/.*Covered: \([0-9.]*\)B keys.*/\1/')
  SPEED=$(grep "GKey/s" gpu${i}_r7.log | tail -1 | sed 's/.*| \([0-9.]*\) GKey\/s.*/\1/')
  echo "GPU $i: ${COVERED}B keys | ${SPEED} GKey/s"
done

# GPU utilization
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader

# Process count
ps aux | grep searchk4_fast | grep -v grep | wc -l
```

## SSH Access

```bash
# Connect to server
ssh -p 20911 -i ~/.ssh/id_ed25519_vast root@ssh8.vast.ai

# Public key (add to server's ~/.ssh/authorized_keys)
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICYREBDG0rvl18yJCB3IzLzyaQdQB6UvswpXWsyJuCE1 devin@cognition.ai
```

## Performance Benchmarks

| GPU | CUDA Cores | GKey/s | $/hr (vast.ai) | $/GKey/s/hr |
|-----|-----------|--------|----------------|-------------|
| RTX 5080 | 10,752 | ~1.65-1.77 | ~$0.148 | **$0.085** |
| RTX 4060 Ti | 4,352 | ~0.72 | ~$0.07 | $0.097 |
| B300 SXM6 (est.) | 36,864 | ~6.1 | ~$0.63 | ~$0.10 |

**RTX 5080 is the most cost-efficient for this workload.**

## Range History

| Range | From (Decimal) | To (Decimal) | Keys | Duration | Result |
|-------|---------------|-------------|------|----------|--------|
| 4 | 61.79...×10^72 | 61.80...×10^72 | — | — | No matches |
| 5 | 90,249,899...×10^72 | 90,310,704...×10^72 | ~19.5 quadrillion | ~14 days | No matches |
| 6 | 82,988...120,423...990 | 82,988...120,923...990 | 500 trillion | ~10 hours | No matches, fully exhausted |
| 7 | 82,988...110,423...990 | 82,988...120,423...990 | 10 quadrillion | ~8.8 days | No matches (92.1% at last check) |

## Troubleshooting

### "Permission denied (publickey)"
Server lost SSH key. Re-add the public key via vast.ai dashboard or from another authorized session.

### Processes died (0% GPU utilization)
1. Verify state files exist: `ls -la gpu*_r7.state` (should be ~40MB each)
2. Resume using the state file resume command above
3. Verify: `nvidia-smi` should show 100% within 15 seconds

### "Connection refused" or "Connection closed"
Server may be down or port changed. Check vast.ai dashboard for current SSH connection details.

### Log shows "Unknown or incomplete option"
You used double-dash flags. Change `--gpu` to `-gpu`, `--patterns` to `-patterns`, etc.
