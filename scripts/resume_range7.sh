#!/bin/bash
# Resume SearchK4 from state files after crash/restart
# Only use this if state files exist (gpu*_r7.state, ~40MB each)

BIN=/root/searchk4_hybrid/SearchK4_optimized/searchk4_fast
PATTERNS=/root/searchk4_hybrid/SearchK4_optimized/combined_patterns.txt
WORKDIR=/root/searchk4_hybrid/SearchK4_optimized

ENDS=(
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a834896273f3ec4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a838fa40c1ec0c4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a83d6b1f0fe42c4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a841dbfd5ddc4c4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a8464cdbabd46c4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a84abdb9f9cc8c4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a84f2e9847c4ac4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a8539f7695bccc4e
)

cd $WORKDIR

# Verify state files exist
echo "Checking state files..."
for i in {0..7}; do
  if [ ! -f "gpu${i}_r7.state" ]; then
    echo "ERROR: gpu${i}_r7.state not found! Cannot resume GPU $i."
    exit 1
  fi
  SIZE=$(stat -c%s "gpu${i}_r7.state" 2>/dev/null)
  echo "  gpu${i}_r7.state: ${SIZE} bytes"
done

echo ""
echo "Resuming all 8 GPUs from state files..."

for i in {0..7}; do
  nohup $BIN \
    -patterns $PATTERNS \
    -direct \
    -state gpu${i}_r7.state \
    -endx ${ENDS[$i]} \
    -gpu $i \
    -o gpu${i}_r7_found.txt \
    > gpu${i}_r7.log 2>&1 &
  sleep 0.5
done

sleep 15
echo "Verifying GPU utilization..."
nvidia-smi --query-gpu=index,utilization.gpu --format=csv,noheader
PROCS=$(ps aux | grep searchk4_fast | grep -v grep | wc -l)
echo "Running processes: $PROCS"
