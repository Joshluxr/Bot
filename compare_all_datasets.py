#!/usr/bin/env python3
"""
Compare all datasets to find overlaps and unique addresses
"""

def load_addresses_from_csv(filename):
    """Load addresses from CSV with header"""
    addresses = set()
    with open(filename, 'r') as f:
        next(f)  # Skip header
        for line in f:
            parts = line.strip().split(',')
            if parts:
                addresses.add(parts[0])
    return addresses

def load_addresses_from_txt(filename):
    """Load addresses from txt without header"""
    addresses = set()
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split(',')
            if parts:
                addresses.add(parts[0])
    return addresses

def main():
    print("=" * 80)
    print("COMPARING ALL DATASETS")
    print("=" * 80)
    print()

    # Load all datasets
    print("Loading datasets...")

    dataset1 = load_addresses_from_csv('./final_complete.csv')
    print(f"final_complete.csv: {len(dataset1):,} addresses")

    dataset2 = load_addresses_from_txt('/tmp/all_candidates_final.txt')
    print(f"all_candidates_final.txt: {len(dataset2):,} addresses")

    print()
    print("=" * 80)
    print("COMPARISON ANALYSIS")
    print("=" * 80)
    print()

    # Find overlaps and unique
    common = dataset1 & dataset2
    only_in_complete = dataset1 - dataset2
    only_in_candidates = dataset2 - dataset1

    print(f"Common addresses (in both): {len(common):,}")
    print(f"Only in final_complete.csv: {len(only_in_complete):,}")
    print(f"Only in all_candidates_final.txt: {len(only_in_candidates):,}")
    print()

    # Total unique across both
    all_unique = dataset1 | dataset2
    print(f"Total unique addresses across both: {len(all_unique):,}")
    print()

    # Calculate percentages
    if len(dataset2) > 0:
        overlap_pct = (len(common) / len(dataset2)) * 100
        print(f"Overlap: {overlap_pct:.1f}% of all_candidates_final.txt is in final_complete.csv")

    print()

    # Determine which is the superset
    if len(only_in_complete) == 0:
        print("✅ all_candidates_final.txt is a SUPERSET (contains all of final_complete.csv)")
    elif len(only_in_candidates) == 0:
        print("✅ final_complete.csv is a SUPERSET (contains all of all_candidates_final.txt)")
    else:
        print("⚠️  Neither is a complete superset - both have unique addresses")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    if len(all_unique) > len(dataset1):
        print(f"Consider merging datasets to get {len(all_unique):,} total unique addresses")
        print(f"This would add {len(only_in_candidates):,} new addresses to final_complete.csv")
    else:
        print("final_complete.csv already contains all addresses from all_candidates_final.txt")

    # Save unique addresses from candidates
    if only_in_candidates:
        print()
        print(f"Saving {len(only_in_candidates):,} unique addresses from candidates to file...")
        with open('unique_in_candidates.txt', 'w') as f:
            for addr in sorted(only_in_candidates):
                f.write(f"{addr}\n")
        print("Saved to 'unique_in_candidates.txt'")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
