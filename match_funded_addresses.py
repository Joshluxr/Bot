#!/usr/bin/env python3
"""
Advanced Bitcoin Address Matching System
Matches candidate addresses against funded addresses database with detailed analysis
"""

import sys
import os
import gzip
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, List, Tuple
import hashlib

# Configuration
WORK_DIR = Path("/root/address_matching")
CANDIDATES_DIR = WORK_DIR / "candidates"
DB_DIR = WORK_DIR / "database"
RESULTS_DIR = WORK_DIR / "results"

# URLs
CANDIDATE_URLS = {
    "server1": "https://tmpfiles.org/dl/21294684/server1_candidates.txt",
    "server2": "https://tmpfiles.org/dl/21294681/server2_candidates.txt",
    "server4": "https://tmpfiles.org/dl/21294682/server4_candidates.txt",
}

FUNDED_DB_URL = "http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz"

EXPECTED_COUNTS = {
    "server1": 153690,
    "server2": 51274,
    "server4": 57958,
}


class AddressMatchingSystem:
    def __init__(self):
        self.candidates: Dict[str, Set[str]] = {}
        self.all_candidates: Set[str] = set()
        self.funded_addresses: Set[str] = set()
        self.matches: Dict[str, List[str]] = {}

        # Create directories
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
        DB_DIR.mkdir(parents=True, exist_ok=True)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def download_file(self, url: str, dest: Path, description: str) -> bool:
        """Download a file with progress indication"""
        print(f"  Downloading {description}...")
        try:
            def report_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(downloaded * 100 / total_size, 100)
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f"\r    Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end="")

            urllib.request.urlretrieve(url, dest, reporthook=report_progress)
            print()  # New line after progress
            return True
        except Exception as e:
            print(f"\n    ERROR: {e}")
            return False

    def load_candidates(self) -> bool:
        """Download and load all candidate files"""
        print("\n[1/6] Downloading and loading candidate files...")

        for server_name, url in CANDIDATE_URLS.items():
            dest = CANDIDATES_DIR / f"{server_name}_candidates.txt"

            # Download if not exists
            if not dest.exists():
                if not self.download_file(url, dest, f"{server_name} candidates"):
                    return False
            else:
                print(f"  Using cached {server_name} candidates")

            # Load addresses
            with open(dest, 'r') as f:
                addresses = set(line.strip() for line in f if line.strip())

            self.candidates[server_name] = addresses
            self.all_candidates.update(addresses)

            expected = EXPECTED_COUNTS.get(server_name, 0)
            actual = len(addresses)
            status = "✓" if actual >= expected * 0.95 else "⚠"
            print(f"    {status} {server_name}: {actual:,} addresses (expected ~{expected:,})")

        print(f"\n  Total unique candidates: {len(self.all_candidates):,}")
        return True

    def load_funded_database(self) -> bool:
        """Download and load funded addresses database"""
        print("\n[2/6] Downloading and loading funded addresses database...")

        gz_file = DB_DIR / "Bitcoin_addresses_LATEST.txt.gz"
        txt_file = DB_DIR / "Bitcoin_addresses_LATEST.txt"

        # Download if not exists
        if not gz_file.exists() and not txt_file.exists():
            if not self.download_file(FUNDED_DB_URL, gz_file, "funded addresses database"):
                return False

        # Extract if needed
        if not txt_file.exists():
            print("  Extracting database...")
            with gzip.open(gz_file, 'rb') as f_in:
                with open(txt_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            print("  ✓ Extraction complete")
        else:
            print("  Using cached database")

        # Load addresses into memory (may take a while for large files)
        print("  Loading addresses into memory...")
        with open(txt_file, 'r') as f:
            for i, line in enumerate(f):
                address = line.strip()
                if address:
                    self.funded_addresses.add(address)

                if (i + 1) % 1000000 == 0:
                    print(f"\r    Loaded {(i + 1):,} addresses...", end="")

        print(f"\n  ✓ Total funded addresses: {len(self.funded_addresses):,}")
        return True

    def perform_matching(self):
        """Match candidates against funded addresses"""
        print("\n[3/6] Performing address matching...")

        # Match all candidates
        all_matches = self.all_candidates.intersection(self.funded_addresses)
        self.matches['all'] = sorted(all_matches)

        print(f"  ✓ Total matches found: {len(all_matches):,}")

        # Match per server
        print("\n  Per-server matches:")
        for server_name, candidates in self.candidates.items():
            server_matches = candidates.intersection(self.funded_addresses)
            self.matches[server_name] = sorted(server_matches)
            print(f"    - {server_name}: {len(server_matches):,} matches")

    def save_results(self):
        """Save matching results to files"""
        print("\n[4/6] Saving results...")

        # Save all matches
        matches_file = RESULTS_DIR / "matches.txt"
        with open(matches_file, 'w') as f:
            for address in self.matches['all']:
                f.write(f"{address}\n")
        print(f"  ✓ All matches: {matches_file}")

        # Save per-server matches
        for server_name in self.candidates.keys():
            server_file = RESULTS_DIR / f"{server_name}_matches.txt"
            with open(server_file, 'w') as f:
                for address in self.matches[server_name]:
                    f.write(f"{address}\n")
            print(f"  ✓ {server_name} matches: {server_file}")

    def generate_report(self):
        """Generate detailed analysis report"""
        print("\n[5/6] Generating analysis report...")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""
{'='*80}
BITCOIN ADDRESS MATCHING REPORT
{'='*80}
Generated: {timestamp}

INPUT STATISTICS
{'='*80}
Candidate Sources:
"""

        for server_name, addresses in self.candidates.items():
            expected = EXPECTED_COUNTS.get(server_name, 0)
            report += f"  • {server_name:10} {len(addresses):>10,} addresses (expected ~{expected:,})\n"

        report += f"""
  • Total Unique: {len(self.all_candidates):>10,} addresses

Database:
  • Funded Addresses: {len(self.funded_addresses):>7,} addresses

MATCHING RESULTS
{'='*80}
"""

        total_matches = len(self.matches['all'])
        report += f"Total Matches Found: {total_matches:,}\n\n"

        if total_matches > 0:
            report += "Per-Server Breakdown:\n"
            for server_name in self.candidates.keys():
                count = len(self.matches[server_name])
                percentage = (count / len(self.candidates[server_name]) * 100) if self.candidates[server_name] else 0
                report += f"  • {server_name:10} {count:>6,} matches ({percentage:.4f}% of candidates)\n"

            report += f"\nFirst 20 Matched Addresses:\n"
            for i, address in enumerate(self.matches['all'][:20], 1):
                report += f"  {i:2d}. {address}\n"

            if total_matches > 20:
                report += f"  ... and {total_matches - 20:,} more\n"
        else:
            report += "No matches found.\n"

        report += f"""
OUTPUT FILES
{'='*80}
All Matches:     {RESULTS_DIR / 'matches.txt'}
Server 1 Matches: {RESULTS_DIR / 'server1_matches.txt'}
Server 2 Matches: {RESULTS_DIR / 'server2_matches.txt'}
Server 4 Matches: {RESULTS_DIR / 'server4_matches.txt'}

Working Directory: {WORK_DIR}
{'='*80}
"""

        # Save report
        report_file = RESULTS_DIR / "ANALYSIS_REPORT.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        # Print report
        print(report)
        print(f"  ✓ Full report saved: {report_file}")

    def display_summary(self):
        """Display final summary"""
        print("\n[6/6] Summary")
        print("="*80)
        print(f"Candidates processed: {len(self.all_candidates):,}")
        print(f"Funded addresses checked: {len(self.funded_addresses):,}")
        print(f"MATCHES FOUND: {len(self.matches['all']):,}")
        print(f"\nAll results saved to: {RESULTS_DIR}/")
        print("="*80)


def main():
    """Main execution function"""
    print("="*80)
    print("BITCOIN ADDRESS MATCHING SYSTEM")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        system = AddressMatchingSystem()

        # Execute matching pipeline
        if not system.load_candidates():
            print("\nERROR: Failed to load candidates")
            return 1

        if not system.load_funded_database():
            print("\nERROR: Failed to load funded addresses database")
            return 1

        system.perform_matching()
        system.save_results()
        system.generate_report()
        system.display_summary()

        print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return 0

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
