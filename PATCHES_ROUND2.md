# SearchK4 Patch Log — Round 2

Patches applied on top of the 20260420 baseline. Five concrete fixes; no
math touched. The `.cu` file goes from 1893 to ~2170 lines. `ripemd160.c`
and `ripemd160.h` are added as a new dependency, linked in via an updated
Makefile.

---

## 1. Correctness: `iter` now round-trips across resume (state format v3)

### Problem

The previous round of patches fixed the `d_seqDelta` upload on resume and
added `nbThread` to the state file (v2). One thing it did not fix: the
main-loop initialiser hard-coded `iter = 0` even on resume.

`reconstruct_privkey` uses `iter` to compute the per-thread iteration
offset: `basePrivkey = baseKey + tid*STEP_SIZE + iter*nbThread*STEP_SIZE
+ keyOffset`. On a fresh start, `iter = 0` is correct. On resume after
100,000 iterations had already run, the next kernel launch might report a
match — and `reconstruct_privkey` would compute the key missing the
`100_000 * nbThread * STEP_SIZE` term. The output file would record a hex
private key that didn't correspond to the address printed next to it.

This is the single worst failure mode for a puzzle solver: a "win" on
paper that doesn't redeem. The existing hash160 comparison on the GPU
side would still pass (the hash160 belongs to a real key in the search
space), so the UI shows success — the only signal is that the hex key,
when imported into a wallet, produces a different address.

### Fix

New v3 state format. Layout: `magic "SK4STv03"` | `total` (8B) | `iter`
(8B) | `baseKey` (32B) | `nbThread` (4B) | `pad` (4B) | `keys data`.
v2 and v1 still load (with warnings); v2 behaves as before (iter lost, 1
iteration of potentially-wrong output after resume) and prints a one-line
warning at load time.

Main loop now initialises `uint64_t iter = g_resumedIter;` — where
`g_resumedIter` is set in the resume branch from the v3 `out_iter`
field. Both save sites (every-500-iter periodic save and final SIGTERM
save) pass `iter` through.

### Why this is a real bug, not a theoretical one

The current build saves state every 500 iterations and on SIGINT/SIGTERM.
The time between saves at ~100 iter/s is ~5 seconds. Any resumed run has
at least some post-resume iterations before the next save, and any match
within that window was subject to this bug. The only reason it wasn't
caught is that for the configured puzzle ranges (2^70..2^73), nobody has
actually found a match yet — so the wrong-key output has never been
exercised in practice. But the code path runs every iteration after
every resume.

---

## 2. Correctness: host-side post-match verification

### Problem

