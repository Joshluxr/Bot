#!/bin/bash
# Launch SearchK4 on 8 GPUs for Range 7
# Range: 82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,110,423,526,066,342,990
#   To:  82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,120,423,526,066,342,990
# Total: 10,000,000,000,000,000 keys (10 quadrillion), 1.25 quadrillion per GPU

BIN=/root/searchk4_hybrid/SearchK4_optimized/searchk4_fast
PATTERNS=/root/searchk4_hybrid/SearchK4_optimized/combined_patterns.txt
WORKDIR=/root/searchk4_hybrid/SearchK4_optimized

# Hex sub-ranges for each GPU (pre-computed from decimal range)
STARTS=(
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a830188425fbcc4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a834896273f3ec4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a838fa40c1ec0c4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a83d6b1f0fe42c4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a841dbfd5ddc4c4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a8464cdbabd46c4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a84abdb9f9cc8c4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a84f2e9847c4ac4e
)
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

echo "Stopping existing searches..."
pkill -f searchk4_fast || true
sleep 2

cd $WORKDIR

# Remove old logs/state for fresh start (comment out to keep state files for resume)
rm -f gpu*_r7.log gpu*_r7_found.txt gpu*_r7.state

for i in {0..7}; do
  echo "Starting GPU $i: ${STARTS[$i]} -> ${ENDS[$i]}"
  nohup $BIN \
    -patterns $PATTERNS \
    -direct \
    -startx ${STARTS[$i]} \
    -endx ${ENDS[$i]} \
    -gpu $i \
    -o gpu${i}_r7_found.txt \
    -state gpu${i}_r7.state \
    > gpu${i}_r7.log 2>&1 &
  sleep 0.5
done

echo "All 8 GPUs launched on range 7."
echo "Monitor with: nvidia-smi"
echo "Check matches: for i in {0..7}; do [ -s gpu\${i}_r7_found.txt ] && cat gpu\${i}_r7_found.txt; done"
