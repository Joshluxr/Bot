# SearchK4 — GPU Sequential Key Search (merged build)

GPU-accelerated secp256k1 key-range scanner with Jacobian coordinates, Montgomery batch inversion, a precomputed generator table, and host-side match verification. Built around VanitySearch's GPU primitives.

Configured for Bitcoin Puzzle Transaction addresses **#71–#74** (see `patterns.txt`).

This build merges the 2026-04-20 patch set's direct-mode / range-clamping features with a subsequent correctness-heavy patch set's checksummed state format, zero-tolerant math, and mod-N reconstruction. See `MERGE_NOTES.md` for provenance.

## Quick start

```bash
make                                              # builds ./searchk4_fast
make smoke                                        # Puzzle #1 end-to-end test
./searchk4_fast -patterns patterns.txt \
    -direct -bits 71 -gpu 0                       # search Puzzle #71
```

## What it does

Given a starting private key `k_start`, an end key `k_end`, and a set of target addresses, the tool iterates over the key range, derives the Bitcoin address (P2PKH) for each candidate key, and reports matches. Keys are scanned in blocks of `nbThread × STEP_SIZE` per GPU iteration using VanitySearch's group-symmetry trick: 1024 keys per thread per inner loop with a single modular inversion per block.

Every reported match is re-derived from scratch on the host (scalar_mult_G → SHA-256 → RIPEMD-160 → Base58) and compared to the GPU's output before it's written. Verified matches log `verified=yes`. Mismatches log `UNVERIFIED RECONSTRUCTION MISMATCH` and should not be imported without investigation.

## Modes

### `-direct` (recommended)

Hash160-direct mode. The host Base58-decodes each address in `patterns.txt`, uploads 20-byte hash160s to GPU constant memory, and the kernel compares the computed hash160 against the target list directly. No Base58 in the hot path. Also skips the uncompressed-address check — puzzle addresses are compressed-derived.

Requires full 34-character addresses in `patterns.txt` — not prefixes. Lines that don't decode as valid mainnet P2PKH addresses are rejected.

Default threads: **16384**.

### Legacy prefix mode (default)

Generates a Base58 address string on the GPU for every candidate and does a character-by-character prefix match. Also checks two uncompressed variants (Y and -Y). Kept for vanity-address workflows.

Default threads: **1024** (register pressure from the wider hash state keeps occupancy sane).

## Command-line options

| Flag | Description |
|---|---|
| `-patterns <file>` | Required. Address list (full addresses in direct mode, prefixes otherwise). |
| `-direct` | Enable hash160-direct mode. |
| `-start <dec>` | Starting private key, decimal. |
| `-startx <hex>` | Starting private key, hex (`0x` prefix optional). |
| `-endx <hex>` | End key (inclusive). Scan terminates when exhausted. |
| `-bits <N>` | Shortcut: set range to `[2^(N-1), 2^N - 1]`. Overridden by explicit `-startx`/`-endx`. |
| `-state <file>` | Resume from state file. See "Resume behaviour" below. |
| `-threads <N>` | CUDA thread count. Must be ≥ 64 and a multiple of 64. Default: 16384 (direct), 1024 (prefix). |
| `-gpu <id>` | GPU device ID. |
| `-o <file>` | Output file for matches. Default: `found_k4_gpu<id>.txt`. |
| `-verbose` | Print per-iteration progress. |
| `-h, --help` | Full usage with examples. |

## Multi-GPU

Run one instance per GPU, dividing the range manually. For Puzzle #71 split four ways:

```bash
./searchk4_fast -patterns patterns.txt -direct -gpu 0 \
    -startx 0x400000000000000000 -endx 0x4FFFFFFFFFFFFFFFFF
./searchk4_fast -patterns patterns.txt -direct -gpu 1 \
    -startx 0x500000000000000000 -endx 0x5FFFFFFFFFFFFFFFFF
./searchk4_fast -patterns patterns.txt -direct -gpu 2 \
    -startx 0x600000000000000000 -endx 0x6FFFFFFFFFFFFFFFFF
./searchk4_fast -patterns patterns.txt -direct -gpu 3 \
    -startx 0x700000000000000000 -endx 0x7FFFFFFFFFFFFFFFFF
```