When the GPU reports a match, the host did: reconstruct privkey, format
as hex+WIF, write to `found_k4.txt`. Zero cross-check. If
`reconstruct_privkey` has any offset bug (see #1) or the GPU scratches
memory, the output is accepted as-is.

### Fix

New `verify_match(privkey, reported_h160, parity)` that re-derives
`hash160 = RIPEMD160(SHA256(0x02|0x03 || px))` from scratch on the host
using the reconstructed key, and compares to what the GPU reported.

- Verified matches log normally.
- Unverified matches log with `UNVERIFIED Pattern=...
  -- RECONSTRUCTION MISMATCH, DO NOT IMPORT WITHOUT INVESTIGATION`, and
  stdout prints `[!] UNVERIFIED match for <addr>` instead of the usual
  success banner.

Host-side pipeline (added):

- `scalar_mult_G` — reused from existing CPU EC code (Jacobian).
- `sha256_host` — already present.
- `ripemd160` — new, from the vetted standalone package. 9/9 published
  test vectors pass, including 1M-"a" stress test. End-to-end verified
  against Puzzle #1: `RIPEMD160(SHA256(02||G.x))` →
  `751e76e8199196d454941c45d1b3a323f1433bd6`, which is the hash160 of
  `1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH` exactly.

Uncompressed-parity matches (parity 2/3, legacy prefix mode) skip
verification and return true. The main use case (`-direct` mode) only
produces parity 0/1, both of which are verified.

### Why this matters independently of fix #1

Even with `iter` correctly restored, `reconstruct_privkey` has non-
trivial logic for compressed parity reconciliation (odd vs even Y, mod-N
negation). A bug there would silently produce wrong keys. The verifier
is cheap (one scalar_mult_G + one SHA + one RIPEMD per match, which is
microseconds; matches are rare) and catches the entire class of
reconstruction errors in one shot.

---

## 3. Input validation

### Problem

Previous parsing was silently permissive:

- `hex_to_256bit` `continue`d on non-hex characters. `-startx 0xdeadZbeef`
  parsed as `0xdeadbeef`.
- `decimal_to_256bit` stripped non-digits. `-start 123abc456` parsed as
  `123456`.
- No overflow check. A 200-hex-digit string wrote garbage into the
  first 32 bytes and got accepted.
- `-threads` accepted `65`, `100`, `1`, or any other value that's not a
  multiple of `NB_THREAD_PER_GROUP = 64`. Kernel launch then uses
  `nbThread / 64` blocks (integer division truncates), so `-threads 65`
  launches 1 block * 64 threads, with key storage allocated for 65. The
  65th thread's starting point exists in memory but is never read.
  Silent coverage bug.
- `-gpu -1`, `-bits -5`, `-bits 500` all parsed and propagated.
- `load_patterns` truncated pattern lines longer than 35 chars with
  `strncpy`, silently dropping the trailing bytes. For address prefix
  matching this could change what addresses match.
- No check that the (parsed or resumed) `g_baseKey` was in the legal
  range `(0, N)`. `baseKey = 0` produces a point-at-infinity start that
  breaks `scalar_mult_G` immediately.

### Fix

- `hex_to_256bit_strict` and `decimal_to_256bit_strict` added alongside
  the legacy lax parsers. Strict versions return `bool`, reject any
  non-valid char, reject empty input, reject overflow. Legacy parsers
  kept only for the internal `-bits` shortcut path that builds a
  guaranteed-valid string.
- CLI-level validation block runs right after argv parsing:
  - `-gpu >= 0`
  - `-threads == 0` OR (`-threads >= 64` AND `-threads % 64 == 0`)
  - `-bits` in `[0, 256]`
  - `-startx`, `-start`, `-endx` parse strictly
- Post-init validation block runs right before the main loop:
  - `g_baseKey != 0`
  - `g_baseKey < N`
  - if `-endx` set: `endKey < N` AND `endKey >= g_baseKey`
- `load_patterns` rejects lines longer than 35 chars explicitly; doesn't
  silently truncate.

---

## 4. Defense-in-depth: `batch_mod_inv` zero-input guard

### Problem

`batch_mod_inv` builds a product chain of inputs, inverts the final
product, then walks back. If any input is zero, the final product is
zero, `mod_inv` on zero produces a bogus "inverse of zero", and every
output in the array is wrong — with no signal to the caller.

For the configured puzzle ranges this is literally unreachable. A zero
input would require `baseKey ≡ ±(t * STEP_SIZE) (mod N)` for some
`t ∈ [1, nbThread)`. With `baseKey >= 2^70` and
`t*STEP_SIZE <= 2^24`, the congruence can't hold.

But the function has no awareness of that constraint. A future maintainer
who repurposes the tool for a smaller key range, or a user who picks a
contrived `-startx`, would get silent corruption.

### Fix

Pre-scan the inputs. If any is zero, `exit(1)` with
`FATAL: batch_mod_inv got zero at index ... — start key collides with
i*G for some i in thread spacing. Choose a different start key.`

Cost: one N-element scan (negligible vs the N multiplications of the
main chain).

The analogous case in the kernel's end-of-iter seqDelta add is also
mathematically unreachable for the configured ranges (the scalar
congruence condition there is even tighter), and adding a guard inside
device code would mean surfacing the error through the found-buffer or
aborting the kernel. Left alone — the host-side `batch_mod_inv` guard is
where the contrived bad input would hit first anyway.

---

## 5. Build system

- Makefile compiles `ripemd160.c` as a separate object (`nvcc -x c`
  because nvcc's host compiler handles pure C fine) and links it into
  `searchk4_fast`.
- `clean` target includes `ripemd160.o`.
- `smoke` target now also greps the output file for `verified=` lines
  so you can see the host-side verifier firing on the Puzzle #1 match.
  A `UNVERIFIED` line anywhere in that output means something is wrong.
- New files in the tree: `ripemd160.c`, `ripemd160.h`.

---

## What was considered and intentionally not done

- **In-kernel seqDelta zero guard.** Argued unnecessary above. Adding
  one would require a device-side error path (found-buffer flag or
  `__trap()`), and for the configured puzzle ranges it's mathematically
  impossible to trigger.
- **`secure_random` still unused, still doesn't check `fread` return.**
  Flagged in the previous review. Not fixed because the function is
  dead code.
- **Dead affine `point_add` / `point_double` functions.** Superseded by
  the Jacobian versions, still compile, not called. Not removed to
  avoid gratuitous churn.
- **`mod_mul` triple reduction.** Correct but over-eager; one of the
  three reduction branches is unreachable for any actual secp256k1
  input. Not touched — "if it ain't broke..."

---

## Files changed

| File                | Change                                           |
|---------------------|--------------------------------------------------|
| `SearchK4_fast.cu`  | All five fixes above. ~280 lines added.          |
| `Makefile`          | Link `ripemd160.o`; `smoke` shows verify output. |
| `ripemd160.c`       | **NEW.** Standalone C99, 9/9 test vectors pass.  |
| `ripemd160.h`       | **NEW.** Public header, one function.            |

Unchanged: `GPUGroup.h`, `GPUMath.h`, `GPUHash.h`, `CPUGroup.h`,
`SearchK4.cu`, `patterns.txt`, `README.md`, `CHANGES.md` (this file is
additive; the previous CHANGES.md describes the prior patch session).

---

## Verification

I did not have nvcc available to compile. The file passes:

- Brace/paren/bracket balance (266/266, 1134/1134, 608/608).
- Symbol reference check: every new name has both a definition and at
  least one use.
- Signature check: both `save_state_seq` call sites pass the new 6-arg
  form; the single `load_state_seq` call site passes the new 6-arg form.

Compile errors, if any, are most likely in:

1. The auto-typed lambdas in the CLI validator (requires `-std=c++14`,
   which the Makefile already specifies).
2. The `-x c` handling of `ripemd160.c` by nvcc's host toolchain. If
   your environment refuses, compile `ripemd160.c` with `gcc -c` and
   pass the `.o` directly — the linkage is plain C.

Run `make smoke` after building. The expected output in `found_k4.txt`:

```
[<date>] Pattern='1BgGZ9tcN4rm9KBzDn7KprQz87SZ26SAMH' Address=1BgGZ... (compressed)
  PrivKey (HEX): 0x0000...0001
  PrivKey (WIF): KwDiBf89QgGbjEhKnhXJuH...
  Hash160: 751e76e8199196d454941c45d1b3a323f1433bd6
  tid=0 incr=512 parity=0 iter=0 verified=yes
```

`verified=yes` is the new signal. If it says `verified=NO` or the line
starts with `UNVERIFIED`, something is wrong — do not import the key.
