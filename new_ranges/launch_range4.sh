#!/bin/bash
# Launch script for Range 4: 81979563453356770746037359084754162925559246477171714229960496311613000000000

RANGE_START='81979563453356770746037359084754162925559246477171714229960496311613000000000'

cd /workspace/k3

echo "Starting Range 4 search on GPU 3..."
nohup ./BloomSearch32K3 \
  -gpu 3 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE_START \
  -state /tmp/range4.state \
  -both > /root/range4_search.log 2>&1 &

echo "Range 4 started on GPU 3"
echo "PID: $!"
echo "View logs: tail -f /root/range4_search.log"
