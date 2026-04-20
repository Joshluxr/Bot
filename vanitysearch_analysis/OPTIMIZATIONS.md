# VanitySearch Performance Optimizations

This document describes the performance optimizations implemented for VanitySearch, with expected speedup estimates and integration instructions.

## Summary of Optimizations

| Optimization | File | Expected Speedup | Applies To |
|-------------|------|------------------|------------|
| 5×52-bit field arithmetic | `Field52.h` | 15-25% on field ops | CPU & GPU |
| GLV decomposition | `GLV.h` | 10-15% on scalar mult | CPU |
| Batch affine conversion | `GPU/GPUAffineBatch.h` | 30-50% on GPU | GPU only |
| Memory coalescing (SoA) | `GPU/GPUMemoryOptimized.h` | 10-20% on GPU | GPU only |

## 1. 5×52-bit Field Representation (`Field52.h`)

### Concept

The original VanitySearch uses 4×64-bit limbs for 256-bit field elements. We implement 5×52-bit limbs following libsecp256k1's approach.

**Why 52-bit limbs are faster:**
- 52 × 52 = 104 bits, which fits in a 128-bit intermediate without overflow
- Allows "lazy reduction" - delaying carry propagation across multiple operations
- Reduces the number of reduction operations needed

### Key Functions

```c
// Conversion
field_from_64(field_elem *r, const uint64_t *a);  // 4×64 → 5×52
field_to_64(uint64_t *r, const field_elem *a);    // 5×52 → 4×64

// Arithmetic
field_mul(field_elem *r, const field_elem *a, const field_elem *b);
field_sqr(field_elem *r, const field_elem *a);
field_add(field_elem *r, const field_elem *a, const field_elem *b);
field_sub(field_elem *r, const field_elem *a, const field_elem *b);
field_normalize(field_elem *r);  // Full reduction mod p
```

### Integration

Replace hot-path `ModMulK1` calls with `field_mul`:

```cpp
// Before:
c.ModMulK1(&a, &b);

// After:
field_elem fa, fb, fc;
field_from_64(&fa, a.bits64);
field_from_64(&fb, b.bits64);
field_mul(&fc, &fa, &fb);
field_normalize(&fc);
field_to_64(c.bits64, &fc);
```

For best performance, keep values in 5×52 format throughout computation chains and only convert at boundaries.

---

## 2. GLV Decomposition (`GLV.h`)

### Concept

The secp256k1 curve has an efficiently computable endomorphism:
```
φ(x, y) = (β·x, y)  where β³ ≡ 1 (mod p)
φ(P) = λ·P          where λ³ ≡ 1 (mod n)
```

For scalar multiplication k·P:
1. Decompose k into k₁, k₂ where k = k₁ + k₂·λ (mod n)
2. |k₁|, |k₂| ≈ √n (128 bits instead of 256)
3. Compute k·P = k₁·P + k₂·φ(P) using half-length scalars

This roughly **halves the number of point doublings**.

### Key Functions

```cpp
// Initialize GLV constants
GLV::Init(Secp256K1 *secp);

// Decompose scalar
GLV::Decompose(const Int *k, Int *k1, Int *k2, bool *k1neg, bool *k2neg);

// Scalar multiplication with GLV
Point result = GLV::ScalarMult(secp, &k, &P);

// wNAF variant for additional speedup
Point result = GLV::ScalarMultWNAF(secp, &k, &P, windowSize);
```

### Integration

Replace `ComputePublicKey` for initial key generation:

```cpp
// Before:
Point p = secp->ComputePublicKey(&k);

// After:
GLV::Init(secp);  // Once at startup
Point p = GLV::ScalarMult(secp, &k, &secp->G);
```

**Note:** VanitySearch already uses endomorphisms for the 6× address multiplier. GLV optimization applies primarily to the initial `ComputePublicKey` calls.

---

## 3. GPU Batch Affine Conversion (`GPU/GPUAffineBatch.h`)

### Concept

Converting projective coordinates (X:Y:Z) to affine (x, y) requires modular inversion:
- x = X · Z⁻²
- y = Y · Z⁻³

Individual inversion is expensive (~100× slower than multiplication). Using **Montgomery's batch inversion trick**:

```
For N elements [z₀, z₁, ..., zₙ₋₁]:
1. Compute cumulative products: c[i] = c[i-1] · z[i]
2. Invert once: inv = c[N-1]⁻¹
3. Recover inverses: z[i]⁻¹ = inv · c[i-1]; inv = inv · z[i]

Total: 1 inversion + 3(N-1) multiplications
```

With N=128, this is approximately **40× faster** than individual inversions.

### Key Functions

```cuda
// Batch convert projective to affine
__device__ void batch_to_affine(
    ProjectivePoint *proj,   // Input projective points
    AffinePoint *affine,     // Output affine points
    int count                // Number of points
);
```

### Integration

Modify the GPU kernel to batch points before hashing:

