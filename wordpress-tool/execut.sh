#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SCRIPT="BRUTER.py"
SITES_DIR="sites"
INSTANCES="${INSTANCES:-1}"

echo
echo "═══════════════════════════════════════════════════════════"
echo "       WORDPRESS MULTI-BRUTEFORCE MANAGER (Linux)"
echo "═══════════════════════════════════════════════════════════"
echo

if [[ ! -f "$SCRIPT" ]]; then
  echo "[ERROR] $SCRIPT not found in $SCRIPT_DIR"
  exit 1
fi

mkdir -p "$SITES_DIR" readyTouse Files

if ! python3 -c "import requests, colorama" 2>/dev/null; then
  echo "[~] Installing Python dependencies..."
  pip install -r requirements.txt -q
fi

mapfile -t SITE_FILES < <(find "$SITES_DIR" -maxdepth 1 -type f -name '*.txt' | sort)

if [[ ${#SITE_FILES[@]} -eq 0 ]]; then
  echo "[WARNING] No site lists in $SITES_DIR/*.txt"
  echo "[INFO] Add targets (one URL per line) then re-run."
  echo "[INFO] Example: echo 'https://your-lab-site.local' > sites/lab.txt"
  exit 1
fi

echo "[~] Found ${#SITE_FILES[@]} site file(s):"
printf '    - %s\n' "${SITE_FILES[@]}"
echo

for ((i = 0; i < INSTANCES && i < ${#SITE_FILES[@]}; i++)); do
  file="${SITE_FILES[$i]}"
  echo "[!] Instance $((i + 1)): python3 $SCRIPT \"$file\""
  python3 "$SCRIPT" "$file" &
  sleep 1
done

wait
echo
echo "[SUCCESS] All instances finished."
