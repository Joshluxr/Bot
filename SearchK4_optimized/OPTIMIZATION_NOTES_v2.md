# SearchK4 Optimization Notes v2 — Stack-Local dx/subp + Thread Count Tuning

## Summary

Two changes yielding **+9.3% throughput** (1.62 → 1.77 GKey/s per GPU) and **-60% VRAM usage** (12.7 GB → 5.2 GB per GPU).

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Per-GPU throughput | 1.62 GKey/s | 1.77 GKey/s | **+9.3%** |
| 8-GPU total | 12.7 GKey/s | 14.0 GKey/s | **+9.3%** |
| VRAM per GPU | 12,742 MiB | 5,234 MiB | **-59%** |
| Cumulative gain (from 0.53 baseline) | +208% | +234% | |

## Change 1: dx/subp moved from cudaMalloc to per-thread stack arrays (+7.4%)

### What changed

`ComputeKeysK4()` previously received two `uint64_t*` pointers into globally-allocated buffers. Host code did:
```c
cudaMalloc(&d_dx, nbThread * 513 * 4 * 8);   // ~6.4 GB at 393K threads
cudaMalloc(&d_subp, nbThread * 513 * 4 * 8);  // ~6.4 GB
// Total: ~12.9 GB for dx+subp alone
```

Each thread indexed into its slice via `tid * arraySize`.

Now `ComputeKeysK4()` declares local arrays:
```c
uint64_t dx[GRP_SIZE / 2 + 1][4];   // ~16 KB per thread
uint64_t subp[GRP_SIZE / 2 + 1][4]; // ~16 KB per thread
```

The `cudaMalloc`/`cudaFree` calls, the `dx_buffer`/`subp_buffer` pointer-passing through the kernel, and the `tid * arraySize` indexing are all deleted.

### Why it works

1. **Warp-coalesced access.** Local variables in CUDA "local memory" are backed by global memory but the hardware auto-strides accesses across the warp: when 32 lanes access `dx[i]`, the hardware emits 32 contiguous 8-byte loads instead of 32 loads strided by 16 KB. ~32× reduction in cacheline transactions on dx/subp accesses.

2. **VRAM scales with resident threads, not total threads.** The previous flat cudaMalloc used `nbThread × 16 KB × 2 = 12.9 GB` regardless of occupancy. Local memory uses only `resident_threads × 16 KB × 2 ≈ 1 GB` (RTX 5080: 84 SMs × ~6 blocks × 64 threads = ~32K resident). The freed ~12 GB becomes available L2 cache for `d_bloom_filter`, `d_target_h160`, and other read-only structures.

### Configuration change

Stack size bumped from 2 KB to 40 KB:
```c
cudaDeviceSetLimit(cudaLimitStackSize, 40 * 1024);
```
Kernel reports 33,824 bytes stack frame (measured by ptxas).

## Change 2: defaultThreads 393,216 → 655,360 (+2.3%)

Changed one line:
```c
int defaultThreads = directMode ? 655360 : 1024;
```

With dx/subp as local memory, VRAM usage is decoupled from thread count. More threads give the SM scheduler more queued blocks to keep in-flight, hiding launch + memcpy overhead between kernel iterations. Empirical sweep: 655K is the steady-state peak (786K slightly worse, 1M comparable).

## What was tried but rejected

Based on bisect testing by a parallel session on real RTX 5080 hardware:

1. **`#undef ASSEMBLY_SIGMA`**: Neutral. NVCC 13 folds the C macro to the same `shf.r.wrap.b32`.
2. **Drop `-maxrregcount=128`**: **-4.3%**. Going 128 → 198 regs cratered occupancy from ~8 → ~5 blocks/SM.
3. **`__forceinline__` hot-path functions**: **-5.7%**. I-cache fragmentation outweighs saved noinline-ABI spills.
4. **Two-level bloom (8 KB shared + 64 KB global)**: **-14.4%**. 8 KB shared/block × 5 blocks/SM = 40 KB shared/SM consumed, killing occupancy.

## Bisect data

```
baseline (16670ef)                       1.62 GKey/s
+ dx/subp on stack ALONE                 1.74 GKey/s   (+7.4%)
+ defaultThreads 393K → 655K             1.77 GKey/s   (+9.3% total)
```

## Build

```bash
make clean && make searchk4_fast    # auto-detects CCAP
make print-config                   # verify build settings
make smoke                          # Puzzle #1 end-to-end test
```

Compiler output confirms:
- 33,824 bytes stack frame (dx/subp as local arrays)
- 128 registers (capped by -maxrregcount)
- 204 bytes spill stores, 452 bytes spill loads

## Key lessons

1. **Occupancy beats spill elimination on RTX 5080.** The 128-reg cap is a feature.
2. **VRAM headroom = L2 cache pressure.** Reducing VRAM usage on a kernel touching read-only structures has a non-obvious throughput win.
3. **Always bisect on real hardware.** Static ptxas metrics did not correlate with actual throughput on Blackwell.
