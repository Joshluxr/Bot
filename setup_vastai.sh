#!/bin/bash
# Vast.ai GPU Server Setup Script for VanitySearch
# Usage: ./setup_vastai.sh <API_KEY>

set -e

API_KEY="${1:-}"

if [ -z "$API_KEY" ]; then
    echo "Usage: ./setup_vastai.sh <VAST_API_KEY>"
    echo ""
    echo "Get your API key from: https://cloud.vast.ai/cli/"
    echo ""
    exit 1
fi

echo "=== Setting up Vast.ai CLI ==="
vastai set api-key "$API_KEY"

echo ""
echo "=== Checking for existing instances ==="
vastai show instances

echo ""
echo "=== Available GPU instances with JupyterLab ==="
echo "Searching for RTX 3090/4090 instances..."
vastai search offers 'gpu_name in ["RTX 3090", "RTX 4090"] rentable=True num_gpus=1' --order 'dph_total' | head -20

echo ""
echo "=== To rent an instance with JupyterLab ==="
echo "1. Find an instance ID from the list above"
echo "2. Run: vastai create instance <ID> --image pytorch/pytorch:2.0.1-cuda11.7-cudnn8-devel --jupyter --disk 20"
echo "3. Once running, get JupyterLab URL: vastai show instances"
echo ""
echo "=== To connect to existing instance ==="
echo "vastai show instances  # Get the instance ID and Jupyter URL"
echo ""
