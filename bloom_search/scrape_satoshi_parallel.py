#!/usr/bin/env python3
"""
Scrape Satoshi addresses from privatekeyfinder.io in parallel
440 pages, 50 addresses per page = 22,000 addresses
"""
import urllib.request
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Bitcoin address pattern (P2PKH starting with 1)
ADDR_PATTERN = re.compile(r'\b1[a-km-zA-HJ-NP-Z1-9]{25,34}\b')

# Thread-safe set for addresses
addresses = set()
lock = threading.Lock()
completed = 0

def fetch_page(page_num):
    """Fetch addresses from a single page"""
    global completed
    try:
        url = f"https://privatekeyfinder.io/satoshi-wallets?page={page_num}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        # Extract addresses
        found = ADDR_PATTERN.findall(html)
        
        # Filter to unique valid addresses (exclude short matches)
        valid = [a for a in found if len(a) >= 26 and len(a) <= 35]
        
        with lock:
            for addr in valid:
                addresses.add(addr)
            completed += 1
            if completed % 20 == 0:
                print(f"Progress: {completed}/440 pages, {len(addresses)} unique addresses")
                sys.stdout.flush()
        
        return len(valid)
    except Exception as e:
        with lock:
            completed += 1
        return 0

# Total pages
TOTAL_PAGES = 440
THREADS = 100

print(f"Scraping {TOTAL_PAGES} pages with {THREADS} threads...")
print(f"Expected: ~22,000 Satoshi addresses")
sys.stdout.flush()

start_time = time.time()

# Fetch all pages in parallel
with ThreadPoolExecutor(max_workers=THREADS) as executor:
    futures = {executor.submit(fetch_page, p): p for p in range(1, TOTAL_PAGES + 1)}
    
    for future in as_completed(futures):
        pass  # Progress printed in fetch_page

elapsed = time.time() - start_time
print(f"\nDone in {elapsed:.1f} seconds!")
print(f"Total unique addresses: {len(addresses)}")

# Save to file
outpath = "satoshi_addresses_scraped.txt"
with open(outpath, "w") as f:
    for addr in sorted(addresses):
        f.write(f"{addr}\n")

print(f"Saved to {outpath}")
