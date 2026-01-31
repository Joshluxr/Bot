#!/bin/bash
# Derive Bitcoin addresses from private keys on remote GPU servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Derive Bitcoin Addresses from Private Keys               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}\n"

# Vast.ai GPU servers
SERVER1="158.51.110.52"
PORT1="29114"
SERVER2="45.77.214.165"
PORT2="24867"

# Files
FILE_SERVER1="/root/all_candidates_server1_NEW.csv"
FILE_SERVER2="/root/all_candidates_server2_NEW.csv"
OUTPUT_SERVER1="/root/all_candidates_server1_DERIVED.csv"
OUTPUT_SERVER2="/root/all_candidates_server2_DERIVED.csv"

derive_on_server() {
    local server=$1
    local port=$2
    local input_file=$3
    local output_file=$4
    local server_name=$5
    local max_lines=$6

    echo -e "\n${GREEN}═══ Processing $server_name ═══${NC}\n"
    echo "Server: $server:$port"
    echo "Input:  $input_file"
    echo "Output: $output_file"
    echo ""

    # Check connectivity
    if ! ssh -p $port -o ConnectTimeout=5 -o StrictHostKeyChecking=no root@$server "echo 'Connected'" 2>/dev/null; then
        echo -e "${RED}✗ Cannot connect to server $server:$port${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Connected${NC}"

    # Copy script to server
    echo "Copying derivation script to server..."
    scp -P $port -o StrictHostKeyChecking=no -q "$SCRIPT_DIR/derive_addresses_from_privkeys.py" root@$server:/tmp/derive_addresses.py

    # Install coincurve if needed
    echo "Checking libraries..."
    if ! ssh -p $port -o StrictHostKeyChecking=no root@$server "python3 -c 'import coincurve' 2>/dev/null"; then
        echo "Installing coincurve..."
        ssh -p $port -o StrictHostKeyChecking=no root@$server "pip install coincurve --break-system-packages -q" 2>/dev/null
    fi

    echo -e "${GREEN}✓ Ready${NC}"
    echo ""

    # Run derivation
    if [ -z "$max_lines" ]; then
        echo -e "${YELLOW}Deriving addresses for ALL entries (this may take a while)...${NC}"
        ssh -p $port -o StrictHostKeyChecking=no root@$server \
            "python3 /tmp/derive_addresses.py $input_file $output_file" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun"
    else
        echo -e "${YELLOW}Deriving addresses for first $max_lines entries...${NC}"
        ssh -p $port -o StrictHostKeyChecking=no root@$server \
            "python3 /tmp/derive_addresses.py $input_file $output_file $max_lines" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun"
    fi

    echo ""
    echo -e "${GREEN}✓ Derivation complete for $server_name${NC}"
    echo "Output file: $output_file"
}

show_results() {
    local server=$1
    local port=$2
    local output_file=$3
    local server_name=$4

    echo -e "\n${GREEN}═══ Results from $server_name ═══${NC}\n"

    # Show file size and line count
    ssh -p $port -o StrictHostKeyChecking=no root@$server \
        "ls -lh $output_file 2>/dev/null && wc -l $output_file 2>/dev/null" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun"

    echo ""
    echo "Sample entries (showing derived addresses):"
    ssh -p $port -o StrictHostKeyChecking=no root@$server \
        "head -6 $output_file" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun"

    echo ""
    echo "Match statistics:"
    local matches=$(ssh -p $port -o StrictHostKeyChecking=no root@$server \
        "grep -c ',YES$' $output_file 2>/dev/null" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun" || echo "0")
    local mismatches=$(ssh -p $port -o StrictHostKeyChecking=no root@$server \
        "grep -c ',NO$' $output_file 2>/dev/null" 2>&1 | grep -v "Welcome to vast.ai" | grep -v "Have fun" || echo "0")

    echo "  Matches: $matches"
    echo "  Mismatches: $mismatches"
}

download_results() {
    local server=$1
    local port=$2
    local output_file=$3
    local local_file=$4

    echo -e "\n${YELLOW}Downloading results to $local_file...${NC}"
    scp -P $port -o StrictHostKeyChecking=no root@$server:$output_file $local_file

    if [ -f "$local_file" ]; then
        echo -e "${GREEN}✓ Downloaded successfully${NC}"
        ls -lh "$local_file"
        echo ""
        echo "You can now analyze the results locally:"
        echo "  head -20 $local_file"
        echo "  grep ',YES$' $local_file | wc -l    # Count matches"
        echo "  grep ',NO$' $local_file | wc -l     # Count mismatches"
    fi
}

main() {
    if [ $# -eq 0 ]; then
        echo "Usage:"
        echo "  $0 test          - Quick test (first 100 lines from both servers)"
        echo "  $0 server1       - Process Server 1 (all entries)"
        echo "  $0 server2       - Process Server 2 (all entries)"
        echo "  $0 both          - Process both servers (all entries)"
        echo "  $0 server1 1000  - Process Server 1 (first 1000 lines)"
        echo "  $0 download      - Download derived results to local machine"
        echo ""
        echo "Servers:"
        echo "  Server 1: $SERVER1:$PORT1 (3.2M candidates)"
        echo "  Server 2: $SERVER2:$PORT2 (5.5M candidates)"
        echo ""
        echo "Note: Processing all entries may take 5-30 minutes per server."
        echo ""
        exit 0
    fi

    case "$1" in
        test)
            derive_on_server "$SERVER1" "$PORT1" "$FILE_SERVER1" "$OUTPUT_SERVER1" "Server1" "100"
            show_results "$SERVER1" "$PORT1" "$OUTPUT_SERVER1" "Server1"
            echo ""
            derive_on_server "$SERVER2" "$PORT2" "$FILE_SERVER2" "$OUTPUT_SERVER2" "Server2" "100"
            show_results "$SERVER2" "$PORT2" "$OUTPUT_SERVER2" "Server2"
            ;;
        server1)
            MAX_LINES="${2:-}"
            derive_on_server "$SERVER1" "$PORT1" "$FILE_SERVER1" "$OUTPUT_SERVER1" "Server1" "$MAX_LINES"
            show_results "$SERVER1" "$PORT1" "$OUTPUT_SERVER1" "Server1"
            ;;
        server2)
            MAX_LINES="${2:-}"
            derive_on_server "$SERVER2" "$PORT2" "$FILE_SERVER2" "$OUTPUT_SERVER2" "Server2" "$MAX_LINES"
            show_results "$SERVER2" "$PORT2" "$OUTPUT_SERVER2" "Server2"
            ;;
        both)
            MAX_LINES="${2:-}"
            derive_on_server "$SERVER1" "$PORT1" "$FILE_SERVER1" "$OUTPUT_SERVER1" "Server1" "$MAX_LINES"
            show_results "$SERVER1" "$PORT1" "$OUTPUT_SERVER1" "Server1"
            echo ""
            echo ""
            derive_on_server "$SERVER2" "$PORT2" "$FILE_SERVER2" "$OUTPUT_SERVER2" "Server2" "$MAX_LINES"
            show_results "$SERVER2" "$PORT2" "$OUTPUT_SERVER2" "Server2"
            ;;
        download)
            download_results "$SERVER1" "$PORT1" "$OUTPUT_SERVER1" "/tmp/server1_derived.csv"
            echo ""
            download_results "$SERVER2" "$PORT2" "$OUTPUT_SERVER2" "/tmp/server2_derived.csv"
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            $0
            ;;
    esac
}

main "$@"
