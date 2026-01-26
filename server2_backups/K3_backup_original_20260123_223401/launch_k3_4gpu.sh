#!/bin/bash

# Define new starting positions for each GPU
GPU0_START='110700593453987414978344539872069285445632253011473704242018438712270000000000'
GPU1_START='74120947517767895891355266452452269842804955139343486161984562552400000000000'
GPU2_START='110700593453987414978344539872069285445632253011473004242018438712270000000000'
GPU3_START='74120947517767895891355266452452269842804955139343006161984562552400000000000'

cd /workspace/k3

echo "Starting GPU 0..."
nohup ./BloomSearch32K3   -gpu 0   -prefix /root/bloom_55m.prefix32   -bloom /root/bloom_k3_standard.bloom   -seeds /root/bloom_k3_standard.seeds   -bits 1073741824   -hashes 12   -start $GPU0_START   -state /tmp/gpu0.state   -both > /root/gpu0_search.log 2>&1 &

echo "Starting GPU 1..."
nohup ./BloomSearch32K3   -gpu 1   -prefix /root/bloom_55m.prefix32   -bloom /root/bloom_k3_standard.bloom   -seeds /root/bloom_k3_standard.seeds   -bits 1073741824   -hashes 12   -start $GPU1_START   -state /tmp/gpu1.state   -both > /root/gpu1_search.log 2>&1 &

echo "Starting GPU 2..."
nohup ./BloomSearch32K3   -gpu 2   -prefix /root/bloom_55m.prefix32   -bloom /root/bloom_k3_standard.bloom   -seeds /root/bloom_k3_standard.seeds   -bits 1073741824   -hashes 12   -start $GPU2_START   -state /tmp/gpu2.state   -both > /root/gpu2_search.log 2>&1 &

echo "Starting GPU 3..."
nohup ./BloomSearch32K3   -gpu 3   -prefix /root/bloom_55m.prefix32   -bloom /root/bloom_k3_standard.bloom   -seeds /root/bloom_k3_standard.seeds   -bits 1073741824   -hashes 12   -start $GPU3_START   -state /tmp/gpu3.state   -both > /root/gpu3_search.log 2>&1 &

echo "All 4 GPUs started. Check logs at /root/gpu*_search.log"
sleep 2
ps aux | grep BloomSearch32K3 | grep -v grep
