#!/usr/bin/env python3
"""
Range Splitter for SearchK4
Converts a decimal key range into 8 GPU sub-ranges in hexadecimal.

Usage:
    python3 range_splitter.py <start_decimal> <end_decimal>

Example:
    python3 range_splitter.py \
      82988190356384517260073324955726623558128682318812983971013110423526066342990 \
      82988190356384517260073324955726623558128682318812983971013120423526066342990
"""

import sys

def split_range(start_dec: int, end_dec: int, num_gpus: int = 8):
    total = end_dec - start_dec
    per_gpu = total // num_gpus
    remainder = total % num_gpus

    print(f"Total range: {total:,} keys")
    print(f"Per GPU: {per_gpu:,} keys")
    print(f"Remainder (added to last GPU): {remainder:,}")
    print()

    starts = []
    ends = []

    for i in range(num_gpus):
        gpu_start = start_dec + (i * per_gpu)
        if i == num_gpus - 1:
            gpu_end = end_dec  # Last GPU gets remainder
        else:
            gpu_end = start_dec + ((i + 1) * per_gpu) - 1

        starts.append(gpu_start)
        ends.append(gpu_end)

        print(f"GPU {i}:")
        print(f"  Decimal: {gpu_start} -> {gpu_end}")
        print(f"  Hex:     {hex(gpu_start)} -> {hex(gpu_end)}")
        print()

    # Output bash arrays for copy-paste into launch script
    print("\n# Bash arrays for launch script:")
    print("STARTS=(")
    for s in starts:
        print(f"  {hex(s)}")
    print(")")
    print("ENDS=(")
    for e in ends:
        print(f"  {hex(e)}")
    print(")")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    start = int(sys.argv[1])
    end = int(sys.argv[2])

    if end <= start:
        print("Error: end must be greater than start")
        sys.exit(1)

    split_range(start, end)
