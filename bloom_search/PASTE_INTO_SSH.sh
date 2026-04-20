#!/bin/bash
#
# PASTE THIS ENTIRE SCRIPT INTO YOUR SSH SESSION
# After connecting with: ssh -p 39975 root@ssh5.vast.ai
#
# This will:
# 1. Download 55M Bitcoin addresses
# 2. Build ~200 MB bloom filter
# 3. Create GPU kernel header
# 4. Test VanitySearch is working
#

set -e

echo "=============================================="
echo "BloomSearch Setup"
echo "=============================================="

cd /root/VanitySearch 2>/dev/null || cd /workspace 2>/dev/null || cd ~

# Create build_bloom.py
cat > build_bloom.py << 'PYTHON_EOF'
#!/usr/bin/env python3
import hashlib, struct, os, math, gzip, urllib.request, time, sys

FALSE_POSITIVE_RATE = 1e-7
ADDRESS_URL = "http://addresses.loyce.club/Bitcoin_addresses_LATEST.txt.gz"
BASE58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
B58MAP = {c: i for i, c in enumerate(BASE58)}

def b58dec(s):
    z = sum(1 for c in s if c == '1')
    n = 0
    for c in s:
        if c not in B58MAP: return None
        n = n * 58 + B58MAP[c]
    r = []
    while n > 0: r.append(n & 0xff); n >>= 8
    return bytes([0]*z) + bytes(reversed(r))

def addr2h160(a):
    try:
        d = b58dec(a)
        if d is None or len(d) != 25: return None
        if d[-4:] != hashlib.sha256(hashlib.sha256(d[:-4]).digest()).digest()[:4]: return None
        return d[1:21]
    except: return None

def bech32dec(a):
    CS = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    try:
        p = a.rfind('1')
        if p < 1: return None
        v = [CS.index(c) for c in a[p+1:].lower()]
        d5 = v[1:-6]; acc = bits = 0; r = []
        for x in d5:
            acc = (acc << 5) | x; bits += 5
            while bits >= 8: bits -= 8; r.append((acc >> bits) & 0xff)
        return bytes(r) if len(r) in (20, 32) else None
    except: return None

