/*
 * GPU Bloom Filter Search Kernel
 * Based on VanitySearch by Jean-Luc PONS
 * Modified for bitmap prefix lookup + candidate output for CPU bloom check
 */

// Output item size: tid(4) + info(4) + hash160(20) = 28 bytes = 7 uint32s
#define BLOOM_ITEM_SIZE32 7

// Check if hash160 prefix is in bitmap, output candidate if yes
__device__ __noinline__ void CheckBitmapPrefix(
    uint32_t *_h,           // 5 x uint32 = 20 bytes HASH160
    int32_t incr,           // Increment from base key
    int32_t endo,           // Endomorphism index (0,1,2)
    int32_t isComp,         // Compressed (1) or uncompressed (0)
    uint8_t *prefixBitmap,  // 512 MB bitmap
    uint32_t maxFound,
    uint32_t *out
) {
    uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
    
    // Get first 32 bits of hash160 as big-endian
    uint32_t prefix32 = __byte_perm(_h[0], 0, 0x0123);  // Swap endianness
    
    // Check bitmap: prefixBitmap[prefix32 / 8] & (1 << (prefix32 % 8))
    uint32_t byteIdx = prefix32 >> 3;
    uint32_t bitIdx = prefix32 & 7;
    
    uint8_t byte = prefixBitmap[byteIdx];
    if (byte & (1 << bitIdx)) {
        // Prefix matches! Output candidate for CPU bloom check
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            out[pos * BLOOM_ITEM_SIZE32 + 1] = tid;
            out[pos * BLOOM_ITEM_SIZE32 + 2] = (uint32_t)(incr << 16) | (uint32_t)(isComp << 15) | (uint32_t)(endo);
            out[pos * BLOOM_ITEM_SIZE32 + 3] = _h[0];
            out[pos * BLOOM_ITEM_SIZE32 + 4] = _h[1];
            out[pos * BLOOM_ITEM_SIZE32 + 5] = _h[2];
            out[pos * BLOOM_ITEM_SIZE32 + 6] = _h[3];
            out[pos * BLOOM_ITEM_SIZE32 + 7] = _h[4];
        }
    }
}

#define CHECK_BITMAP(_h, incr, endo, isComp)     CheckBitmapPrefix(_h, incr, endo, isComp, prefixBitmap, maxFound, out)

// Check compressed key hashes against prefix bitmap
__device__ __noinline__ void CheckHashBitmapComp(
    uint8_t *prefixBitmap,
    uint64_t *px,
    uint8_t isOdd,
    int32_t incr,
    uint32_t maxFound,
    uint32_t *out
) {
    uint32_t h[5];
    uint64_t pe1x[4];
    uint64_t pe2x[4];

    // Original point
    _GetHash160Comp(px, isOdd, (uint8_t *)h);
    CHECK_BITMAP(h, incr, 0, 1);
    
    // Endomorphism 1
    _ModMult(pe1x, px, _beta);
    _GetHash160Comp(pe1x, isOdd, (uint8_t *)h);
    CHECK_BITMAP(h, incr, 1, 1);
    
    // Endomorphism 2
    _ModMult(pe2x, px, _beta2);
    _GetHash160Comp(pe2x, isOdd, (uint8_t *)h);
    CHECK_BITMAP(h, incr, 2, 1);

    // Symmetric points (negated Y)
    _GetHash160Comp(px, !isOdd, (uint8_t *)h);
    CHECK_BITMAP(h, -incr, 0, 1);
    _GetHash160Comp(pe1x, !isOdd, (uint8_t *)h);
    CHECK_BITMAP(h, -incr, 1, 1);
    _GetHash160Comp(pe2x, !isOdd, (uint8_t *)h);
    CHECK_BITMAP(h, -incr, 2, 1);
}

// Main compute function for bloom search (compressed keys only for now)
__device__ void ComputeKeysBitmap(
    uint64_t *startx,
    uint64_t *starty,
    uint8_t *prefixBitmap,
    uint32_t maxFound,
    uint32_t *out
) {
    uint64_t dx[GRP_SIZE / 2 + 1][4];
    uint64_t px[4];
    uint64_t py[4];
    uint64_t pyn[4];
    uint64_t sx[4];
    uint64_t sy[4];
    uint64_t dy[4];
    uint64_t _s[4];
    uint64_t _p[4];
    uint8_t  isOdd;

    // Load starting point
    __syncthreads();
    Load256A(sx, startx);
    Load256A(sy, starty);
    Load256(px, sx);
    Load256(py, sy);

    // Compute differences for batch inversion
    for (int32_t i = 0; i < GRP_SIZE / 2; i++) {
        ModSub256(dx[i], Gx[i], px);
    }
    ModSub256(dx[GRP_SIZE / 2], Gx[GRP_SIZE / 2 - 1], px);

    // Batch modular inversion
    _ModInvGrouped(dx);

    // First point check
    isOdd = IsOdd256(IsY256);
    CheckHashBitmapComp(prefixBitmap, IsX256, isOdd, 0, maxFound, out);

    // Process group of points
    for (int32_t i = 0; i < GRP_SIZE / 2; i++) {
        // P + i*G
        ModSub256(dy, IsY256, IsMyY256);
        _ModMult(_s, IsMyD256, IsMyDD256);
        _ModSqr(_p, _s);
        ModSub256(px, _p, IsMyX256);
        ModSub256(px, px, IsX256);
        ModSub256(py, IsX256, px);
        _ModMult(py, IsMyS256, py);
        ModSub256(py, py, IsMyYY256);

        isOdd = IsOdd256(py);
        CheckHashBitmapComp(prefixBitmap, px, isOdd, i + 1, maxFound, out);
    }

    // Negate Y for symmetric points
    ModNeg256(IsY256, sy);
    for (int32_t i = 0; i < GRP_SIZE / 2; i++) {
        // P - i*G  
        ModSub256(dy, IsMyY256, IsY256);
        _ModMult(_s, IsMyD256, IsMyDD256);
        _ModSqr(_p, _s);
        ModSub256(px, _p, IsMyX256);
        ModSub256(px, px, IsX256);
        ModSub256(py, IsX256, px);
        _ModMult(py, IsMyS256, py);
        ModSub256(py, py, IsMyYY256);

        isOdd = IsOdd256(py);
        CheckHashBitmapComp(prefixBitmap, px, isOdd, -(i + 1), maxFound, out);
    }

    // Store updated point for next iteration
    Load256(IsX256, IsMyX256);
    Load256(IsY256, IsMyYY256);
    __syncthreads();
    Store256A(startx, IsX256);
    Store256A(starty, IsY256);
}
