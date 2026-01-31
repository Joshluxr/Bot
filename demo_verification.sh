#!/bin/bash
# Demonstration of the keypair verification toolkit

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

clear

echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     Bitcoin Keypair Verification Toolkit - DEMO              ║
║                                                               ║
║     This demo shows how to verify Bitcoin keypairs           ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

pause() {
    echo -e "\n${YELLOW}Press Enter to continue...${NC}"
    read
}

section() {
    echo -e "\n${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}\n"
}

section "DEMO 1: Testing with Known Bitcoin Keypairs"

echo "We'll verify some well-known Bitcoin keypairs to show the tool works correctly."
echo ""
echo "Testing private key = 1:"
echo "  Expected address: 1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"
echo ""

pause

python3 "$SCRIPT_DIR/test_verify.py"

pause

section "DEMO 2: Creating Sample Test Data"

# Create a sample CSV file with known keypairs
DEMO_CSV="/tmp/demo_candidates.csv"

echo "Creating sample CSV file with test keypairs..."
echo ""

cat > "$DEMO_CSV" << 'CSVEOF'
address,privkey,hash160
1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm,0000000000000000000000000000000000000000000000000000000000000001,91b24bf9f5288532960ac687abb035127b1d28a5
1LagHJk2FyCV2VzrNHVqg3gYG4TSYwDV4m,0000000000000000000000000000000000000000000000000000000000000002,65a9bef8cc853fa6933bb4911d3e0fc55ab46489
1Dn8NF8qDyyfHMktmuoQLGyjWmZXgvosXf,0000000000000000000000000000000000000000000000000000000000000003,8fd139bb39ffe5f0f781b06ef9e0b19dc62dadaa
1F3sAm6ZtwLAUnj7d38pGFxtP3RVEvtsbV,0000000000000000000000000000000000000000000000000000000000000004,39a42e6cc87d9e5e0dc8a6d87b0ea5e3af7e7ea5
1Bvjij5653y9rzcLFTfLvZL5EUF5pBskzz,0000000000000000000000000000000000000000000000000000000000000005,df7a08da69f86f7e9d1d31a0c3c71b72b5978e14
CSVEOF

echo -e "${GREEN}✓ Created sample file: $DEMO_CSV${NC}"
echo ""
echo "Contents:"
cat "$DEMO_CSV"

pause

section "DEMO 3: Verifying CSV File"

echo "Now let's verify the keypairs in the CSV file..."
echo ""

"$SCRIPT_DIR/quick_verify.sh" "$DEMO_CSV"

pause

section "DEMO 4: Adding an INVALID Keypair"

echo "Let's add an invalid entry to show how mismatches are detected..."
echo ""

# Add invalid entry (wrong private key for the address)
echo "1InvalidMatchTest,0000000000000000000000000000000000000000000000000000000000000001,0000000000000000000000000000000000000000" >> "$DEMO_CSV"

echo -e "${YELLOW}Added invalid entry with mismatched private key${NC}"
echo ""

pause

echo "Verifying file again (should show 1 invalid entry):"
echo ""

"$SCRIPT_DIR/quick_verify.sh" "$DEMO_CSV"

pause

section "DEMO 5: Verifying Single Keypair"

echo "You can also verify individual keypairs without a CSV file..."
echo ""
echo "Command: ./quick_verify.sh <privkey> <address>"
echo ""

pause

"$SCRIPT_DIR/quick_verify.sh" \
    "0000000000000000000000000000000000000000000000000000000000000001" \
    "1EHNa6Q4Jz2uvNExL497mE43ikXhwF6kZm"

pause

section "DEMO 6: Sampling Large Files"

echo "For large files, you can sample every Nth entry..."
echo ""

# Create a larger demo file
LARGE_CSV="/tmp/demo_large_candidates.csv"
echo "address,privkey,hash160" > "$LARGE_CSV"

echo "Creating a larger sample file with 100 entries..."

for i in {1..100}; do
    # Generate valid keypairs (using sequential private keys for demo)
    printf -v privkey "%064x" $i
    # We'll just use placeholders since this is a demo of sampling
    echo "1DemoAddress${i},${privkey},0000000000000000000000000000000000000000" >> "$LARGE_CSV"
done

wc -l "$LARGE_CSV"

echo ""
echo "Now let's verify every 10th entry (should check 10 entries total):"
echo ""

pause

# Only check every 10th line
python3 "$SCRIPT_DIR/verify_keypairs.py" "$LARGE_CSV" 100 10

pause

section "DEMO 7: Using with Real Candidate Data"

echo -e "${BLUE}When you have real candidate data from your GPU servers:${NC}"
echo ""
echo "1. Quick local verification:"
echo "   ${YELLOW}./quick_verify.sh /path/to/candidates.csv 100${NC}"
echo ""
echo "2. Verify on remote server (without downloading):"
echo "   ${YELLOW}./check_remote_candidates.sh verify-remote 195.26.253.243 /root/candidates.csv${NC}"
echo ""
echo "3. Verify all configured servers:"
echo "   ${YELLOW}./check_remote_candidates.sh verify-all${NC}"
echo ""
echo "4. Full verification of large file (with sampling):"
echo "   ${YELLOW}python3 verify_keypairs.py /path/to/candidates.csv 100000 100${NC}"
echo "   (checks 100,000 lines, sampling every 100th line = 1,000 verifications)"

pause

section "DEMO Complete!"

echo -e "${GREEN}✓ Verification toolkit demonstration complete!${NC}"
echo ""
echo "Summary of tools:"
echo ""
echo "  ${BLUE}verify_keypairs.py${NC}          - Core verification engine"
echo "  ${BLUE}quick_verify.sh${NC}             - Easy-to-use wrapper"
echo "  ${BLUE}check_remote_candidates.sh${NC}  - Remote server verification"
echo "  ${BLUE}test_verify.py${NC}              - Test suite"
echo ""
echo "Documentation:"
echo ""
echo "  ${BLUE}KEYPAIR_VERIFICATION_README.md${NC}  - Quick start guide"
echo "  ${BLUE}KEYPAIR_VERIFICATION_GUIDE.md${NC}   - Detailed technical guide"
echo ""
echo -e "${YELLOW}Cleaning up demo files...${NC}"
rm -f "$DEMO_CSV" "$LARGE_CSV"
echo -e "${GREEN}✓ Demo files removed${NC}"
echo ""
echo -e "${GREEN}You're ready to verify your Bitcoin keypairs!${NC}\n"
