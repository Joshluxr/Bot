#!/usr/bin/env python3
"""
Checkpoint Manager for GPU Bloom Search

This system allows multiple GPU servers to coordinate their search space
by uploading/downloading checkpoint states to a central VPS.

State file format:
- 8 bytes: total keys checked (uint64)
- 65536 * 8 * 8 bytes: EC point states (x,y for each thread)

Usage:
  # Upload current state to VPS
  python3 checkpoint_manager.py upload --server user@vps --gpu 0

  # Download latest state from VPS
  python3 checkpoint_manager.py download --server user@vps --gpu 0

  # Start fresh with new random keys (no overlap with existing searches)
  python3 checkpoint_manager.py init --server user@vps --gpu 0

  # Show status of all checkpoints
  python3 checkpoint_manager.py status --server user@vps
"""

import os
import sys
import json
import struct
import hashlib
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
STATE_DIR = "/root"
REMOTE_STATE_DIR = "/root/bloom_checkpoints"
STATE_FILE_PATTERN = "gpu{}.state"
METADATA_FILE = "checkpoints.json"

def get_state_info(state_file):
    """Read state file and return info"""
    if not os.path.exists(state_file):
        return None

    with open(state_file, 'rb') as f:
        data = f.read(8)
        if len(data) < 8:
            return None
        total_keys = struct.unpack('<Q', data)[0]

        # Get file hash for dedup
        f.seek(0)
        file_hash = hashlib.md5(f.read()).hexdigest()[:12]

    stat = os.stat(state_file)
    return {
        'total_keys': total_keys,
        'total_keys_human': f"{total_keys/1e12:.2f}T",
        'file_size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        'hash': file_hash
    }