Default state files are `gpu<id>.state` and output is `found_k4_gpu<id>.txt`, so the four processes don't collide.

## Resume behaviour

State files are written every 500 iterations and on clean exit (SIGINT/SIGTERM). The format is a versioned v2 struct:

- 8-byte magic `K4SEQV2\0`
- version, thread count, step size
- total keys covered, **iteration count** (critical for post-resume key reconstruction)
- keys-per-iteration, base key
- key buffer length
- FNV-1a checksum over header + key buffer

Consistency checks on load: version, step size, thread count, stride math, file size, checksum, and `baseKey ∈ [1, N−1]`. A mismatch in any field aborts the resume with a specific error rather than silently continuing with corrupt state.

If `-threads` is omitted and a v2 state file is supplied, the thread count is restored from the state header automatically.

Legacy (pre-v2) state files with the original 40-byte header are still readable; on next save they're upgraded to v2.

## Correctness guarantees

1. **`iter` round-trips across resume.** Without this, any match in the first iteration after a resume would reconstruct with the wrong private key (off by `saved_iter × nbThread × STEP_SIZE`).
2. **State-file checksum.** Catches disk corruption, partial writes, and accidental truncation.
3. **Host-side post-match verification.** `scalar_mult_G → SHA-256 → RIPEMD-160 → Base58` is re-run for every reported match and compared to the GPU's output. Mismatches log as `UNVERIFIED`.
4. **Zero-tolerant host batch inversion.** If `init_keys_from_start` finds a thread offset that collides with the base key (astronomically unlikely for the configured puzzle ranges, but possible for contrived inputs), that thread falls back to a full `scalar_mult_G` instead of corrupting the whole batch.
5. **Zero-masked kernel grouped inversion.** Same guarantee inside `ComputeKeysK4`: zero denominators are routed to an affine special-case path instead of poisoning the grouped inverse.
6. **`reconstruct_privkey` uses mod-N arithmetic throughout.** Correct for all valid iter counts, not just ones that fit in 64-bit products.
7. **Strict input parsing.** Decimal and hex parsers reject malformed input rather than silently skipping characters. Start key must be in `[1, N−1]`. Thread count must be `≥ 64` and a multiple of 64.

## Building

Auto-detects compute capability via `nvidia-smi`. Falls back to `sm_120` (Blackwell / RTX 5090). Override:

```bash
make CCAP=89     # Ada (RTX 4090)
make CCAP=86     # Ampere (RTX 3090)
make CCAP=75     # Turing (RTX 2080)
make CCAP=120    # Blackwell (RTX 5090)
```

Requires CUDA 12+ for Blackwell, CUDA 11.8+ for Ada/Ampere/Turing.

The build links a small C translation unit (`ripemd160.c`) alongside the CUDA source. nvcc handles it via its embedded host compiler (`-x c`). If that ever fails in your environment, build `ripemd160.o` with `gcc -c ripemd160.c` and pass the `.o` to the link step — the ABI is plain C.

## Smoke tests

- `make smoke` runs Puzzle #1 (private key = 1, address `1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH`) end-to-end. Should complete in a fraction of a second. Output must contain `verified=yes` and no `UNVERIFIED` lines.
- `make test` runs a short prefix-mode search against a small prefix set (no guaranteed match — this just confirms the binary launches and the kernel runs).

## Safety / restraint

1. `-direct` mode requires full P2PKH addresses. Prefixes are rejected. The kernel only fires on an exact 20-byte hash160 match.
2. Range clamping is available and documented. `-endx` or `-bits N` constrain the scan.
3. `patterns.txt` ships with exactly four addresses, all Bitcoin Puzzle Transaction targets with public ranges and designated solver rewards. No dormant third-party addresses.

## Credits

- [VanitySearch](https://github.com/JeanLucPons/VanitySearch) — GPU primitives, memory layout, `_ModInvGrouped`, Base58 kernel, hash pipeline.
- [hyperelliptic.org](https://hyperelliptic.org/EFD/g1p/auto-shortw-jacobian-0.html) — Jacobian coordinate formulas.
- Montgomery batch inversion (standard cryptographic literature).
- Dobbertin/Bosselaers/Preneel — RIPEMD-160 specification.

## License

GPL v3.0 (inherits from VanitySearch).
