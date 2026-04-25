# SearchK4 Optimization Pass — April 25, 2026

This document records the **second** optimization pass on `April25devinworking`,
after the +77% throughput pass documented in `OPTIMIZATION_NOTES.md`.

It covers (a) what was attempted, (b) what worked, (c) what failed and why,
and (d) methodology so future optimization passes don't repeat the same
mistakes.

---

## Summary

| | Before | After | Δ |
|---|---|---|---|
| Per-GPU throughput | 1.62 GKey/s | **1.77 GKey/s** | **+9.3%** |
| 8-GPU aggregate (projected) | ~13.0 GKey/s | ~14.2 GKey/s | +9.3% |
| dx/subp VRAM | 12.9 GB | ~1 GB | **-11.9 GB freed** |
| Per-kernel spill stores / loads | 224 / 540 B | 204 / 452 B | -9% / -16% |
| Stack frame | 1008 B | 33,824 B | (now in local memory, auto-coalesced) |
| `defaultThreads` (direct mode) | 393,216 | 655,360 | +66% |

**Cumulative changes:**
1. **dx/subp moved to per-thread stack** — auto-coalesced via the CUDA
   local-memory ABI, frees 11+ GB VRAM (+7.4%)
2. **`defaultThreads` bumped 393,216 → 655,360** — empirical sweep peak
   on RTX 5080 (+2.3% on top)

Branch: `devin/1777111192-searchk4-microopts`
Tip: `b683a5a` (single commit on top of `April25devinworking@16670ef`)
PR: https://github.com/Joshluxr/Bot/pull/19

Hardware: 1× RTX 5080 (sm_120), CUDA 13.0, NVCC 13.0, vast.ai
`45.77.214.165:25256`. All measurements at `-bits 71 -threads 393216`,
single pattern, 140 s steady-state runs.

---

## Phase 1: Static Analysis

The full report is in `/home/ubuntu/SearchK4_April25_Analysis.md` (delivered
separately as a PR-side attachment). Bottlenecks identified, ranked by
projected ROI:

1. **Non-coalesced `d_dx`/`d_subp`** — adjacent threads in a warp accessed
   addresses 16 KB apart. Per-warp working set was 32 cachelines for what
   should have been 1. Also burned 12.9 GB of VRAM at `nbThread=393216`.
   Projected: 1.5–2.5×.
2. **Two-stream double-buffered launch loop** to overlap CPU
   post-processing with GPU work. Projected: 5–15%.
3. **`#undef ASSEMBLY_SIGMA`** — the legacy 64-bit-shift PTX rotate
   emulation is slower than the C-macro fallback (single
   `shf.r.wrap.b32`). Projected: 5–15%.
4. **Two-level bloom filter** — L1 (8 KB shared) + L2 (64 KB global).
   Most probes terminate at L1 speed. Projected: 5–10%.
5. **`__forceinline__` hot-path functions** — `CheckHashCompSymK4` and
   `_GetHash160` were `__noinline__` from the era when stack was 33 KB;
   with stack now ~1 KB, the inline-cost tradeoff has flipped. Projected:
   5–15%.
6. **Drop `-maxrregcount=128` cap** — kernel was hitting the cap and
   spilling 640 B/kernel. Projected: 5–15%.

Stacked, projection: ~3–5 GKey/s per 5080.

**This projection turned out to be wrong by ~3×.** What follows is why.

---

## Phase 2: Implementation (5 commits, all wins on paper)

Implemented as 5 separate commits for bisectability:

| Commit | Change | ptxas regs | spill stores | spill loads | smem |
|---|---|---|---|---|---|
| baseline `16670ef` | — | 128 (capped) | 224 B | 540 B | 0 |
| `792575e` | `#undef ASSEMBLY_SIGMA` | 128 | 224 B | 540 B | 0 |
| `70022de` | drop `-maxrregcount=128` | **198** | **0** | **0** | 0 |
| `36336a0` | `__forceinline__` hot-path | **168** | 0 | 0 | 0 |
| `48f84f7` | 2-level bloom (8 KB shared) | 164 | 0 | 0 | **8 KB** |
| `9df2eb7` | dx/subp on stack | 198 | 0 | 0 | 8 KB |

