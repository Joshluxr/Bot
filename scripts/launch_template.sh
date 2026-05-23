#!/bin/bash
# Template for launching SearchK4 on a new range
# 
# HOW TO USE:
# 1. Convert your decimal range start/end to hex (use Python: hex(decimal_number))
# 2. Split the hex range into 8 equal parts
# 3. Fill in STARTS[] and ENDS[] arrays below
# 4. Deploy to server and run
#
# CONVERSION EXAMPLE (Python):
#   start_dec = 82988190356384517260073324955726623558128682318812983971013110423526066342990
#   end_dec   = 82988190356384517260073324955726623558128682318812983971013120423526066342990
#   total = end_dec - start_dec  # 10,000,000,000,000,000
#   per_gpu = total // 8         # 1,250,000,000,000,000
#   for i in range(8):
#       gpu_start = start_dec + (i * per_gpu)
#       gpu_end = start_dec + ((i+1) * per_gpu) - 1  # (last GPU uses original end)
#       print(f"GPU {i}: {hex(gpu_start)} -> {hex(gpu_end)}")

BIN=/root/searchk4_hybrid/SearchK4_optimized/searchk4_fast
PATTERNS=/root/searchk4_hybrid/SearchK4_optimized/combined_patterns.txt
WORKDIR=/root/searchk4_hybrid/SearchK4_optimized
RANGE_NAME="r8"  # Change this for each new range

# Fill these in after hex conversion and splitting
STARTS=(
  0x_GPU0_START_HEX
  0x_GPU1_START_HEX
  0x_GPU2_START_HEX
  0x_GPU3_START_HEX
  0x_GPU4_START_HEX
  0x_GPU5_START_HEX
  0x_GPU6_START_HEX
  0x_GPU7_START_HEX
)
ENDS=(
  0x_GPU0_END_HEX
  0x_GPU1_END_HEX
  0x_GPU2_END_HEX
  0x_GPU3_END_HEX
  0x_GPU4_END_HEX
  0x_GPU5_END_HEX
  0x_GPU6_END_HEX
  0x_GPU7_END_HEX
)

echo "Stopping existing searches..."
pkill -f searchk4_fast || true
sleep 2

cd $WORKDIR
rm -f gpu*_${RANGE_NAME}.log gpu*_${RANGE_NAME}_found.txt gpu*_${RANGE_NAME}.state

for i in {0..7}; do
  echo "Starting GPU $i: ${STARTS[$i]} -> ${ENDS[$i]}"
  nohup $BIN \
    -patterns $PATTERNS \
    -direct \
    -startx ${STARTS[$i]} \
    -endx ${ENDS[$i]} \
    -gpu $i \
    -o gpu${i}_${RANGE_NAME}_found.txt \
    -state gpu${i}_${RANGE_NAME}.state \
    > gpu${i}_${RANGE_NAME}.log 2>&1 &
  sleep 0.5
done

echo "All 8 GPUs launched on ${RANGE_NAME}."
