#!/bin/bash
# Launch script for Range 2: 11494219353108143562991068411194509532350831987680500254629221506744305000000000

RANGE_START='11494219353108143562991068411194509532350831987680500254629221506744305000000000'

cd /workspace/k3

echo "Starting Range 2 search on GPU 1..."
nohup ./BloomSearch32K3 \
  -gpu 1 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE_START \
  -state /tmp/range2.state \
  -both > /root/range2_search.log 2>&1 &

echo "Range 2 started on GPU 1"
echo "PID: $!"
echo "View logs: tail -f /root/range2_search.log"
