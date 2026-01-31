#!/usr/bin/env python3
"""
Create sample candidate data and demonstrate verification.
This simulates what your actual candidate files should look like.
"""

import sys
import os
sys.path.insert(0, '/root/repo')

from verify_keypairs import verify_keypair, privkey_to_pubkey, hash160, hash160_to_address

def create_sample_candidates():
    """Create a sample candidate file similar to your GPU server output"""

    sample_file = "/tmp/sample_candidates.csv"

    print("Creating sample candidate file...")
    print("Format: address,privkey,hash160")
    print()

    # Generate some valid test candidates
    candidates = []

    for i in range(1, 11):
        # Generate private key
        privkey = f"{i:064x}"

        # Generate corresponding public key and address
        pubkey = privkey_to_pubkey(privkey)
        if pubkey:
            h160 = hash160(pubkey).hex()
            address = hash160_to_address(h160)

            candidates.append({
                'address': address,
                'privkey': privkey,
                'hash160': h160
            })

    # Write to CSV
    with open(sample_file, 'w') as f:
        f.write("address,privkey,hash160\n")
        for c in candidates:
            f.write(f"{c['address']},{c['privkey']},{c['hash160']}\n")

    print(f"✓ Created: {sample_file}")
    print(f"  Lines: {len(candidates) + 1}")
    print()

    # Show first few lines
    print("Preview:")
    with open(sample_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 4:
                print(f"  {line.strip()}")
    print()

    return sample_file

def verify_sample(sample_file):
    """Verify the sample file"""
    print("=" * 80)
    print("VERIFYING SAMPLE CANDIDATES")
    print("=" * 80)
    print()

    total = 0
    valid = 0
    invalid = 0

    with open(sample_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Skip header
            if line_num == 1:
                continue

            parts = line.strip().split(',')
            if len(parts) < 3:
                continue

            address, privkey, hash160_expected = parts[0], parts[1], parts[2]

            # Verify
            is_valid, msg = verify_keypair(privkey, address, hash160_expected)

            total += 1
            if is_valid:
                valid += 1
                print(f"Line {line_num}: ✓ VALID")
            else:
                invalid += 1
                print(f"\nLine {line_num}: ✗ INVALID")
                print(f"  {msg}")
                print()

    print()
    print("=" * 80)
    print("RESULTS:")
    print(f"  Total: {total}")
    print(f"  Valid: {valid} ({100*valid/total if total > 0 else 0:.1f}%)")
    print(f"  Invalid: {invalid}")
    print("=" * 80)

def demonstrate_mismatch():
    """Show what happens when private key doesn't match address"""
    print("\n\n")
    print("=" * 80)
    print("DEMONSTRATION: What happens with MISMATCHED keypair")
    print("=" * 80)
    print()

    # Use privkey 1 with privkey 2's address (intentional mismatch)
    wrong_privkey = "0000000000000000000000000000000000000000000000000000000000000001"
    wrong_address = "1LagHJk2FyCV2VzrNHVqg3gYG4TSYwDV4m"  # This is privkey=2's address

    print("Testing MISMATCHED keypair:")
    print(f"  Private Key: {wrong_privkey} (this is privkey for 1EHNa6Q4Jz...)")
    print(f"  Address: {wrong_address} (this is address for privkey=2)")
    print()

    is_valid, msg = verify_keypair(wrong_privkey, wrong_address)
    print(f"Result: {msg}")
    print()
    print("This is what you'll see if your candidate data has mismatched keys!")
    print("=" * 80)

def main():
    print()
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  Bitcoin Keypair Verification - Sample Demonstration      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Check library
    try:
        import coincurve
        print("✓ coincurve library available")
    except ImportError:
        print("⚠ Installing coincurve...")
        os.system("pip install coincurve --break-system-packages -q")

    print()

    # Create sample
    sample_file = create_sample_candidates()

    # Verify it
    verify_sample(sample_file)

    # Show mismatch example
    demonstrate_mismatch()

    print("\n")
    print("Next Steps:")
    print("=" * 80)
    print("To verify YOUR actual candidate files from GPU servers:")
    print()
    print("  1. Verify Server 1:")
    print("     ./verify_my_candidates.sh server1")
    print()
    print("  2. Verify Server 2:")
    print("     ./verify_my_candidates.sh server2")
    print()
    print("  3. Verify both servers:")
    print("     ./verify_my_candidates.sh both")
    print()
    print("Files to verify:")
    print("  - Server 1: /root/all_candidates_server1_NEW.csv (3.2M candidates)")
    print("  - Server 2: /root/all_candidates_server2_NEW.csv (5.5M candidates)")
    print("=" * 80)

if __name__ == '__main__':
    main()
