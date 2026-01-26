#!/bin/bash
set -e

# VPS Configuration
VPS_IP="65.75.200.134"
VPS_USER="root"
VPS_PASSWORD="Q9qk4Hl6R2YGpw7"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "VPS Address Matching Deployment"
echo "================================================"
echo ""

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo -e "${YELLOW}Installing sshpass...${NC}"
    apt-get update -qq && apt-get install -y sshpass
fi

# Function to run SSH commands
run_ssh() {
    sshpass -p "${VPS_PASSWORD}" ssh -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_IP}" "$@"
}

# Function to copy files
copy_file() {
    sshpass -p "${VPS_PASSWORD}" scp -o StrictHostKeyChecking=no "$1" "${VPS_USER}@${VPS_IP}:$2"
}

echo -e "${GREEN}[1/5] Testing VPS connectivity...${NC}"
if run_ssh "echo 'Connection successful'"; then
    echo -e "${GREEN}✓ Connected to VPS${NC}"
else
    echo -e "${RED}✗ Failed to connect to VPS${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}[2/5] Checking VPS environment...${NC}"
run_ssh "python3 --version && echo '✓ Python3 available'"
run_ssh "which wget && echo '✓ wget available'"

echo ""
echo -e "${GREEN}[3/5] Copying scripts to VPS...${NC}"
copy_file "/root/repo/match_funded_addresses.sh" "/root/match_funded_addresses.sh"
copy_file "/root/repo/match_funded_addresses.py" "/root/match_funded_addresses.py"
run_ssh "chmod +x /root/match_funded_addresses.sh /root/match_funded_addresses.py"
echo -e "${GREEN}✓ Scripts deployed${NC}"

echo ""
echo -e "${GREEN}[4/5] Choose execution method:${NC}"
echo "  1) Bash script (simple, uses shell tools)"
echo "  2) Python script (advanced, with detailed analysis)"
echo "  3) Both (run Python script with fallback)"
echo ""
read -p "Enter choice [1-3] (default: 2): " choice
choice=${choice:-2}

echo ""
echo -e "${GREEN}[5/5] Starting matching process on VPS...${NC}"
echo -e "${YELLOW}Note: This may take 30-60 minutes depending on download speeds${NC}"
echo ""

case $choice in
    1)
        echo "Running Bash script..."
        run_ssh "bash /root/match_funded_addresses.sh 2>&1 | tee /root/matching_log.txt"
        ;;
    2)
        echo "Running Python script..."
        run_ssh "python3 /root/match_funded_addresses.py 2>&1 | tee /root/matching_log.txt"
        ;;
    3)
        echo "Running Python script with Bash fallback..."
        run_ssh "python3 /root/match_funded_addresses.py 2>&1 | tee /root/matching_log.txt || bash /root/match_funded_addresses.sh 2>&1 | tee -a /root/matching_log.txt"
        ;;
    *)
        echo "Invalid choice, defaulting to Python script..."
        run_ssh "python3 /root/match_funded_addresses.py 2>&1 | tee /root/matching_log.txt"
        ;;
esac

echo ""
echo "================================================"
echo -e "${GREEN}DEPLOYMENT COMPLETE${NC}"
echo "================================================"
echo ""
echo "To check results:"
echo "  ssh root@${VPS_IP}"
echo "  cat /root/address_matching/results/ANALYSIS_REPORT.txt"
echo ""
echo "To download results:"
echo "  scp root@${VPS_IP}:/root/address_matching/results/* ./results/"
echo ""
echo "To view live progress:"
echo "  ssh root@${VPS_IP} 'tail -f /root/matching_log.txt'"
echo ""
