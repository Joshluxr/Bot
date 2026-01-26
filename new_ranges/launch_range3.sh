#!/bin/bash
# Launch script for Range 3: 81979563453356770746037359084754162925559246477171714229961496311613000000000

RANGE_START='81979563453356770746037359084754162925559246477171714229961496311613000000000'

cd /workspace/k3

echo "Starting Range 3 search on GPU 2..."
nohup ./BloomSearch32K3 \
  -gpu 2 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE_START \
  -state /tmp/range3.state \
  -both > /root/range3_search.log 2>&1 &

echo "Range 3 started on GPU 2"
echo "PID: $!"
echo "View logs: tail -f /root/range3_search.log"
