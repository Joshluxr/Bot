"""HTTP via curl (avoids TLS fingerprint blocks on CloudFront)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

from waf_bypass import BROWSER_UA


@dataclass
class HttpResponse:
    status_code: int
    text: str
    url: str
    headers: dict[str, str]


class CurlSession:
    def __init__(self) -> None:
        self._jar = tempfile.NamedTemporaryFile(prefix="wp_cookies_", delete=False)
        self.jar_path = Path(self._jar.name)

    def request(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        allow_redirects: bool = True,
        timeout: int = 30,
    ) -> HttpResponse:
        headers = headers or {}
        headers.setdefault("User-Agent", BROWSER_UA)
        headers.setdefault("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")

        if not shutil.which("curl"):
            import requests

            if method.upper() == "GET":
                r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=allow_redirects)
            else:
                r = requests.post(url, headers=headers, data=data, timeout=timeout, allow_redirects=allow_redirects)
            return HttpResponse(r.status_code, r.text, str(r.url), dict(r.headers))

        cmd = [
            "curl",
            "-sS",
            "-X",
            method.upper(),
            "-b",
            str(self.jar_path),
            "-c",
            str(self.jar_path),
            "-w",
            "\n__CURL_META__%{http_code} %{url_effective}",
            "--max-time",
            str(timeout),
            "-A",
            headers.get("User-Agent", BROWSER_UA),
        ]
        if not allow_redirects:
            cmd.extend(["--max-redirs", "0"])
        for key, value in headers.items():
            if key.lower() == "user-agent":
                continue
            cmd.extend(["-H", f"{key}: {value}"])
        if data is not None:
            cmd.extend(["--data-raw", urlencode(data)])
            if "Content-Type" not in headers:
                cmd.extend(["-H", "Content-Type: application/x-www-form-urlencoded"])
        cmd.append(url)

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        raw = proc.stdout
        if "__CURL_META__" not in raw:
            raise RuntimeError(f"curl failed: {proc.stderr.strip() or proc.stdout[:200]}")
        body, meta = raw.rsplit("\n__CURL_META__", 1)
        code_str, effective = meta.strip().split(" ", 1)
        return HttpResponse(int(code_str), body, effective, {})


_default_session: CurlSession | None = None


def get_session() -> CurlSession:
    global _default_session
    if _default_session is None:
        _default_session = CurlSession()
    return _default_session


def request(
    method: str,
    url: str,
    *,
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    allow_redirects: bool = True,
    timeout: int = 30,
    session: CurlSession | None = None,
) -> HttpResponse:
    return (session or get_session()).request(
        method,
        url,
        data=data,
        headers=headers,
        allow_redirects=allow_redirects,
        timeout=timeout,
    )