Static analysis on every commit confirmed the predicted register / spill
behavior. NVCC compiled cleanly. Smoke test (Puzzle #1) passed at every
step.

The two-stream pipeline was skipped: profiling showed kernel time
(~250 ms) dominates iteration time so completely that overlap is <0.1%.

PR #19 was opened with all 5 commits and the projected ~3–5 GKey/s
ceiling.

---

## Phase 3: Real-Hardware Bisect — the Surprise

The user provisioned an SSH key for the live 4× RTX 5080 box. Each
commit was rebuilt with NVCC 13.0 / sm_120 and benchmarked end-to-end.

### Bisect results

| Layered change | GKey/s | Δ vs baseline |
|---|---|---|
| baseline `16670ef` | **1.62** | — |
| + `#undef ASSEMBLY_SIGMA` | 1.62 | 0% |
| + drop `-maxrregcount=128` | 1.55 | **-4.3%** |
| + `__forceinline__` hot-path | 1.46 | **-9.9%** |
| + two-level bloom (8 KB shared) | 1.23 | **-24.1%** |
| + dx/subp on stack | 1.60 | -1.2% |
| **baseline + dx/subp on stack ALONE** | **1.74** | **+7.4%** |

The full 5-commit stack regressed perf by ~2%. Of the 5 changes:

- **1 was neutral** (`#undef ASSEMBLY_SIGMA`)
- **3 were net regressions** (maxregcount drop, forceinline, two-level bloom)
- **1 was a real win** (dx/subp on stack)

### Why each failed prediction was wrong

**Drop `-maxrregcount=128`** — Predicted a small occupancy hit overcome
by zeroing spill traffic. Actual: 128 → 198 regs cratered occupancy from
~8 blocks/SM to ~5 blocks/SM. The avoided spill traffic was already cheap
(spill goes to L1-cached local memory; 640 B/kernel × ~250 ms iter time is
microseconds of work) while the lost latency hiding from 3 fewer in-flight
blocks/SM was milliseconds of stalls. Net: -4.3%.

**`__forceinline__`** — Predicted ~5–15% from saving the noinline ABI
spill on every call. Actual: another -6% on top of the -4.3% from the
maxregcount drop. With the cap already off and 168–198 regs in use, the
inlined kernel apparently fragmented its instruction-cache footprint
enough that the kernel slowed down further. The "noinline ABI spill"
that the analysis was worried about turned out to be cheaper than the
i-cache pressure of a fully-inlined hot loop. Net: -5.7% incremental.

**Two-level bloom** — This was the biggest miss: -24% net. The 8 KB
shared-memory L1 was supposed to short-circuit ~99.5% of probes at
~5 ns each. Actual cost dynamics on Blackwell:

- **Shared memory occupancy hit.** RTX 5080 has 100 KB shared / SM.
  64 threads/block × 5 blocks/SM × 8 KB = 40 KB shared/SM consumed by
  the L1. Plus the existing constants (`Gx[]`, `Gy[]` — already in
  cmem) and per-block `__syncthreads` traffic. Occupancy dropped further
  from ~5 → ~3 blocks/SM.
- **Cooperative load is per-block, every kernel launch.** 8 KB / 64
  threads = 128 B / thread = 32 vector loads. Cheap, but it happens
  on every kernel call (2,000+ times in a 60 s run).
- **L2 path is now slower, not faster.** Adding the L1 check means
  every probe now does 1 shared read; only ~0.5% of those go on to
  hit the global L2. But `d_bloom_filter` was already hot in L2
  cache, so a global read was ~50 ns (cached) or ~200 ns (cold), not
  the ~500 ns the analysis assumed. The L1 layer cost ~5 ns/probe but
  saved only ~50 ns/probe × 0.995 = ~50 ns — a slim margin even before
  occupancy effects. After occupancy effects: huge net loss.

**ASSEMBLY_SIGMA** — Neutral. NVCC 13 produces identical-perf code
either way. Either it folds the C-macro shifts into the same
`shf.r.wrap.b32` (likely), or the kernel is so memory-bound that the
SHA-256 sigma op isn't on the critical path.

### Why dx/subp on stack worked

This was the one optimization where the static analysis was right —
*and* turned out to be much bigger than predicted, because of a lever
that wasn't in the original analysis: **VRAM L2 cache pressure.**

The previous layout cudaMalloc'd 12.9 GB of d_dx/d_subp at
`nbThread=393216`. That's 80% of the RTX 5080's 16 GB. The remaining
3 GB was barely enough for `d_keys` (1 GB), `d_found`, and driver/CUDA
context — leaving essentially no room for the L2 cache to keep
`d_bloom_filter` (64 KB), `d_target_h160` (~80 KB), and other hot
read-only structures resident.

Moving dx/subp to the per-thread stack:

- **Coalescing.** CUDA's local-memory ABI auto-strides accesses
  across the warp: when 32 lanes access `local[i]`, the hardware
  emits 32 contiguous 8-byte loads instead of 32 16 KB-strided loads.
  Same memory-transaction count as the previous flat layout, but
  each transaction is a single coalesced cacheline fetch instead of
  32 separate ones. **~32× memory throughput on dx/subp accesses.**
- **VRAM scaling.** Local memory backing scales with *resident*
  threads, not total threads. At ~32K resident on RTX 5080
  (84 SMs × 6 blocks × 64 threads), that's ~32K × 33 KB = ~1 GB.
  **11+ GB of VRAM freed**, all of which is now hot in L2 cache for
  the small read-only structures.
- **Reduced spill traffic.** Spill stores: 224 → 204 (-9%).
  Spill loads: 540 → 452 (-16%). Confirmation that the previous
  layout was forcing cache misses that NVCC accounted for as spill.

The net effect — real measured at 1.74 GKey/s vs 1.62 baseline,
+7.4% — is consistent with both the coalescing improvement *and* the
freed L2 cache benefiting the bloom-filter / target-h160 hot path.

---

## Phase 4: Lessons Learned

**1. On Blackwell, occupancy is more valuable than spill elimination.**
The 5080 has narrow scheduling windows and depends on having many
in-flight warps to hide memory latency. A 128-reg cap that costs 640 B
of spill is probably the right tradeoff up to compute capability 12.0.
Removing the cap on a hash kernel is **not** automatically a win.

**2. NVCC's static analysis lies about cost.** `ptxas info` reports
register pressure, spill bytes, stack frame, and shared memory. It does
*not* report occupancy, latency-hiding effectiveness, instruction-cache
fragmentation, or L2 residency. Three of the four metrics it does
report were better in every regressing commit. None of those metrics
correlated with throughput.

**3. Static analysis can lie — bisect always.** Each of the 5 commits
"looked good" by ptxas metrics. A real-hardware bisect at small
granularity (one optimization per commit) was the only way to find the
truth. This is doubly important on consumer Blackwell where occupancy
behavior differs from documented A100 / H100 patterns.

**4. VRAM pressure on the L2 cache is invisible to ptxas.** The biggest
multiplier on the dx/subp change was probably *not* the coalescing —
it was freeing 11 GB so the small hot structures could stay resident.
Future optimization passes should treat VRAM headroom as a first-class
metric, not just total allocation.

**5. The original ROI projections (~3–5 GKey/s ceiling) were 3× too
optimistic.** The actual ceiling without algorithmic changes appears
to be much closer to 1.74 GKey/s/GPU on this hardware. Future
analysis should derate static-analysis projections by ~3× when
applied to consumer Blackwell.

---

## Phase 5: Methodology for Future Optimization Passes

1. **Always bisect.** One optimization per commit. Even if 5 are
   "obviously cheap and stackable", they probably aren't all wins.
2. **Always benchmark on real hardware.** ptxas metrics are necessary
   but radically insufficient. Build per-commit and run a 60–140 s
   steady-state benchmark.
3. **Track occupancy, not just registers.** Use `nvidia-smi
   dmon -s u` during a run, or `ncu --section LaunchStats` after, to
   confirm achieved occupancy hasn't dropped vs baseline.
4. **Track VRAM pressure as an L2 cache proxy.** If a change reduces
   VRAM usage on a kernel that touches read-only structures, expect a
   non-obvious win even if the kernel-level change looks neutral.
5. **Be skeptical of "stackable" wins.** Predicted gains compose
   arithmetically only when the optimizations are genuinely
   independent. If two wins both consume occupancy (extra registers,
   extra shared mem), the second one is usually negative.
6. **Smoke-test every commit.** `make smoke` runs Puzzle #1 in 30 s.
   Cheap insurance against silent correctness breaks.

---

## Reproducing the bisect

```bash
cd /root/Bot
git fetch origin

for sha in 16670ef 792575e 70022de 36336a0 48f84f7 9df2eb7 b683a5a; do
  echo "=== $sha ==="
  git checkout $sha
  cd SearchK4_optimized
  make clean >/dev/null
  make searchk4_fast 2>&1 | grep -E "stack frame|Used [0-9]+|spill"
  rm -f gpu0.state found_k4*.txt
  echo '1PWo3JeB9jrGwfHDNpdGK54CRas7fsVzXU' > bench_patterns.txt
  timeout 150 ./searchk4_fast -patterns bench_patterns.txt -direct \
      -bits 71 -threads 393216 -gpu 0 2>&1 | grep -E "GKey|Covered" | tail -1
  cd ..
done
```

Expected output (140 s steady state column):

```
16670ef  baseline                     1.62 GKey/s
792575e  #undef ASSEMBLY_SIGMA        1.62 GKey/s
70022de  drop -maxrregcount=128       1.55 GKey/s
36336a0  __forceinline__              1.46 GKey/s
48f84f7  two-level bloom              1.23 GKey/s
9df2eb7  + dx/subp on stack           1.60 GKey/s
b683a5a  ONLY dx/subp on stack        1.74 GKey/s
```

---

## Phase 6: Tier-2 Sweeps

After locking in the dx/subp-on-stack change, three tier-2 ideas were
tested on the same 5080.

### Thread count sweep (steady-state ~90s runs, dx/subp-on-stack tip)

| `-threads` | GKey/s |
|---|---|
| 65,536    | 1.40 |
| 131,072   | 1.58 |
| 196,608   | 1.65 |
| 262,144   | 1.69 |
| 327,680   | 1.72 |
| **393,216** *(prior default)* | **1.72** |
| 458,752   | 1.73 |
| 524,288   | 1.75 |
| **655,360** *(new default)* | **1.77** |
| 786,432   | 1.73 |
| 1,048,576 | 1.76 |

Hypothesis going in: 393K is overkill for ~32K resident on RTX 5080,
so lower `nbThread` should win by reducing per-iter setup overhead.
**Hypothesis was wrong.** Higher thread counts give the SM scheduler
more queued blocks to keep in-flight, which apparently hides launch
+ memcpy overhead better than fewer-but-fatter iterations. The peak is
at 655,360 threads (~+2.3% over 393,216). Above that, returns
diminish — 786K is slightly worse, suggesting some second-order cost
(maybe d_keys VRAM pressure) creeping back in.

**Action:** Bumped `defaultThreads` from 393,216 to 655,360 in
direct mode.

### MAXREG sweep (655,360 threads, dx/subp-on-stack tip)

Re-ran a register-cap sweep now that dx/subp is on the stack, in case
the dynamics had changed.

| MAXREG | regs used | GKey/s |
|---|---|---|
| 128 *(current)* | 128 | 1.77 |
| 144 | 144 | 1.79 (long-run: 1.78) |
| 160 | 160 | 1.77 |
| 176 | 176 | 1.70 |
| 192 | 192 | 1.73 |
| 224 | 224 | 1.70 |
| 256 | 198 | 1.73 |

`MAXREG=144` is a marginal +0.5% improvement (within noise). The
spill profile improves meaningfully (160/316 vs 204/452 spill
stores/loads), but the throughput delta is too small to be confident.
**Not committing this change** — keeping `-maxrregcount=128` for now.
Revisit in a future pass with multi-run averaging.

### `NB_THREAD_PER_GROUP` (block size) sweep

Tested 32, 64 (default), 96, 128. All gave ~1.77 GKey/s within noise
on the long-run column. **Not changing.**

### `ncu` profiler

The vast.ai instance has `ncu` installed but
`ERR_NVGPUCTRPERM` blocks userland access to the perf counters. Would
need root + kernel-module reconfiguration to enable, which would
require a host reboot. **Skipped.** A more thorough optimization pass
would require a non-cloud GPU or a vast.ai instance with relaxed
counter permissions.

### Other tier-2 ideas that don't apply on closer inspection

- **Bloom L1 in registers.** Bloom filters are positional — every
  thread needs the *same* filter contents to probe its own hash.
  Per-thread register copies of a 256-bit filter wouldn't reject
  anything (FP rate ≈ 100% with 4000 targets in 256 bits).
  Constant memory broadcast would serialize on hash divergence.
  **Skipped.**
- **`__constant__` bloom filter.** Same problem: each thread queries
  a different bloom slot, so `__constant__`'s broadcast advantage
  vanishes and serializes the warp.
- **Manual block-strided dx/subp.** The whole point of the local-mem
  ABI win is that NVCC + CUDA hardware do this for free. Manual
  rewrite would add complexity without changing the actual access
  pattern. **Skipped.**

---

## Tier-2 Final Tally

| Change | Δ from prior | Cumulative from baseline |
|---|---|---|
| dx/subp on stack (Phase 3) | +7.4% | 1.62 → 1.74 GKey/s |
| nbThread default 655,360 | +2.3% | 1.74 → 1.77 GKey/s |
| (MAXREG=144 — not committed; +0.5%) | — | — |

**Final: 1.62 → 1.77 GKey/s = +9.3% per RTX 5080.**

8-GPU aggregate projection: ~13.0 → ~14.2 GKey/s.

---

## What's left on the table

After this pass, the kernel is genuinely close to its single-GPU
ceiling without algorithmic changes. To push past ~1.8 GKey/s/5080,
the levers that remain are all expensive or risky:

1. **Profile with `ncu` on a permissive-counter host.** Without it,
   we're still guessing at the bottleneck. With it, we'd know if
   we're memory-bound, issue-bound, or stalled on a specific
   instruction.
2. **GLV endomorphism.** Cuts EC scalar-mul work by ~40% but
   requires correctness-critical math infra. ~3–5 days.
3. **Pollard kangaroo.** Rejected by the user, but for completeness:
   ~10¹⁰× expected speedup on the *actual* puzzle problem. ~1–3 days.
4. **PTX hand-tuning of the inner SHA-256 / RIPEMD-160.** sm_120
   exposes new instructions vs sm_86 era code. ~1 week.

Without one of those, ~1.77 GKey/s / 14 GKey/s aggregate is the
practical ceiling for this codebase on this hardware.
