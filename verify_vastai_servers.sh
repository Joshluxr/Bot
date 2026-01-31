#!/bin/bash
# Verify Bitcoin keypairs on vast.ai GPU servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Verifying Bitcoin Candidates from vast.ai GPU Servers    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Vast.ai GPU servers
SERVER1="158.51.110.52"
PORT1="29114"
SERVER2="45.77.214.165"
PORT2="24867"

# Candidate files
FILE_SERVER1="/root/all_candidates_server1_NEW.csv"
FILE_SERVER2="/root/all_candidates_server2_NEW.csv"

verify_server() {
    local server=$1
    local port=$2
    local file=$3
    local server_name=$4

    echo -e "\n${GREEN}═══ Verifying $server_name ═══${NC}\n"
    echo "Server: $server:$port"
    echo "File: $file"
    echo ""

    # Check connectivity
    if ! ssh -p $port -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$server "echo 'Connected'" 2>/dev/null; then
        echo -e "${RED}✗ Cannot connect to server $server:$port${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Connected to server${NC}"

    # Check if file exists
    if ! ssh -p $port -o StrictHostKeyChecking=no root@$server "test -f $file" 2>/dev/null; then
        echo -e "${RED}✗ File not found: $file${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ File exists${NC}"

    # Get file info
    echo ""
    echo "File information:"
    ssh -p $port -o StrictHostKeyChecking=no root@$server "ls -lh $file && wc -l $file"

    # Show sample data
    echo ""
    echo "Sample data (first 5 lines):"
    ssh -p $port -o StrictHostKeyChecking=no root@$server "head -5 $file"

    # Copy verification script to server
    echo ""
    echo "Copying verification script to server..."
    scp -P $port -o StrictHostKeyChecking=no -q "$SCRIPT_DIR/verify_keypairs.py" root@$server:/tmp/verify_keypairs.py

    # Install coincurve if needed
    echo "Checking crypto libraries..."
    if ! ssh -p $port -o StrictHostKeyChecking=no root@$server "python3 -c 'import coincurve' 2>/dev/null"; then
        echo "Installing coincurve..."
        ssh -p $port -o StrictHostKeyChecking=no root@$server "pip install coincurve --break-system-packages -q" 2>/dev/null || \
        ssh -p $port -o StrictHostKeyChecking=no root@$server "pip install coincurve -q" 2>/dev/null
    fi
    echo -e "${GREEN}✓ Libraries ready${NC}"

    # Run verification with sampling
    echo ""
    echo -e "${YELLOW}Running verification (sampling 100 entries)...${NC}"
    echo "This will verify that private keys correctly generate the addresses."
    echo ""

    ssh -p $port -o StrictHostKeyChecking=no root@$server "python3 /tmp/verify_keypairs.py $file 100 1" 2>&1 | grep -v "Welcome to vast.ai" | tee /tmp/verify_${server_name}.log

    echo ""
    echo -e "${GREEN}✓ Verification complete for $server_name${NC}"
    echo "Results saved to: /tmp/verify_${server_name}.log"
}

main() {
    if [ $# -eq 0 ]; then
        echo "Usage:"
        echo "  $0 server1    - Verify Server 1 only"
        echo "  $0 server2    - Verify Server 2 only"
        echo "  $0 both       - Verify both servers"
        echo ""
        echo "Servers:"
        echo "  Server 1: $SERVER1:$PORT1 (3.2M candidates, 437MB)"
        echo "  Server 2: $SERVER2:$PORT2 (5.5M candidates, 739MB)"
        echo ""
        exit 0
    fi

    case "$1" in
        server1)
            verify_server "$SERVER1" "$PORT1" "$FILE_SERVER1" "Server1"
            ;;
        server2)
            verify_server "$SERVER2" "$PORT2" "$FILE_SERVER2" "Server2"
            ;;
        both)
            verify_server "$SERVER1" "$PORT1" "$FILE_SERVER1" "Server1"
            echo ""
            echo ""
            verify_server "$SERVER2" "$PORT2" "$FILE_SERVER2" "Server2"
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            $0
            ;;
    esac
}

main "$@"
