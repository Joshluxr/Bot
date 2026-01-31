#!/bin/bash
# Quick script to check candidate files on remote GPU servers

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_section() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Function to verify candidates on a remote server
verify_remote_candidates() {
    local server=$1
    local csv_file=$2
    local sample_size=${3:-100}
    local sample_every=${4:-1}

    print_section "Verifying candidates on $server"

    echo "Server: $server"
    echo "File: $csv_file"
    echo "Sample size: $sample_size"
    echo "Sample every: $sample_every lines"
    echo ""

    # Check if file exists on remote
    echo "Checking if file exists on remote server..."
    if ! ssh -o ConnectTimeout=5 root@$server "test -f $csv_file"; then
        print_error "File not found on remote server: $csv_file"
        return 1
    fi

    echo "✓ File exists"

    # Get file info
    echo -e "\nFile information:"
    ssh root@$server "ls -lh $csv_file && wc -l $csv_file"

    # Preview first few lines
    echo -e "\nFirst 3 lines:"
    ssh root@$server "head -3 $csv_file"

    # Copy verification script to remote
    echo -e "\nCopying verification script to remote server..."
    scp -q "$SCRIPT_DIR/verify_keypairs.py" root@$server:/tmp/verify_keypairs.py
    echo "✓ Script copied"

    # Check if coincurve is installed on remote
    echo -e "\nChecking for crypto libraries on remote..."
    if ssh root@$server "python3 -c 'import coincurve' 2>/dev/null"; then
        echo "✓ coincurve installed"
    else
        print_warning "coincurve not installed on remote server"
        echo "Installing coincurve..."
        ssh root@$server "pip install coincurve --break-system-packages -q"
        echo "✓ coincurve installed"
    fi

    # Run verification on remote
    echo -e "\nRunning verification on remote server..."
    echo "This may take a while..."
    ssh root@$server "python3 /tmp/verify_keypairs.py $csv_file $sample_size $sample_every"
}

# Function to download and verify locally
download_and_verify() {
    local server=$1
    local remote_file=$2
    local local_file=${3:-/tmp/candidates_temp.csv}
    local sample_size=${4:-100}

    print_section "Downloading and verifying from $server"

    echo "Downloading $remote_file from $server..."
    echo "Saving to: $local_file"

    # Download file
    if scp root@$server:$remote_file $local_file; then
        echo "✓ File downloaded successfully"

        # Get file size
        local size=$(ls -lh $local_file | awk '{print $5}')
        local lines=$(wc -l < $local_file)
        echo "File size: $size"
        echo "Lines: $lines"

        # Verify locally
        echo -e "\nVerifying locally..."
        python3 "$SCRIPT_DIR/verify_keypairs.py" "$local_file" "$sample_size"
    else
        print_error "Failed to download file"
        return 1
    fi
}

# Function to verify all candidates across servers
verify_all_servers() {
    print_section "Verifying candidates across all servers"

    # Define your GPU servers here
    local servers=(
        "195.26.253.243"  # Server 1
        "195.26.253.245"  # Server 2
    )

    local candidate_files=(
        "/root/all_candidates_server1_NEW.csv"
        "/root/all_candidates_server2_NEW.csv"
    )

    for i in "${!servers[@]}"; do
        local server="${servers[$i]}"
        local file="${candidate_files[$i]}"

        echo -e "\n${GREEN}Checking server $((i+1)): $server${NC}"

        # Check if we can connect
        if ! ssh -o ConnectTimeout=5 root@$server "echo 'Connected'" &>/dev/null; then
            print_error "Cannot connect to $server"
            continue
        fi

        # Check if file exists
        if ssh root@$server "test -f $file" 2>/dev/null; then
            echo "✓ Found: $file"

            # Quick verification (first 50 lines)
            echo "Running quick verification (50 samples)..."
            verify_remote_candidates "$server" "$file" 50 1
        else
            print_warning "File not found: $file"

            # Try to find candidate files
            echo "Searching for candidate files..."
            ssh root@$server "find /root -name '*candidate*.csv' -type f 2>/dev/null | head -5" || true
        fi

        echo ""
    done
}

# Function to compare addresses between servers
compare_servers() {
    print_section "Comparing candidate addresses between servers"

    local server1=$1
    local server2=$2
    local file1=$3
    local file2=$4

    echo "Downloading address lists..."

    # Extract addresses from both servers
    echo "Extracting addresses from server 1..."
    ssh root@$server1 "cut -d',' -f1 $file1 | tail -n +2 | sort > /tmp/addresses1.txt"

    echo "Extracting addresses from server 2..."
    ssh root@$server2 "cut -d',' -f1 $file2 | tail -n +2 | sort > /tmp/addresses2.txt"

    # Find unique and common addresses
    echo -e "\nComparing..."
    ssh root@$server1 "comm -12 /tmp/addresses1.txt <(scp -q root@$server2:/tmp/addresses2.txt - | sort) | wc -l" || true
}

# Main menu
main() {
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════╗"
    echo "║  Bitcoin Keypair Verification Tool        ║"
    echo "║  Remote Candidate Checker                 ║"
    echo "╚════════════════════════════════════════════╝"
    echo -e "${NC}"

    if [ $# -eq 0 ]; then
        echo "Usage:"
        echo "  $0 verify-remote <server_ip> <csv_file> [sample_size] [sample_every]"
        echo "  $0 download <server_ip> <remote_file> [local_file] [sample_size]"
        echo "  $0 verify-all"
        echo ""
        echo "Examples:"
        echo "  $0 verify-remote 195.26.253.243 /root/all_candidates_server1_NEW.csv 100"
        echo "  $0 verify-remote 195.26.253.243 /root/all_candidates_server1_NEW.csv 1000 10"
        echo "  $0 download 195.26.253.243 /root/all_candidates_server1_NEW.csv"
        echo "  $0 verify-all"
        exit 1
    fi

    case "$1" in
        verify-remote)
            verify_remote_candidates "${@:2}"
            ;;
        download)
            download_and_verify "${@:2}"
            ;;
        verify-all)
            verify_all_servers
            ;;
        *)
            print_error "Unknown command: $1"
            $0
            ;;
    esac
}

main "$@"
