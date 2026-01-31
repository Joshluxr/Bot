#!/bin/bash
# Quick verification wrapper for Bitcoin keypairs

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Quick Keypair Verification Tool       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}\n"

# Check if coincurve is installed
if ! python3 -c "import coincurve" 2>/dev/null; then
    echo -e "${YELLOW}⚠ coincurve not installed. Installing...${NC}"
    pip install coincurve --break-system-packages -q
    echo -e "${GREEN}✓ coincurve installed${NC}\n"
fi

# If no arguments, show help
if [ $# -eq 0 ]; then
    echo "Usage:"
    echo "  1. Verify CSV file (quick check first 10 lines):"
    echo "     $0 <file.csv>"
    echo ""
    echo "  2. Verify CSV file with custom sample size:"
    echo "     $0 <file.csv> <num_lines>"
    echo ""
    echo "  3. Verify CSV file with sampling:"
    echo "     $0 <file.csv> <num_lines> <sample_every>"
    echo ""
    echo "  4. Verify single keypair:"
    echo "     $0 <privkey_hex> <address>"
    echo ""
    echo "  5. Run test suite:"
    echo "     $0 test"
    echo ""
    echo "Examples:"
    echo "  $0 candidates.csv                    # Quick check first 10 lines"
    echo "  $0 candidates.csv 100                # Check first 100 lines"
    echo "  $0 candidates.csv 1000 10            # Check 1000 lines, sample every 10th"
    echo "  $0 0000...001 1EHNa6Q4Jz...          # Verify single keypair"
    echo "  $0 test                              # Run tests"
    exit 0
fi

# Handle test command
if [ "$1" == "test" ]; then
    echo -e "${GREEN}Running test suite...${NC}\n"
    python3 "$SCRIPT_DIR/test_verify.py"
    exit $?
fi

# If first argument is a file, verify it
if [ -f "$1" ]; then
    FILE="$1"
    LINES="${2:-10}"  # Default to 10 lines if not specified
    SAMPLE="${3:-1}"   # Default to every line

    echo -e "${GREEN}File:${NC} $FILE"
    echo -e "${GREEN}Lines to check:${NC} $LINES"
    echo -e "${GREEN}Sample rate:${NC} every $SAMPLE line(s)"
    echo ""

    # Show file info
    echo "File info:"
    ls -lh "$FILE"
    echo "Total lines: $(wc -l < "$FILE")"
    echo ""

    # Show first few lines
    echo "Preview (first 3 lines):"
    head -3 "$FILE"
    echo ""

    # Run verification
    python3 "$SCRIPT_DIR/verify_keypairs.py" "$FILE" "$LINES" "$SAMPLE"
    exit $?
fi

# Otherwise, assume it's a keypair
if [ $# -eq 2 ]; then
    PRIVKEY="$1"
    ADDRESS="$2"

    echo -e "${GREEN}Verifying single keypair...${NC}\n"
    python3 "$SCRIPT_DIR/verify_keypairs.py" "$PRIVKEY" "$ADDRESS"
    exit $?
fi

echo "Invalid arguments. Run without arguments for help."
exit 1
