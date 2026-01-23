#!/bin/bash
# Quick script to check all server statuses

echo "=== GPU Search Servers Status ==="
echo ""

echo "Server 1 (8x RTX 4080 SUPER) - 45.77.214.165:24867"
ssh -p 24867 root@45.77.214.165 -i ~/.ssh/terragon_server_key "ps aux | grep BloomSearch32K3 | grep -v grep | wc -l" 2>/dev/null && echo "✓ Processes running" || echo "✗ Connection failed"
echo ""

echo "Server 2 (4x RTX 5090) - 173.180.134.131:35952"
ssh -p 35952 root@173.180.134.131 -i ~/.ssh/terragon_server_key "ps aux | grep BloomSearch32K3 | grep -v grep | wc -l" 2>/dev/null && echo "✓ Processes running" || echo "✗ Connection failed"
echo ""

echo "Server 3 (8x RTX A5000 - Vast.ai) - 195.93.174.17:24229"
ssh -p 24229 root@195.93.174.17 -i ~/.ssh/terragon_server_key "ps aux | grep BloomSearch32K3 | grep -v grep | wc -l" 2>/dev/null && echo "✓ Processes running" || echo "✗ Connection failed"
echo ""
