# SearchK4 patch notes

Date: 2026-04-19

This repository snapshot contains the maintained patch set applied to **`SearchK4_fast.cu`** and supporting project files.

## Scope

The fast path in `SearchK4_fast.cu` is the maintained implementation. `SearchK4.cu` is now explicitly marked as a legacy/reference file so the repo no longer implies that both top-level CUDA files are equally current.

## Files changed

- `SearchK4_fast.cu`
- `Makefile`
- `README.md`
- `SearchK4.cu`
- `LICENSE`
- `TESTING.md`

## File-by-file changes

### `SearchK4_fast.cu`

- added strict decimal/hex parsing and private-key range checks
- added versioned state header, checksum, and resume metadata validation
- restored iteration-aware resume handling
- restored sequential-delta configuration on both fresh start and resume
- made host batch inversion zero-tolerant
- added special-case host initialization fallback via exact scalar multiplication
- made GPU grouped inversion zero-tolerant via masking plus affine special-case handling
- hardened private-key reconstruction
- added host-side RIPEMD-160, address derivation, and final match verification
- validated and documented thread-count constraints
- removed hot-loop debug spam and unused random/debug remnants
- changed default output behavior to per-GPU output names

### `Makefile`

- made `searchk4_fast` the default build target
- labeled `searchk4` as legacy/reference
- added a clearer `help` target
- added a maintained smoke-test target based on the patched fast path

### `README.md`

- rewrote the project description around the maintained fast path
- documented current command-line options and defaults
- documented pattern-length limits and the v2 state format
- documented the maintained smoke-test entry point

### `TESTING.md`

- added a single maintained validation path for the repo
- documented fresh, resume, and edge-case testing expectations

### `SearchK4.cu`

- marked as legacy/reference so the repo no longer implies it is the primary maintained entry point

### `LICENSE`

- added a top-level GPLv3 license file

## Summary of fixes

### 1. Resume/state correctness

**Problem:** The previous fast path saved point buffers and `totalKeys`, but resume did not fully restore the sequential-search state. The code restarted `iter` from zero, did not restore the effective per-iteration stride metadata, and did not verify state-file integrity. That could reconstruct the wrong private key after resume and could also cause overlapping coverage after a resumed run.

**Fix applied:**

- Replaced the old ad hoc sequential state format with a versioned **v2** header.
- Added `K4StateHeaderV2` with:
  - magic
  - version
  - thread count
  - step size
  - total keys covered
  - iteration count
  - keys-per-iteration
  - base key
  - serialized key buffer length
  - checksum
- Added `compute_state_checksum()` using FNV-1a over the header fields plus the saved key buffer.
- Added `peek_state_seq_header()` so the program can restore the thread count from a v2 state when `-threads` is omitted.
- Reworked `save_state_seq()` and `load_state_seq()` to save and restore:
  - `iter`
  - `totalKeys`
  - base key
  - thread count
  - keys-per-iteration
  - full key buffer
- Added validation on load for version, step size, thread count, stride, file size, checksum, and base-key range.
- Legacy state files are still accepted when their size and progress metadata are internally consistent. They are upgraded to the new format on the next save.
- Added `configure_sequential_delta()` and call it in both fresh-start and resume paths so the device constants are reloaded consistently.
- The main loop now initializes `total` and `iter` from loaded state metadata instead of restarting from zero.

**Why it fixes the issue:** The reconstruction formula now uses the correct iteration count after resume, and the GPU gets the correct sequential-delta constants again, so resumed searches continue from the saved position instead of silently reusing iteration-zero assumptions.

### 2. Strict start-key parsing and private-key validation

**Problem:** The old decimal parser stripped non-digits, the old hex parser skipped non-hex characters and silently truncated oversized input, and neither path strictly enforced the secp256k1 private-key range.

**Fix applied:**

- Replaced the old permissive parsing helpers with strict `decimal_to_256bit()` and `hex_to_256bit()` implementations.
- Added whitespace trimming.
- Added controlled allowance only for `_` and `,` separators.
- Rejects:
  - empty input
  - invalid characters
  - hex strings longer than 64 digits
  - values above 256 bits
  - private keys outside `[1, n - 1]`
