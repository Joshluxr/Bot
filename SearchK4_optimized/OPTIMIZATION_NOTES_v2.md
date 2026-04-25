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
| Per-GPU throughput | 1.62 GKey/s | 1.74 GKey/s | **+7.4%** |
| 8-GPU aggregate (projected) | ~13.0 GKey/s | ~13.9 GKey/s | +7.4% |
| dx/subp VRAM | 12.9 GB | ~1 GB | **-11.9 GB freed** |
| Per-kernel spill stores / loads | 224 / 540 B | 204 / 452 B | -9% / -16% |
| Stack frame | 1008 B | 33824 B | (now in local memory, auto-coalesced) |

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

## Future Tier-2 Ideas (this pass, in progress)

- **Sweep `nbThread` downward** (393K is overkill at ~32K resident on
  5080). Lower thread count → less per-iter setup → potentially
  higher steady-state throughput.
- **Sweep `MAXREG`** (144, 160, 192) with dx/subp-on-stack to find
  the spill / occupancy sweet spot.
- **Bloom L1 in registers** (very small, e.g. 256–1024 bits) to
  short-circuit before any memory access at all. Costs registers,
  not occupancy.
- **Manual block-strided dx/subp** as a sanity check that NVCC's
  auto-stride is actually optimal.
- **Profile with `ncu`** to find the actual bottleneck (memory
  bandwidth? L2 hit rate? warp issue stall?) instead of guessing.

These will be benchmarked the same way and added to PR #19 if they win.
