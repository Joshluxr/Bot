# Merge notes

This build merges two prior SearchK4 patch sets into a single maintained tree. Both had strengths, both had gaps. Neither has been compiled in this environment (nvcc not available), but each has been statically verified where possible.

## Provenance

**Base:** `SearchK4_fixed_20260419.zip` (ChatGPT's correctness-heavy patch set).

**Ported in:** features from `SearchK4_patched_20260420.zip` (direct mode, range clamping) and the external RIPEMD-160 drop-in from `ripemd160.zip` (9/9 test vectors passing, verified against Puzzle #1 end-to-end).

## What came from ChatGPT's 20260419 patch set

- **Versioned state format with FNV-1a checksum.** `K4StateHeaderV2` struct (magic, version, threadCount, stepSize, totalKeys, iter, keysPerIter, baseKey, keyWords, checksum). Load-time validation of every field. Legacy v1 files still readable; upgraded on next save.
- **`peek_state_seq_header`** — if `-threads` is omitted and a v2 state file is supplied, the thread count is restored from the state header.
- **`iter` round-trips across resume.** The main loop initialiser reads `loadedState.iter` instead of hard-coding 0.
- **Zero-tolerant `batch_mod_inv`.** Indexes non-zero entries, inverts only those, leaves zero outputs in place. The caller (`init_keys_from_start`) tracks `special_case[]` and falls back to full `scalar_mult_G` for those threads.
- **Kernel zero-mask for `_ModInvGrouped`.** New device helpers `IsZero256Dev`, `SetOne256Dev`, `ModAdd256Dev`, `PointAddAffineDev`. Zero denominators get replaced with 1 before the grouped inversion, and the special entries are routed to affine point-addition in the second pass.
- **`reconstruct_privkey` using mod-N arithmetic.** `add_mod_n_scalar`, `mul_u64_u64_mod_n`, `sub_mod_n` throughout. Returns `bool` and rejects invalid outputs. Correct for iter counts that would overflow 64-bit integer products.
- **Strict input parsing.** `parse_start_key` centralizes decimal / hex parsing and range validation. Malformed input rejected; `_` and `,` separators allowed.
- **Pattern length validation.** `K4_PATTERN_MAX_LEN = 35`. Lines longer than the limit are rejected, not truncated.
- **Per-GPU output defaults.** `found_k4_gpu<id>.txt` and `gpu<id>.state` so multi-GPU runs don't collide.
- **Thread count validation.** `≥ 64` and a multiple of 64 — the kernel's block structure requires it.
- **Host-side post-match verification.** `derive_address_from_privkey` → `pubkey_to_hash160_host` → `sha256_host` + `ripemd160`. Verified vs. unverified matches logged distinctly.

## What came from the 20260420 patched baseline

- **`-direct` mode.** `d_target_h160`, `d_num_targets`, `d_direct_mode` device constants. `_MatchHash160` device function. `CheckHashCompSymK4` now has an early `if (d_direct_mode) { 2 hashes + 2 raw compares; return; }` branch. Skips Base58 long-division and skips uncompressed-address checks in the hot path.
- **`address_to_hash160_host`.** Host-side Base58Check decoder with version byte + checksum verification. Used to decode full P2PKH addresses into hash160 targets for the `d_target_h160` upload.
- **Range clamping via `-endx` and `-bits N`.** `d_endKey`, `d_have_endx` device constants. `-bits N` expands to `-startx 2^(N-1) -endx 2^N-1`. Host-side termination check between iterations — branch-free kernel, clean exit on range exhaustion.
- **Mode-aware default thread count.** 16384 in `-direct` mode (lighter register state), 1024 in prefix mode.
- **`-verbose` flag** for per-iteration progress.
- **Puzzle #71–#74 `patterns.txt`.** Restored with full addresses and range documentation.

## What came from the external RIPEMD-160 drop-in

- **`ripemd160.c` / `ripemd160.h`.** Standalone C99 RIPEMD-160. Compiles clean with `-Wall -Wextra -std=c99`. Replaces ChatGPT's inline `ripemd160_host` + `ripemd160_transform_host`.

Why swap it in:
  - Verified against all 9 published test vectors, including the 1-million-"a" stress vector (ChatGPT's inline version was only testable up to ~119 bytes because of its fixed `uint8_t padded[128]` buffer — correct for its actual caller but a latent trap).
  - Puzzle #1 end-to-end: `RIPEMD160(SHA256(02||G.x))` → `751e76e8199196d454941c45d1b3a323f1433bd6`, which matches the Base58-decoded hash160 of `1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH`.
  - Cleaner separation of the general-purpose hash primitive from application code.

## What was considered and deliberately NOT changed

- **Kernel seqDelta-zero guard.** ChatGPT added defensive code here. I analyzed that for the configured puzzle ranges (`baseKey ≥ 2^70`), the collision condition `baseKey ≡ ±(nbThread-2-tid)*STEP_SIZE − iter*nbThread*STEP_SIZE (mod N)` is mathematically impossible. But ChatGPT's implementation is correct and the cost on the normal path is one register load plus a never-taken branch — cheap insurance. Left in.
- **Dead affine `point_add` / `point_double` host functions.** Superseded by the Jacobian versions but still present. Not called. Not removed to avoid churn.
- **`mod_mul` triple-reduction on host.** Correct but over-eager; one of the three reduction branches is unreachable for any actual secp256k1 input. Untouched.
- **ChatGPT's `SearchK4.cu` → "legacy/reference" reclassification.** Kept. The maintained path is `SearchK4_fast.cu`.

## Static verification that was performed

- **Brace / paren / bracket balance.** 326/326, 1427/1427, 654/654.
- **Symbol reference check.** Every new or ported name (`_MatchHash160`, `d_target_h160`, `d_num_targets`, `d_direct_mode`, `d_endKey`, `d_have_endx`, `address_to_hash160_host`, `ripemd160`, `K4StateHeaderV2`) has both a definition and at least one use.
- **Signature check on refactored functions.** All `hex_to_256bit` call sites pass the strict 4-argument form. All `save_state_seq` / `load_state_seq` call sites match their new signatures. Removed inline symbols (`ripemd160_host`, `ripemd160_transform_host`, `rol32_host`) have zero remaining references.
- **Pure-C compile of `ripemd160.c`.** Compiles cleanly with `cc -O3 -Wall -Wextra -std=c99`. nvcc `-x c` should handle it identically; fallback to `gcc -c` documented in the README.

## What needs a real CUDA host to validate

- **`nvcc` build.** Most likely friction points: (1) the `configure_sequential_delta` and `peek_state_seq_header` symbols are now called from both fresh-start and resume paths — confirm the forward declarations are in scope; (2) `nvcc -x c ripemd160.c` — if nvcc's host toolchain rejects it, fall back to `gcc -c`.
- **`make smoke`.** Should complete Puzzle #1 in under a second and produce `verified=yes` in the output file. Any `UNVERIFIED` line means the verifier caught a mismatch — investigate before trusting further output.
- **Resume correctness.** Kill a run after several hundred iterations, resume, and confirm: the rate counter picks up from the saved point, iter increments continue monotonically, and any match is reconstructed with the correct private key.
- **Direct vs prefix mode parity.** A run with `-direct` on the Puzzle #1 pattern should produce the same reconstructed private key as a prefix-mode run on the same pattern. Timing should differ (direct mode ~30-40% faster on the hot path).

## File list

| File | Status |
|---|---|
| `SearchK4_fast.cu` | **Modified.** Base = ChatGPT's. Direct mode, range clamping, external ripemd160 ported in. ~2430 lines. |
| `Makefile` | **Modified.** Compiles/links `ripemd160.o`, bumped default arch to sm_120, `-maxrregcount 96`, new `smoke` target. |
| `ripemd160.c`, `ripemd160.h` | **New.** External drop-in, verified. |
| `patterns.txt` | **Replaced** with the Puzzle #71–#74 set. |
| `README.md` | **Rewritten** to document the merged feature set. |
| `MERGE_NOTES.md` | **New.** This file. |
| `PATCH_NOTES_2026-04-19.md` | Kept (ChatGPT's notes on their patch round). |
| `SearchK4.cu` | Unchanged. Legacy/reference. |
| `GPUGroup.h`, `GPUMath.h`, `GPUHash.h`, `CPUGroup.h` | Unchanged. VanitySearch primitives. |
| `LICENSE`, `TESTING.md`, `DEBUGGING_HISTORY.md`, `UNCOMPRESSED_ADDRESS_FIX.md` | Kept. |
| `test_*.cu` | Kept as historical probes. Not built by the default target. |
