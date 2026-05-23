#!/bin/bash
# Quick status check script for SearchK4
# Run directly on the vast.ai server

cd /root/searchk4_hybrid/SearchK4_optimized

echo "=== MATCH CHECK ==="
FOUND_MATCH=0
for i in {0..7}; do
  if [ -s "gpu${i}_r7_found.txt" ]; then
    echo "GPU $i: *** MATCH FOUND! ***"
    cat "gpu${i}_r7_found.txt"
    FOUND_MATCH=1
  else
    echo "GPU $i: no match"
  fi
done

if [ $FOUND_MATCH -eq 0 ]; then
  echo "No matches across all GPUs."
fi

echo ""
echo "=== PER-GPU PROGRESS ==="
TOTAL=0
for i in {0..7}; do
  COVERED=$(grep "Covered:" "gpu${i}_r7.log" 2>/dev/null | tail -1 | sed 's/.*Covered: \([0-9.]*\)B keys.*/\1/')
  SPEED=$(grep "GKey/s" "gpu${i}_r7.log" 2>/dev/null | tail -1 | sed 's/.*| \([0-9.]*\) GKey\/s.*/\1/')
  echo "GPU $i: ${COVERED:-0}B keys | ${SPEED:-N/A} GKey/s"
done

echo ""
echo "=== PROCESS STATUS ==="
PROCS=$(ps aux | grep searchk4_fast | grep -v grep | wc -l)
echo "Running SearchK4 processes: $PROCS"

echo ""
echo "=== GPU UTILIZATION ==="
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
