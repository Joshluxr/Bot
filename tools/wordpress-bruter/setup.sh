#!/usr/bin/env bash
# Setup Wordpress-Bruter-And-Upload-Shell (bossxz238) for Linux/cloud agents.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${ROOT}/vendor/Wordpress-Bruter-And-Upload-Shell"
ZIP_URL="https://github.com/bossxz238/Wordpress-Bruter-And-Upload-Shell/raw/refs/heads/main/rainproofer/Wordpress-Bruter-Shell-And-Upload-2.3.zip"
EXTRACT_DIR="${ROOT}/vendor/extracted"

echo "[*] Installing Python dependencies..."
python3 -m pip install -q -r "${ROOT}/requirements.txt"

if [[ ! -d "${REPO_DIR}/.git" ]]; then
  echo "[*] Cloning upstream repository..."
  git clone --depth 1 https://github.com/bossxz238/Wordpress-Bruter-And-Upload-Shell.git "${REPO_DIR}"
fi

mkdir -p "${EXTRACT_DIR}"
if [[ ! -f "${EXTRACT_DIR}/static.txt" ]]; then
  echo "[*] Downloading Windows release bundle..."
  curl -fsSL -o "${ROOT}/vendor/tool.zip" "${ZIP_URL}"
  unzip -qo "${ROOT}/vendor/tool.zip" -d "${EXTRACT_DIR}"
fi

echo "[*] Upstream bundle: ${EXTRACT_DIR}"
echo "[*] Linux runner: ${ROOT}/wp_bruter.py"
echo "[+] Setup complete. Run tests: ${ROOT}/run_tests.sh"