- Added `parse_start_key()` which centralizes validation and error reporting.

**Why it fixes the issue:** The start key is now either accepted exactly as intended or rejected; malformed input can no longer silently map to a different key.

### 3. Pattern-length validation

**Problem:** Patterns were copied into a 36-byte slot but the recorded pattern length could exceed the stored string length, which allowed `_MatchPrefix()` to read past the stored pattern buffer.

**Fix applied:**

- Introduced `K4_PATTERN_MAX_LEN = 35`.
- `load_patterns()` now rejects overlong patterns instead of truncating them while preserving the original length.
- Pattern and pattern-length arrays are zero-initialized before being copied to constant memory.

**Why it fixes the issue:** Device-side prefix comparison now sees a bounded pattern string and a matching bounded pattern length.

### 4. Zero-denominator handling in host batch inversion

**Problem:** The host initializer used batch inversion on `dx = iGx - p0x` without handling zero denominators. A start aligned with one of the precomputed offsets could poison the batch and corrupt all inversions in that batch.

**Fix applied:**

- Reworked `batch_mod_inv()` to tolerate zero inputs. Zero inputs now produce zero outputs and are excluded from the Montgomery product chain.
- In `init_keys_from_start()`, the code records zero-denominator entries in a `special_case` mask.
- Those threads now fall back to exact scalar multiplication of the per-thread private key instead of using the affine-add shortcut.
- Added an explicit guard for thread-start key zero in the fallback path.

**Why it fixes the issue:** A single zero denominator no longer poisons the whole batch, and the problematic points are handled by an exact path.

### 5. Zero-denominator handling in the GPU grouped inversion path

**Problem:** The kernel grouped-inversion path had the same structural assumption that all denominators were nonzero. Certain start ranges or aligned points could hit exact-point or opposite-point edge cases and break the grouped inversion math.

**Fix applied:**

- Added small device helpers:
  - `IsZero256Dev()`
  - `SetZero256Dev()`
  - `SetOne256Dev()`
  - `ModAdd256Dev()`
  - `PointAddAffineDev()`
- `ComputeKeysK4()` now masks zero denominators before `_ModInvGrouped()` by replacing zero entries with one and tracking which entries were special cases.
- Special cases are processed with `PointAddAffineDev()` instead of the normal grouped-inversion fast path.
- The same helper is also used when applying the sequential delta after each iteration.

**Why it fixes the issue:** The grouped inversion stays well-defined for the nonzero entries, and zero-denominator point additions are routed to an exact affine path that correctly handles add/double/infinity edge cases.

### 6. Thread-count validation and safer defaults

**Problem:** `-threads` previously accepted arbitrary integers even though the kernel layout assumes 64-thread groups. Non-multiples of 64 were silently truncated in the launch configuration and values below 64 could produce an invalid zero-grid launch.

**Fix applied:**

- `print_usage()` now documents `-threads`.
- The main program now enforces:
  - `threads >= 64`
  - `threads % 64 == 0`
- The default remains `1024`.
- If resuming from a v2 state and `-threads` is omitted, the saved thread count is restored automatically.

**Why it fixes the issue:** The launch geometry and the serialized state now stay aligned with the actual assumptions used by the kernel.

### 7. Host-side post-match verification

**Problem:** The original fast path trusted GPU match metadata plus host reconstruction without doing a final round-trip validation from the reconstructed private key back to the reported address/hash160.

**Fix applied:**

- Added host-side RIPEMD-160 implementation.
- Added `pubkey_to_hash160_host()` and `derive_address_from_privkey()`.
- Match handling now reconstructs the private key, derives the expected address/hash160 on the host, and compares both against the GPU-reported match metadata before writing output.
- Invalid or mismatched reconstructions are skipped and logged as warnings.
- Output now records the verified address explicitly.

**Why it fixes the issue:** Even if a bug appears in reconstruction or match metadata, it is caught before a false result is written as a found key.

