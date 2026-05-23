#!/bin/bash
# Launch SearchK4 on 8 GPUs for Range 6
# Range: 82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,120,423,526,066,342,990
#   To:  82,988,190,356,384,517,260,073,324,955,726,623,558,128,682,318,812,983,971,013,120,923,526,066,342,990
# Total: 500,000,000,000,000 keys (500 trillion), 62.5 trillion per GPU
# Status: COMPLETED - No matches found

BIN=/root/searchk4_hybrid/SearchK4_optimized/searchk4_fast
PATTERNS=/root/searchk4_hybrid/SearchK4_optimized/combined_patterns.txt
WORKDIR=/root/searchk4_hybrid/SearchK4_optimized

STARTS=(
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a8539f7695bccc4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853b0ea77a5b04e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853c25e598e944e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853d3d23b77784e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853e5461d605c4e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853f6b9ff49404e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a854082de132244e
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a85419a1c31b084e
)
ENDS=(
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853b0ea77a5b04d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853c25e598e944d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853d3d23b77784d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853e5461d605c4d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a853f6b9ff49404d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a854082de132244d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a85419a1c31b084d
  0xb779a6b50b0f27bb2fec56d5cfaacd9d9abc8e658959c281a8542b15a503ec4e
)

echo "Stopping existing searches..."
pkill -f searchk4_fast || true
sleep 2

cd $WORKDIR
rm -f gpu*_r6.log gpu*_r6_found.txt gpu*_r6.state

for i in {0..7}; do
  echo "Starting GPU $i: ${STARTS[$i]} -> ${ENDS[$i]}"
  nohup $BIN \
    -patterns $PATTERNS \
    -direct \
    -startx ${STARTS[$i]} \
    -endx ${ENDS[$i]} \
    -gpu $i \
    -o gpu${i}_r6_found.txt \
    -state gpu${i}_r6.state \
    > gpu${i}_r6.log 2>&1 &
  sleep 0.5
done

echo "All 8 GPUs launched on range 6."
