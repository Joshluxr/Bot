#!/bin/bash
# Master script to launch all 4 new K3 ranges on Server 2

echo "=== Stopping Current Searches ==="
pkill -f BloomSearch32K3
sleep 3
echo "All previous searches stopped."
echo ""

echo "=== Launching 4 New Ranges ==="
echo ""

# Range 1 on GPU 0
RANGE1_START='11494219353108143562991068411194509532350831987680500254629221556744305000000000'
echo "Starting Range 1 on GPU 0..."
cd /workspace/k3
nohup ./BloomSearch32K3 \
  -gpu 0 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE1_START \
  -state /tmp/range1.state \
  -both > /root/range1_search.log 2>&1 &
RANGE1_PID=$!
echo "  ✓ Range 1 started (PID: $RANGE1_PID)"
sleep 1

# Range 2 on GPU 1
RANGE2_START='11494219353108143562991068411194509532350831987680500254629221506744305000000000'
echo "Starting Range 2 on GPU 1..."
nohup ./BloomSearch32K3 \
  -gpu 1 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE2_START \
  -state /tmp/range2.state \
  -both > /root/range2_search.log 2>&1 &
RANGE2_PID=$!
echo "  ✓ Range 2 started (PID: $RANGE2_PID)"
sleep 1

# Range 3 on GPU 2
RANGE3_START='81979563453356770746037359084754162925559246477171714229961496311613000000000'
echo "Starting Range 3 on GPU 2..."
nohup ./BloomSearch32K3 \
  -gpu 2 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE3_START \
  -state /tmp/range3.state \
  -both > /root/range3_search.log 2>&1 &
RANGE3_PID=$!
echo "  ✓ Range 3 started (PID: $RANGE3_PID)"
sleep 1

# Range 4 on GPU 3
RANGE4_START='81979563453356770746037359084754162925559246477171714229960496311613000000000'
echo "Starting Range 4 on GPU 3..."
nohup ./BloomSearch32K3 \
  -gpu 3 \
  -prefix /root/bloom_55m.prefix32 \
  -bloom /root/bloom_k3_standard.bloom \
  -seeds /root/bloom_k3_standard.seeds \
  -bits 1073741824 \
  -hashes 12 \
  -start $RANGE4_START \
  -state /tmp/range4.state \
  -both > /root/range4_search.log 2>&1 &
RANGE4_PID=$!
echo "  ✓ Range 4 started (PID: $RANGE4_PID)"
sleep 2

echo ""
echo "=== All 4 Ranges Running ==="
echo ""
ps aux | grep BloomSearch32K3 | grep -v grep
echo ""
echo "Monitor logs:"
echo "  tail -f /root/range1_search.log"
echo "  tail -f /root/range2_search.log"
echo "  tail -f /root/range3_search.log"
echo "  tail -f /root/range4_search.log"
echo ""
echo "Or monitor all at once:"
echo "  tail -f /root/range*_search.log"
echo ""