### 8. Private-key reconstruction hardening

**Problem:** Reconstruction previously depended on the implicit assumption that `iter` started from zero and on a looser mix of signed offsets and parity handling.

**Fix applied:**

- Reworked `reconstruct_privkey()` to return `bool` and reject invalid/zero outputs.
- Computes the iteration offset modulo the group order using `mul_u64_u64_mod_n()`.
- Uses modular add/subtract helpers over `SECP_N`.
- Applies parity handling consistently for compressed and uncompressed cases.

**Why it fixes the issue:** Reconstruction is now tied to the actual sequential progression of the search grid and rejects invalid edge results instead of silently emitting them.

### 9. Logging cleanup

**Problem:** The hot loop printed multiple debug messages per iteration, which was both noisy and harmful for throughput.

**Fix applied:**

- Removed the per-iteration debug print spam from the main search loop.
- Removed the device debug globals that were only used for tracing.
- Kept coarse progress reporting and explicit warnings/errors.

**Why it fixes the issue:** The runtime behavior is now closer to the intended benchmark path while still preserving useful operator-visible diagnostics.

### 10. Output-file isolation and repo/docs cleanup

**Problem:** The old default output file `found_k4.txt` encouraged accidental cross-process append collisions in multi-GPU runs. Documentation also lagged behind the maintained implementation.

**Fix applied:**

- Default output file is now `found_k4_gpu<id>.txt`.
- Default state file is now `gpu<id>.state` when not explicitly supplied.
- README was rewritten to describe the actual maintained path, current options, state format, and constraints.
- Makefile was rewritten to make `searchk4_fast` the default build target and to label `searchk4` as legacy/reference.
- Added a top-level `LICENSE` file using GPLv3 text.

**Why it fixes the issue:** Operators now get safer defaults and the repository communicates the real supported entry point more clearly.

### 11. Legacy/stale code cleanup

**Problem:** The repository still carried stale signals from earlier random-mode and debug-era development, which made it harder to see which code path was current.

**Fix applied:**

- Marked `SearchK4.cu` as legacy/reference directly in the source file header.
- Removed unused random/debug remnants from `SearchK4_fast.cu` where they were no longer part of the maintained path.
- Made `searchk4_fast` the default build target and labeled `searchk4` as legacy/reference in the Makefile.

**Why it fixes the issue:** The repo now points operators toward the maintained code path and reduces confusion caused by leftover experimental scaffolding.

## Compatibility notes

- **Fresh runs:** use `SearchK4_fast.cu` / `searchk4_fast`.
- **v2 state files:** can restore thread count automatically when `-threads` is omitted.
- **Legacy state files:** still load when they match the current thread count and expected file size. They do not contain thread-count metadata, so an operator may still need to pass the original `-threads` value if the file predates the v2 format.
- **Patterns:** prefixes longer than 35 characters are now rejected instead of truncated.

## Validation performed in this patching environment

The environment used to patch this repository did **not** provide a working CUDA toolkit or a GPU runtime for building and executing the kernels. The validation completed here was therefore static rather than live-runtime:

- structural review of the maintained implementation
- patch consistency review across the fresh-start, resume, and output paths
- sanity checks on symbol references and control flow after patching
- documentation and build-target cleanup so the maintained entry point matches the code

## Validation still recommended on a CUDA host

Run these checks on a machine with `nvcc` and a supported GPU before relying on the patched code for long unattended runs:

1. Build `searchk4_fast` with the local CUDA toolkit.
2. Run a short fresh-start search with a tiny prefix set.
3. Save/resume after several iterations and confirm:
   - `iter` resumes correctly
   - coverage counters continue monotonically
   - reconstructed addresses still verify
4. Test edge starts such as `0x1`, `0x400`, and values aligned to multiples of `1024`.
5. Test invalid inputs and confirm they are rejected cleanly.

## Recommended command after extraction

```bash
make searchk4_fast
./searchk4_fast -patterns patterns.txt -startx 0x1 -threads 1024 -gpu 0
```