```cuda
// Original: convert each point individually
for (int i = 0; i < STEP_SIZE; i++) {
    // Point addition in projective
    // Convert to affine (expensive!)
    // Hash
}

// Optimized: batch convert
for (int step = 0; step < STEP_SIZE; step += BATCH_SIZE) {
    // Accumulate BATCH_SIZE points in projective
    batch_to_affine(projective, affine, BATCH_SIZE);  // Single batch inversion!
    // Hash all BATCH_SIZE points
}
```

---

## 4. GPU Memory Optimization (`GPU/GPUMemoryOptimized.h`)

### Concept

The original code uses **Array of Structures (AoS)**:
```
keys[i] = {x[0], x[1], x[2], x[3], y[0], y[1], y[2], y[3]}
```

When thread i accesses `keys[i]`, adjacent threads access non-contiguous memory, causing **uncoalesced access** (multiple memory transactions).

Switching to **Structure of Arrays (SoA)**:
```
x0[i], x1[i], x2[i], x3[i]  // All x[0] values together
y0[i], y1[i], y2[i], y3[i]  // All x[1] values together
...
```

Now adjacent threads access adjacent memory → **coalesced access** (single transaction for 32 threads).

### Additional Optimizations

1. **Texture memory for prefix table**: Read-only data with spatial locality benefits from texture cache
2. **Shared memory tiling**: Load generator table tiles into fast shared memory
3. **128-bit vector loads**: Use `uint4` for aligned 16-byte loads
4. **Warp-level primitives**: Fast `__any_sync`, `__ballot_sync` for match detection

### Integration

```cpp
// Host: Convert AoS to SoA before upload
KeysSoA h_keys, d_keys;
allocateKeysSoA(&h_keys, numKeys);
convertAoStoSoA(keysAoS, &h_keys, numKeys);
allocateKeysSoA(&d_keys, numKeys);
copyKeysSoAToDevice(&d_keys, &h_keys, numKeys);

// Kernel: Use SoA layout
__global__ void compute_keys_optimized(
    uint64_t *x0, uint64_t *x1, uint64_t *x2, uint64_t *x3,
    uint64_t *y0, uint64_t *y1, uint64_t *y2, uint64_t *y3,
    ...
) {
    int gid = blockIdx.x * blockDim.x + threadIdx.x;
    // Coalesced loads
    uint64_t px0 = x0[gid];  // Thread 0-31 load consecutive addresses
    uint64_t px1 = x1[gid];
    ...
}
```

---

## Benchmark Results

Run the benchmark to see actual speedups on your hardware:

```bash
# Compile
g++ -O3 -march=native -o benchmark benchmark.cpp \
    Int.cpp IntMod.cpp IntGroup.cpp SECP256K1.cpp Point.cpp Random.cpp \
    -lpthread

# Run
./benchmark
```

### Expected Output

```
=== Field Multiplication Benchmark ===
Original (4x64):  XXX ms for 1000000 iterations
Optimized (5x52): XXX ms for 1000000 iterations
Speedup: ~1.20x

=== Scalar Multiplication Benchmark ===
Standard:  XXX ms for 10000 iterations
GLV:       XXX ms for 10000 iterations
Speedup: ~1.15x

=== Batch Inversion Benchmark ===
Batch size 128: Individual XXX ms, Batch XXX ms, Speedup ~40x
```

---

## Integration Checklist

### CPU Optimizations

- [ ] Replace `Int` field operations with `field_elem` in hot paths
- [ ] Use `GLV::ScalarMult` for initial public key computation
- [ ] Ensure batch inversion is used for group operations (already implemented)

### GPU Optimizations

- [ ] Convert key storage to SoA layout
- [ ] Implement batch affine conversion in kernel
- [ ] Bind prefix table to texture memory
- [ ] Add shared memory tiling for generator table
- [ ] Use vector loads (`uint4`) for aligned data

### Testing

- [ ] Run benchmark to verify speedups
- [ ] Verify output correctness with `-check` flag
- [ ] Test with various prefix patterns
- [ ] Profile with `nvprof` or Nsight for GPU

---

## Compatibility Notes

1. **5×52 field arithmetic** requires 128-bit integer support (available on x64 and CUDA)
2. **GLV decomposition** uses the same endomorphism constants VanitySearch already has
3. **GPU optimizations** require CUDA compute capability 3.0+ (for warp intrinsics)
4. **Texture memory API** varies between CUDA versions; code includes both legacy and modern paths

---

## References

- [libsecp256k1](https://github.com/bitcoin-core/secp256k1) - 5×52 field implementation
- [GLV Paper](https://www.iacr.org/archive/crypto2001/21390189.pdf) - Gallant-Lambert-Vanstone method
- [Montgomery's Trick](https://en.wikipedia.org/wiki/Montgomery_modular_multiplication) - Batch inversion
- [CUDA Best Practices](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/) - Memory coalescing