def mm3(d, s):
    c1, c2 = 0xcc9e2d51, 0x1b873593
    h = s & 0xffffffff
    for i in range(len(d)//4):
        k = struct.unpack('<I', d[i*4:i*4+4])[0]
        k = ((k * c1) & 0xffffffff)
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * c2) & 0xffffffff
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xffffffff
        h = ((h * 5) + 0xe6546b64) & 0xffffffff
    t = d[(len(d)//4)*4:]
    k = 0
    for i, b in enumerate(t): k |= b << (i*8)
    if t:
        k = ((k * c1) & 0xffffffff)
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * c2) & 0xffffffff
        h ^= k
    h ^= len(d)
    h ^= h >> 16; h = (h * 0x85ebca6b) & 0xffffffff
    h ^= h >> 13; h = (h * 0xc2b2ae35) & 0xffffffff
    return h ^ (h >> 16)

class BF:
    def __init__(s, m, k):
        s.m, s.k = m, k
        s.b = bytearray(((m+7)//8+3)//4*4)
        s.seeds = [0x7a2f3c1d,0x9e8b4f2a,0x3d5c7e9b,0x1f4a6b8c,0x5c9d2e7f,
                   0x8b3a4f1e,0x2e7c9d5a,0x4f1b8c3e,0x6a9e2d7c,0x3c8f5b1a,
                   0x9d4e7a2f,0x1b6c3f8e,0x7e2a9d5c,0x4c8b1f3a,0x5a3e7c9d,
                   0x2f9c4b8e,0x8d5a2e7f,0x3b7f9c4e,0x6c1a5d3b,0x9f4e2a7c][:k]
        s.n = 0
    def add(s, d):
        for sd in s.seeds:
            p = mm3(d, sd) % s.m
            s.b[p//8] |= 1 << (p%8)
        s.n += 1
    def save(s, fn):
        with open(fn, 'wb') as f:
            f.write(struct.pack('<QQ', s.m, len(s.b)))
            f.write(struct.pack('<II', s.k, s.n))
            for sd in s.seeds: f.write(struct.pack('<I', sd))
            f.write(b'\x00' * (256 - 24 - s.k*4))
            f.write(s.b)

print("BloomSearch - Building Bloom Filter")
print("=" * 50)

if os.path.exists('targets.bloom') and os.path.getsize('targets.bloom') > 1e8:
    print("Bloom filter already exists!")
    sys.exit(0)

af = 'Bitcoin_addresses_LATEST.txt'
if not os.path.exists(af):
    print(f"Downloading addresses...")
    def prog(b,bs,ts): print(f"\r  {min(100,b*bs*100/ts):.1f}%", end='', flush=True)
    urllib.request.urlretrieve(ADDRESS_URL, af+'.gz', prog)
    print("\nExtracting...")
    with gzip.open(af+'.gz','rb') as fi, open(af,'wb') as fo:
        while c := fi.read(1<<20): fo.write(c)
    os.remove(af+'.gz')

print("Counting..."); total = sum(1 for _ in open(af)); print(f"Total: {total:,}")
m = int(-total * math.log(FALSE_POSITIVE_RATE) / (math.log(2)**2))
k = min(20, int(m/total * math.log(2)))
print(f"Filter: {m:,} bits ({m/8/1024/1024:.1f} MB), {k} hashes")

bf = BF(m, k); h160s = []; t0 = time.time(); done = 0
with open(af) as f:
    for ln in f:
        a = ln.strip()
        h = bech32dec(a) if a.startswith('bc1') else addr2h160(a) if a[0] in '13' else None
        if h:
            if len(h) > 20: h = h[:20]
            bf.add(h); h160s.append(h)
        done += 1
        if done % 1000000 == 0:
            r = done/(time.time()-t0)
            print(f"\r  {done:,}/{total:,} ({done*100/total:.1f}%) - ETA: {(total-done)/r:.0f}s", end='', flush=True)

print(f"\n\nAdded {bf.n:,} addresses")
bf.save('targets.bloom')
print(f"Saved targets.bloom ({os.path.getsize('targets.bloom')/1024/1024:.1f} MB)")

print("Sorting hash160s...")
h160s.sort()
with open('targets.sorted', 'wb') as f:
    for h in h160s: f.write(h)
print(f"Saved targets.sorted ({len(h160s)*20/1024/1024:.1f} MB)")
print("\nDone!")
PYTHON_EOF

# Create GPUComputeBloom.h
mkdir -p GPU
cat > GPU/GPUComputeBloom.h << 'CUDA_EOF'
// Bloom filter for VanitySearch GPU
__device__ uint8_t* d_bloomData;
__device__ uint64_t d_bloomBits;
__device__ uint32_t d_bloomHashes;
__device__ uint32_t d_bloomSeeds[24];

__device__ __forceinline__ uint32_t rotl32_b(uint32_t x, int8_t r) {
    return (x << r) | (x >> (32 - r));
}

__device__ __forceinline__ uint32_t murmur3_32(const uint8_t* key, int len, uint32_t seed) {
    uint32_t h1 = seed, c1 = 0xcc9e2d51, c2 = 0x1b873593;
    const uint32_t* blocks = (const uint32_t*)key;
    for (int i = 0; i < len/4; i++) {
        uint32_t k1 = blocks[i] * c1;
        k1 = rotl32_b(k1, 15) * c2;
        h1 = rotl32_b(h1 ^ k1, 13) * 5 + 0xe6546b64;
    }
    const uint8_t* tail = key + (len/4)*4;
    uint32_t k1 = 0;
    switch (len & 3) {
        case 3: k1 ^= tail[2] << 16;
        case 2: k1 ^= tail[1] << 8;
        case 1: k1 ^= tail[0];
            k1 = rotl32_b(k1 * c1, 15) * c2; h1 ^= k1;
    }
    h1 ^= len; h1 ^= h1 >> 16;
    h1 = (h1 * 0x85ebca6b) ^ ((h1 * 0x85ebca6b) >> 13);
    return (h1 * 0xc2b2ae35) ^ ((h1 * 0xc2b2ae35) >> 16);
}

__device__ __forceinline__ bool bloom_check(const uint8_t* hash160) {
    for (uint32_t i = 0; i < d_bloomHashes; i++) {
        uint32_t h = murmur3_32(hash160, 20, d_bloomSeeds[i]);
        if (!(d_bloomData[(h % d_bloomBits) >> 3] & (1 << ((h % d_bloomBits) & 7))))
            return false;
    }
    return true;
}

__device__ __noinline__ void CheckPointBloom(uint32_t* _h, int32_t incr, int32_t endo,
    int32_t mode, uint32_t maxFound, uint32_t* out) {
    if (bloom_check((uint8_t*)_h)) {
        uint32_t tid = (blockIdx.x * blockDim.x) + threadIdx.x;
        uint32_t pos = atomicAdd(out, 1);
        if (pos < maxFound) {
            out[pos*ITEM_SIZE32+1] = tid;
            out[pos*ITEM_SIZE32+2] = (incr<<16)|(mode<<15)|endo;
            out[pos*ITEM_SIZE32+3] = _h[0]; out[pos*ITEM_SIZE32+4] = _h[1];
            out[pos*ITEM_SIZE32+5] = _h[2]; out[pos*ITEM_SIZE32+6] = _h[3];
            out[pos*ITEM_SIZE32+7] = _h[4];
        }
    }
}
#define CHECK_POINT_BLOOM(h,i,e,m) CheckPointBloom(h,i,e,m,maxFound,out)
CUDA_EOF

echo ""
echo "Files created:"
ls -la build_bloom.py GPU/GPUComputeBloom.h

echo ""
echo "=============================================="
echo "Building bloom filter (takes ~15-20 minutes)..."
echo "=============================================="
python3 build_bloom.py

echo ""
echo "=============================================="
echo "Checking results..."
echo "=============================================="
ls -lh targets.bloom targets.sorted 2>/dev/null || echo "Files not found"

echo ""
echo "Testing VanitySearch GPU..."
timeout 10 ./VanitySearch -gpu -stop 1Test 2>&1 | tail -20 || echo "VanitySearch test skipped"

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "Bloom filter: targets.bloom"
echo "Verification: targets.sorted"
echo "GPU header:   GPU/GPUComputeBloom.h"