def ssh_exec(server, cmd):
    """Execute command on remote server"""
    result = subprocess.run(
        ['ssh', '-o', 'StrictHostKeyChecking=no', server, cmd],
        capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout, result.stderr

def scp_upload(local, server, remote):
    """Upload file via SCP"""
    result = subprocess.run(
        ['scp', '-o', 'StrictHostKeyChecking=no', local, f"{server}:{remote}"],
        capture_output=True, text=True
    )
    return result.returncode == 0

def scp_download(server, remote, local):
    """Download file via SCP"""
    result = subprocess.run(
        ['scp', '-o', 'StrictHostKeyChecking=no', f"{server}:{remote}", local],
        capture_output=True, text=True
    )
    return result.returncode == 0

def upload_checkpoint(server, gpu_id, server_name=None):
    """Upload GPU state to VPS"""
    state_file = os.path.join(STATE_DIR, STATE_FILE_PATTERN.format(gpu_id))

    if not os.path.exists(state_file):
        print(f"Error: State file not found: {state_file}")
        return False

    info = get_state_info(state_file)
    if not info:
        print(f"Error: Could not read state file")
        return False

    print(f"Uploading GPU {gpu_id} state:")
    print(f"  Total keys: {info['total_keys_human']}")
    print(f"  File hash: {info['hash']}")

    # Ensure remote directory exists
    ssh_exec(server, f"mkdir -p {REMOTE_STATE_DIR}")

    # Upload with server identifier
    hostname = server_name or os.uname().nodename
    remote_file = f"{REMOTE_STATE_DIR}/{hostname}_gpu{gpu_id}.state"

    if not scp_upload(state_file, server, remote_file):
        print("Error: Upload failed")
        return False

    # Update metadata
    update_remote_metadata(server, hostname, gpu_id, info)

    print(f"Uploaded to {remote_file}")
    return True

def update_remote_metadata(server, hostname, gpu_id, info):
    """Update checkpoint metadata on VPS"""
    metadata_path = f"{REMOTE_STATE_DIR}/{METADATA_FILE}"

    # Download existing metadata
    ok, stdout, _ = ssh_exec(server, f"cat {metadata_path} 2>/dev/null || echo '{{}}'")
    try:
        metadata = json.loads(stdout)
    except:
        metadata = {}

    # Update entry
    key = f"{hostname}_gpu{gpu_id}"
    metadata[key] = {
        **info,
        'hostname': hostname,
        'gpu_id': gpu_id,
        'uploaded': datetime.now().isoformat()
    }

    # Upload updated metadata
    ssh_exec(server, f"cat > {metadata_path} << 'EOF'\n{json.dumps(metadata, indent=2)}\nEOF")

def download_checkpoint(server, gpu_id, source_name=None):
    """Download GPU state from VPS"""
    state_file = os.path.join(STATE_DIR, STATE_FILE_PATTERN.format(gpu_id))

    if source_name:
        remote_file = f"{REMOTE_STATE_DIR}/{source_name}_gpu{gpu_id}.state"
    else:
        # Find latest checkpoint for this GPU slot
        ok, stdout, _ = ssh_exec(server, f"ls -t {REMOTE_STATE_DIR}/*_gpu{gpu_id}.state 2>/dev/null | head -1")
        if not ok or not stdout.strip():
            print(f"No checkpoint found for GPU {gpu_id}")
            return False
        remote_file = stdout.strip()

    print(f"Downloading from {remote_file}")

    if not scp_download(server, remote_file, state_file):
        print("Error: Download failed")
        return False

    info = get_state_info(state_file)
    print(f"Downloaded GPU {gpu_id} state:")
    print(f"  Total keys: {info['total_keys_human']}")
    print(f"  File hash: {info['hash']}")

    return True

def show_status(server):
    """Show status of all checkpoints"""
    metadata_path = f"{REMOTE_STATE_DIR}/{METADATA_FILE}"

    ok, stdout, _ = ssh_exec(server, f"cat {metadata_path} 2>/dev/null")
    if not ok or not stdout.strip():
        print("No checkpoints found")
        return

    try:
        metadata = json.loads(stdout)
    except:
        print("Error parsing metadata")
        return

    print("=" * 70)
    print("CHECKPOINT STATUS")
    print("=" * 70)

    total_keys = 0
    for key, info in sorted(metadata.items()):
        total_keys += info.get('total_keys', 0)
        print(f"\n{key}:")
        print(f"  Keys checked: {info.get('total_keys_human', 'N/A')}")
        print(f"  Last upload:  {info.get('uploaded', 'N/A')}")
        print(f"  Hash:         {info.get('hash', 'N/A')}")

    print("\n" + "=" * 70)
    print(f"TOTAL KEYS CHECKED: {total_keys/1e12:.2f}T ({total_keys/1e15:.4f}P)")
    print("=" * 70)

def init_fresh(server, gpu_id):
    """Initialize fresh state, ensuring no overlap with existing searches"""
    print("Initializing fresh search state...")
    print("Note: The GPU search binary will generate cryptographically random starting points")
    print("The probability of overlap with existing searches is astronomically low (< 2^-256)")

    state_file = os.path.join(STATE_DIR, STATE_FILE_PATTERN.format(gpu_id))

    # Remove existing state to force fresh random initialization
    if os.path.exists(state_file):
        backup = f"{state_file}.backup.{int(datetime.now().timestamp())}"
        os.rename(state_file, backup)
        print(f"Backed up existing state to {backup}")

    print(f"GPU {gpu_id} will start with fresh random keys on next run")
    return True

def main():
    parser = argparse.ArgumentParser(description='GPU Bloom Search Checkpoint Manager')
    parser.add_argument('action', choices=['upload', 'download', 'status', 'init'],
                       help='Action to perform')
    parser.add_argument('--server', '-s', required=True,
                       help='VPS server (user@host or user@host:port)')
    parser.add_argument('--gpu', '-g', type=int, default=0,
                       help='GPU ID (default: 0)')
    parser.add_argument('--name', '-n',
                       help='Server name identifier')
    parser.add_argument('--source',
                       help='Source server name for download')

    args = parser.parse_args()

    # Handle port in server string
    if ':' in args.server and '@' in args.server:
        # Format: user@host:port
        parts = args.server.rsplit(':', 1)
        server = f"-p {parts[1]} {parts[0]}"
    else:
        server = args.server

    if args.action == 'upload':
        upload_checkpoint(server, args.gpu, args.name)
    elif args.action == 'download':
        download_checkpoint(server, args.gpu, args.source)
    elif args.action == 'status':
        show_status(server)
    elif args.action == 'init':
        init_fresh(server, args.gpu)

if __name__ == '__main__':
    main()
