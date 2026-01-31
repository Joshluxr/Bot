#!/bin/bash
# Script to verify YOUR specific candidate files from GPU servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Verifying Bitcoin Candidates from GPU Servers            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Your GPU servers
SERVER1="195.26.253.243"
SERVER2="195.26.253.245"

# Your candidate files
FILE_SERVER1="/root/all_candidates_server1_NEW.csv"
FILE_SERVER2="/root/all_candidates_server2_NEW.csv"

verify_server() {
    local server=$1
    local file=$2
    local server_name=$3

    echo -e "\n${GREEN}═══ Verifying $server_name ═══${NC}\n"
    echo "Server: $server"
    echo "File: $file"
    echo ""

    # Check connectivity
    if ! ssh -o ConnectTimeout=5 root@$server "echo 'Connected'" 2>/dev/null; then
        echo -e "${RED}✗ Cannot connect to server $server${NC}"
        echo "Please check:"
        echo "  1. SSH keys are configured"
        echo "  2. Server is online"
        echo "  3. Firewall allows connection"
        return 1
    fi

    echo -e "${GREEN}✓ Connected to server${NC}"

    # Check if file exists
    if ! ssh root@$server "test -f $file" 2>/dev/null; then
        echo -e "${RED}✗ File not found: $file${NC}"
        echo ""
        echo "Searching for candidate files on server..."
        ssh root@$server "find /root -name '*candidate*.csv' -type f 2>/dev/null" || true
        return 1
    fi

    echo -e "${GREEN}✓ File exists${NC}"

    # Get file info
    echo ""
    echo "File information:"
    ssh root@$server "ls -lh $file && echo 'Lines:' && wc -l $file"

    # Show sample data
    echo ""
    echo "Sample data (first 5 lines):"
    ssh root@$server "head -5 $file"

    # Copy verification script to server
    echo ""
    echo "Copying verification script to server..."
    scp -q "$SCRIPT_DIR/verify_keypairs.py" root@$server:/tmp/verify_keypairs.py

    # Install coincurve if needed
    echo "Checking crypto libraries..."
    if ! ssh root@$server "python3 -c 'import coincurve' 2>/dev/null"; then
        echo "Installing coincurve..."
        ssh root@$server "pip install coincurve --break-system-packages -q" 2>/dev/null
    fi
    echo -e "${GREEN}✓ Libraries ready${NC}"

    # Run verification with sampling
    echo ""
    echo -e "${YELLOW}Running verification (sampling 100 random entries)...${NC}"
    echo "This will verify that private keys correctly generate the addresses."
    echo ""

    ssh root@$server "python3 /tmp/verify_keypairs.py $file 100 1" 2>&1 | tee /tmp/verify_${server_name}.log

    echo ""
    echo -e "${GREEN}✓ Verification complete for $server_name${NC}"
    echo "Results saved to: /tmp/verify_${server_name}.log"
}

main() {
    echo "This script will verify that your Bitcoin candidates have"
    echo "matching private keys and public addresses."
    echo ""
    echo "Expected format: address,privkey,hash160"
    echo ""

    # Ask which server to verify
    if [ $# -eq 0 ]; then
        echo "Usage:"
        echo "  $0 server1    - Verify Server 1 only"
        echo "  $0 server2    - Verify Server 2 only"
        echo "  $0 both       - Verify both servers"
        echo "  $0 quick      - Quick test (first 10 lines from Server 1)"
        echo ""
        exit 0
    fi

    case "$1" in
        server1)
            verify_server "$SERVER1" "$FILE_SERVER1" "Server1"
            ;;
        server2)
            verify_server "$SERVER2" "$FILE_SERVER2" "Server2"
            ;;
        both)
            verify_server "$SERVER1" "$FILE_SERVER1" "Server1"
            echo ""
            echo ""
            verify_server "$SERVER2" "$FILE_SERVER2" "Server2"
            ;;
        quick)
            echo -e "${YELLOW}Quick test: Verifying first 10 lines from Server 1${NC}\n"
            ssh root@$SERVER1 "python3 /tmp/verify_keypairs.py $FILE_SERVER1 10 1" || \
                echo "Note: Make sure to run 'server1' first to copy the script"
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            $0
            ;;
    esac
}

main "$@"
