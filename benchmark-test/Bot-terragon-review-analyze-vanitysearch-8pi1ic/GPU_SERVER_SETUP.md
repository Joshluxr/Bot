# GPU Server Setup Guide for Optimized VanitySearch

## Repository Access

The optimized VanitySearch codebase is available at:
- **GitHub**: `https://github.com/Joshluxr/Bot.git`
- **Branch**: `terragon/review-analyze-vanitysearch-8pi1ic`
- **Path**: `vanitysearch_analysis/`

## Quick Setup (Any GPU Server)

```bash
# Clone the repository
git clone https://github.com/Joshluxr/Bot.git
cd Bot
git checkout terragon/review-analyze-vanitysearch-8pi1ic

# Navigate to optimized VanitySearch
cd vanitysearch_analysis

# Build with CUDA support
make gpu=1 ccap=86  # Adjust ccap for your GPU (75 for RTX 20xx, 86 for RTX 30xx, 89 for RTX 40xx)
```

## Alternative Access Methods (Not SSH)

### Option 1: RunPod Web Terminal

1. Log into [RunPod](https://www.runpod.io/)
2. Create a GPU pod with CUDA installed
3. Use the **Web Terminal** button (no SSH required)
4. Run the setup commands above

### Option 2: Vast.ai JupyterLab

1. Log into [Vast.ai](https://vast.ai/)
2. Rent a GPU instance with JupyterLab enabled
3. Open JupyterLab via the web interface
4. Open a terminal from JupyterLab's launcher
5. Run the setup commands

### Option 3: Google Colab (Free GPU)

```python
# Run in a Colab notebook with GPU runtime
!git clone https://github.com/Joshluxr/Bot.git
%cd Bot
!git checkout terragon/review-analyze-vanitysearch-8pi1ic
%cd vanitysearch_analysis

# Install CUDA toolkit if not available
!apt-get update && apt-get install -y cuda-toolkit-12-0

# Build
!make gpu=1 ccap=75
```

### Option 4: Lambda Labs Web Console

1. Log into [Lambda Labs](https://lambdalabs.com/)
2. Launch a GPU instance
3. Use the **Web Terminal** from the dashboard
4. Run the setup commands

### Option 5: Paperspace Gradient

1. Log into [Paperspace Gradient](https://www.paperspace.com/)
2. Create a notebook or machine
3. Use the integrated terminal
4. Run the setup commands

## Build Options

```bash
# Standard GPU build
make gpu=1 ccap=86

# With custom thread grouping (for high-end GPUs)
make gpu=1 ccap=86 CXXFLAGS="-DNB_THREAD_PER_GROUP=256"

# Debug build
make gpu=1 ccap=86 debug=1

# Clean rebuild
make clean && make gpu=1 ccap=86
```

## CUDA Compute Capability Reference

| GPU Series | Compute Capability |
|------------|-------------------|
| GTX 10xx   | 61                |
| RTX 20xx   | 75                |
| RTX 30xx   | 86                |
| RTX 40xx   | 89                |
| A100       | 80                |
| H100       | 90                |

## Usage Examples

```bash
# Basic search for compressed addresses
./VanitySearch -gpu 1abc

# Search with keyspace range
./VanitySearch -gpu --keyspace 8000000000000000:ffffffffffffffff 1abc

# Multiple prefixes
./VanitySearch -gpu -i prefixes.txt

# High performance with custom grid
./VanitySearch -gpu -g 256,256 1abc
```

## New Features Implemented

1. **Keyspace Range Scanning** (`--keyspace START:END`)
   - BitCrack-style range specification
   - Supports formats: `START:END`, `START:+COUNT`, `:END`

2. **Batch GPU Initialization**
   - 100x faster startup for large thread counts
   - Uses Montgomery batch inversion

3. **GPU Math Optimizations**
   - UMultSpecial: Optimized constant multiplication
   - ModSub256isOdd: Parity-only computation
   - Configurable thread grouping (128/256/512)

## Troubleshooting

### CUDA not found
```bash
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

### Wrong compute capability
Check your GPU and use the appropriate ccap value:
```bash
nvidia-smi --query-gpu=compute_cap --format=csv
```

### Build errors
Ensure you have the required dependencies:
```bash
apt-get install -y build-essential libssl-dev
```
