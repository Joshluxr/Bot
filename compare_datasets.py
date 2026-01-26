#!/usr/bin/env python3
"""
Compare the downloaded dataset with existing datasets to identify:
1. Total unique addresses across all datasets
2. Addresses unique to the new dataset
3. Overlap between datasets
"""

import csv
from collections import defaultdict

def load_addresses(filename):
    """Load addresses from a CSV file"""
    addresses = set()
    try:
        with open(filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'address' in row:
                    addresses.add(row['address'])
        print(f"Loaded {len(addresses):,} addresses from {filename}")
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return addresses

def main():
    print("=" * 80)
    print("BITCOIN ADDRESS DATASET COMPARISON")
    print("=" * 80)
    print()

    # Load all datasets
    datasets = {
        'downloaded': '/tmp/final_downloaded.csv',
        'final.csv': './final.csv',
        'final_latest.csv': './final_latest.csv',
        'final_new.csv': './final_new.csv'
    }

    loaded_sets = {}
    for name, path in datasets.items():
        print(f"Loading {name}...")
        loaded_sets[name] = load_addresses(path)

    print()
    print("=" * 80)
    print("DATASET STATISTICS")
    print("=" * 80)

    # Calculate unique addresses
    all_addresses = set()
    for addresses in loaded_sets.values():
        all_addresses.update(addresses)

    print(f"\nTotal unique addresses across ALL datasets: {len(all_addresses):,}")
    print()

    # Check what's unique in the downloaded dataset
    downloaded = loaded_sets['downloaded']
    existing = set()
    for name, addresses in loaded_sets.items():
        if name != 'downloaded':
            existing.update(addresses)

    unique_to_downloaded = downloaded - existing
    unique_to_existing = existing - downloaded
    common = downloaded & existing

    print(f"Addresses in downloaded dataset: {len(downloaded):,}")
    print(f"Addresses in existing datasets (combined): {len(existing):,}")
    print(f"Common addresses (overlap): {len(common):,}")
    print(f"Unique to downloaded dataset: {len(unique_to_downloaded):,}")
    print(f"Unique to existing datasets: {len(unique_to_existing):,}")
    print()

    # Detailed comparison with each existing dataset
    print("=" * 80)
    print("PAIRWISE COMPARISONS")
    print("=" * 80)
    print()

    for name, addresses in loaded_sets.items():
        if name != 'downloaded':
            overlap = downloaded & addresses
            only_in_downloaded = downloaded - addresses
            only_in_other = addresses - downloaded

            print(f"Downloaded vs {name}:")
            print(f"  Overlap: {len(overlap):,} addresses")
            print(f"  Only in downloaded: {len(only_in_downloaded):,}")
            print(f"  Only in {name}: {len(only_in_other):,}")
            print()

    # Determine best dataset
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Find the superset dataset
    superset_candidates = []
    for name, addresses in loaded_sets.items():
        is_superset = True
        for other_name, other_addresses in loaded_sets.items():
            if name != other_name:
                if not other_addresses.issubset(addresses):
                    is_superset = False
                    break
        if is_superset:
            superset_candidates.append((name, len(addresses)))

    if superset_candidates:
        superset_candidates.sort(key=lambda x: x[1], reverse=True)
        print(f"Superset dataset (contains all others): {superset_candidates[0][0]}")
        print(f"  Size: {superset_candidates[0][1]:,} addresses")
    else:
        largest = max(loaded_sets.items(), key=lambda x: len(x[1]))
        print(f"No single dataset contains all others.")
        print(f"Largest dataset: {largest[0]} with {len(largest[1]):,} addresses")
        print(f"Combined unique addresses: {len(all_addresses):,}")

    print()

    # Save unique addresses from downloaded dataset
    if unique_to_downloaded:
        print(f"Saving {len(unique_to_downloaded):,} unique addresses to 'unique_from_download.txt'")
        with open('unique_from_download.txt', 'w') as f:
            for addr in sorted(unique_to_downloaded):
                f.write(f"{addr}\n")

    print()
    print("Analysis complete!")

if __name__ == '__main__':
    main()
