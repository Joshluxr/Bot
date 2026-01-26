#!/bin/bash
# Launch script for Range 1: 11494219353108143562991068411194509532350831987680500254629221556744305000000000

RANGE_START='11494219353108143562991068411194509532350831987680500254629221556744305000000000'

cd /workspace/k3

echo "Starting Range 1 search on GPU 0..."
nohup ./BloomSearch32K3 \
  -gpu 0 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE_START \
  -state /tmp/range1.state \
  -both > /root/range1_search.log 2>&1 &

echo "Range 1 started on GPU 0"
echo "PID: $!"
echo "View logs: tail -f /root/range1_search.log"
