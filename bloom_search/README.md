# GPU Bloom Filter Bitcoin Address Search

High-performance GPU-accelerated Bitcoin address search using bloom filters for efficient key space elimination.

## Performance

| Hardware | Speed |
|----------|-------|
| RTX 4080 SUPER (single) | ~2.4-2.5 GKey/s |
| 8x RTX 4080 SUPER | ~19-20 GKey/s |

- 32-bit prefix filter eliminates 99.35% of keys before bloom filter check
- Persistent state allows resume after restart or server migration

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Search Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│  Random EC Point → SHA256 → RIPEMD160 → Prefix Check → Bloom   │
│                                              │              │    │
│                                         99.35% rejected    │    │
│                                                       ~0.1% FP  │
│                                                            │    │
│                                                    Verify against│
│                                                    address DB   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files

### Source Code (`src/`)
- `BloomSearch32Silent.cu` - Main GPU search kernel (silent mode)
- `BloomSearch32.cu` - GPU search with bloom filter hit logging

### Scripts (`scripts/`)
- `gpu_only_search.sh` - Main search launcher for 8 GPUs
- `checkpoint_manager.py` - Upload/download checkpoints to VPS
- `auto_checkpoint_sync.sh` - Auto-sync states to VPS periodically

### Data Files (generated separately)
- `bloom_v2.bloom` - Bloom filter (~42MB)
- `bloom_v2.prefix32` - 32-bit prefix bitmap (512MB)
- `bloom_v2.seeds` - Bloom filter hash seeds

## Checkpoint System

The search saves state every 500 iterations (~33M keys per GPU). State files contain:
- Total keys checked (8 bytes)
- EC point states for all threads (4MB per GPU)

### Sync to VPS (Prevents Progress Loss)

```bash
# On GPU server - auto-sync every 30 minutes
./scripts/auto_checkpoint_sync.sh root@your-vps.com 30 &

# Manual operations
python3 scripts/checkpoint_manager.py upload -s root@your-vps.com -g 0
python3 scripts/checkpoint_manager.py download -s root@your-vps.com -g 0
python3 scripts/checkpoint_manager.py status -s root@your-vps.com
```

### State File Format

```
Offset  Size    Description
0       8       Total keys checked (uint64 LE)
8       4MB     Thread EC points (65536 × 8 × uint64)
```

## Quick Start

### 1. Setup New GPU Server

```bash
# Install CUDA
apt update && apt install -y nvidia-cuda-toolkit

# Clone and setup
git clone https://github.com/YourRepo/bloom_search.git
cd bloom_search

# Download filter files (host these somewhere)
wget https://your-storage/bloom_v2.bloom -O /root/bloom_v2.bloom
wget https://your-storage/bloom_v2.prefix32 -O /root/bloom_v2.prefix32
wget https://your-storage/bloom_v2.seeds -O /root/bloom_v2.seeds

# Compile
cd src && nvcc -O3 -o /root/VanitySearch/BloomSearch32Silent BloomSearch32Silent.cu -arch=sm_89
```

### 2. Resume from Checkpoint (Optional)

```bash
python3 scripts/checkpoint_manager.py download -s root@your-vps.com -g 0
# Repeat for GPUs 1-7
```

### 3. Start Search

```bash
nohup ./scripts/gpu_only_search.sh &
nohup ./scripts/auto_checkpoint_sync.sh root@your-vps.com 30 &
```

### 4. Monitor

```bash
tail -f /root/gpu_search.log
grep -oP '\d+\.\d+B keys' /root/gpu_search.log | tail -8
```

## Mathematical Reality

Finding a match is essentially impossible:

| Metric | Value |
|--------|-------|
| Funded addresses | ~50 million (2^26) |
| Possible addresses | 2^160 (1.46 × 10^48) |
| Search rate | 20 GKey/s |
| Time to exhaustive search | 2.3 × 10^38 seconds |
| Age of universe | 4.3 × 10^17 seconds |

This demonstrates Bitcoin's cryptographic security.

## Legacy Scripts

| Script | Description |
|--------|-------------|
| `build_bloom_fast.py` | Build bloom filter from address list |
| `bloom_verifier.py` | Verify addresses against bloom filter |
| `continuous_search.sh` | Older crash-resilient runner |

## License

For research and educational purposes only.
