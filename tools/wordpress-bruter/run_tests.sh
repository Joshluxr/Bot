#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_ROOT="$(cd "${ROOT}/../../lab" && pwd)"
TARGET="${TARGET_URL:-http://127.0.0.1:18080}"
MOCK_PID=""

cleanup() {
  if [[ -n "${MOCK_PID}" ]] && kill -0 "${MOCK_PID}" 2>/dev/null; then
    kill "${MOCK_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "=== CloudFront WAF bypass tests ==="
bash "${ROOT}/setup.sh"
python3 -m pip install -q -r "${ROOT}/requirements.txt"

if command -v docker >/dev/null 2>&1; then
  echo "[*] Docker found — starting full lab..."
  docker compose -f "${LAB_ROOT}/docker-compose.yml" up -d --build
  for _ in $(seq 1 60); do
    curl -sf "${TARGET}/health" >/dev/null 2>&1 && break
    sleep 2
  done
else
  echo "[*] Docker not available — using Python mock WAF server"
  MOCK_PORT=18080 python3 -c "
import sys
sys.path.insert(0, '../../lab')
from mock_waf_server import Handler
from http.server import HTTPServer
HTTPServer(('127.0.0.1', 18080), Handler).serve_forever()
" &
  MOCK_PID=$!
  sleep 1
fi

echo ""
python3 "${ROOT}/verify_waf_bypass.py" -u "${TARGET}"

printf 'admin\n' > /tmp/lab-user.txt
printf 'admin123\n' > /tmp/lab-pass.txt
python3 "${ROOT}/wp_bruter.py" -u "${TARGET}" --bypass hyphen --users /tmp/lab-user.txt --passwords /tmp/lab-pass.txt --delay 0

echo ""
echo "=== ALL TESTS PASSED ==="
