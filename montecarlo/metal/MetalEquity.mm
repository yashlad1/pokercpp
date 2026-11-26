#import <Metal/Metal.h>
#import <Foundation/Foundation.h>

#include "MetalEquity.h"
#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <random>

static NSString *const kSource = @R"MSL(
#include <metal_stdlib>
using namespace metal;

struct GJob {
    ulong heroMask, boardMask, seed;
    uint comboOff, comboCnt, trials, slice, need, pad0, pad1;
};

// Cards are 0..51: suit*13 + (rank-2). Per-suit 13-bit masks, bit 0 = deuce.
inline int hb(uint x) { return 31 - (int)clz(x); }
inline uint topN(uint x, int n) {
    uint r = 0;
    for (int i = 0; i < n; ++i) { int h = hb(x); r = (r << 4) | (uint)h; x &= ~(1u << h); }
    return r;
}
inline int straightTop(uint m) {
    uint x = (m << 1) | (m >> 12);
    uint y = x & (x >> 1) & (x >> 2) & (x >> 3) & (x >> 4);
    return y ? hb(y) + 3 : -1;
}
inline uint evalMask(ulong m) {
    uint s0 = (uint)(m & 0x1FFF), s1 = (uint)((m >> 13) & 0x1FFF);
    uint s2 = (uint)((m >> 26) & 0x1FFF), s3 = (uint)((m >> 39) & 0x1FFF);
    uint all = s0 | s1 | s2 | s3;
    uint flush = 0;
    uint ss[4] = {s0, s1, s2, s3};
    for (int i = 0; i < 4; ++i) if (popcount(ss[i]) >= 5) flush = ss[i];
    if (flush) { int sf = straightTop(flush); if (sf >= 0) return (8u << 20) | (uint)sf; }
    uint quads = s0 & s1 & s2 & s3;
    uint trips = (s0 & s1 & s2) | (s0 & s1 & s3) | (s0 & s2 & s3) | (s1 & s2 & s3);
    uint pairs = (s0 & s1) | (s0 & s2) | (s0 & s3) | (s1 & s2) | (s1 & s3) | (s2 & s3);
    if (quads) {
        int q = hb(quads);
        return (7u << 20) | ((uint)q << 16) | ((uint)hb(all & ~(1u << q)) << 12);
    }
    if (trips) {
        int t = hb(trips);
        uint p = pairs & ~(1u << t);
        if (p) return (6u << 20) | ((uint)t << 16) | ((uint)hb(p) << 12);
    }
    if (flush) return (5u << 20) | topN(flush, 5);
    int st = straightTop(all);
    if (st >= 0) return (4u << 20) | (uint)st;
    if (trips) {
        int t = hb(trips);
        return (3u << 20) | ((uint)t << 16) | (topN(all & ~(1u << t), 2) << 8);
    }
    if (popcount(pairs) >= 2) {
        int p1 = hb(pairs); uint r = pairs & ~(1u << p1); int p2 = hb(r);
        uint k = all & ~(1u << p1) & ~(1u << p2);
        return (2u << 20) | ((uint)p1 << 16) | ((uint)p2 << 12) | ((uint)hb(k) << 8);
    }
    if (pairs) {
        int p = hb(pairs);
        return (1u << 20) | ((uint)p << 16) | (topN(all & ~(1u << p), 3) << 4);
    }
    return topN(all, 5);
}

struct Rng { ulong s, inc; };
inline uint nextU(thread Rng &r) {
    ulong o = r.s;
    r.s = o * 6364136223846793005UL + r.inc;
    uint x = (uint)(((o >> 18) ^ o) >> 27);
    uint rot = (uint)(o >> 59);
    return (x >> rot) | (x << ((32u - rot) & 31u));
}
inline ulong splitmix(ulong z) {
    z += 0x9E3779B97F4A7C15UL;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL;
    return z ^ (z >> 31);
}
inline void seedRng(thread Rng &r, ulong seed, ulong seq) {
    r.s = 0; r.inc = (seq << 1) | 1UL; nextU(r); r.s += splitmix(seed); nextU(r);
}

kernel void equityKernel(const device GJob *jobs [[buffer(0)]],
                         const device ushort *combos [[buffer(1)]],
                         device atomic_uint *out [[buffer(2)]],
                         constant uint &X [[buffer(3)]],
                         uint2 gid [[thread_position_in_grid]],
                         uint lane [[thread_index_in_simdgroup]]) {
    GJob j = jobs[gid.y];
    uint start = min(gid.x * j.slice, j.trials);
    uint end = min(start + j.slice, j.trials);
    Rng r; seedRng(r, j.seed, (ulong)gid.y * X + gid.x);
    uint w = 0, t = 0;
    for (uint i = start; i < end; ++i) {
        uint pick = (uint)(((ulong)nextU(r) * j.comboCnt) >> 32);
        ushort c = combos[j.comboOff + pick];
        ulong vm = (1UL << (c & 0xFF)) | (1UL << (c >> 8));
        ulong used = j.heroMask | j.boardMask | vm, board = j.boardMask;
        for (uint k = 0; k < j.need; ++k) {
            while (true) {
                uint card = (uint)(((ulong)nextU(r) * 52) >> 32);
                ulong b = 1UL << card;
                if (!(used & b)) { used |= b; board |= b; break; }
            }
        }
        uint hs = evalMask(j.heroMask | board), vs = evalMask(vm | board);
        w += hs > vs; t += hs == vs;
    }
    w = simd_sum(w); t = simd_sum(t);  // all lanes participate (no early return)
    if (lane == 0) {
        atomic_fetch_add_explicit(&out[2 * gid.y], w, memory_order_relaxed);
        atomic_fetch_add_explicit(&out[2 * gid.y + 1], t, memory_order_relaxed);
    }
}

kernel void compareKernel(const device uchar *deals [[buffer(0)]],
                          device char *out [[buffer(1)]],
                          uint gid [[thread_position_in_grid]]) {
    const device uchar *d = deals + gid * 16;
    ulong h = 0, v = 0, b = 0;
    for (int i = 0; i < 2; ++i) h |= 1UL << d[i];
    for (int i = 2; i < 4; ++i) v |= 1UL << d[i];
    for (int i = 4; i < 9; ++i) b |= 1UL << d[i];
    uint hs = evalMask(h | b), vs = evalMask(v | b);
    out[gid] = hs > vs ? 1 : (hs < vs ? -1 : 0);
}
)MSL";

namespace {
struct GJob {
    unsigned long long heroMask, boardMask, seed;
    uint32_t comboOff, comboCnt, trials, slice, need, pad0, pad1;
};
static_assert(sizeof(GJob) == 56, "must match MSL GJob");

struct Ctx {
    id<MTLDevice> dev = nil;
    id<MTLCommandQueue> q = nil;
    id<MTLComputePipelineState> eq = nil, cmp = nil;
    bool ok = false;
};

Ctx &ctx() {
    static Ctx c = [] {
        Ctx c;
        @autoreleasepool {
            const char *off = std::getenv("POKER_NO_METAL");
            if (off && *off == '1') return c;
            c.dev = MTLCreateSystemDefaultDevice();
            if (!c.dev) return c;
            NSError *err = nil;
            id<MTLLibrary> lib = [c.dev newLibraryWithSource:kSource options:nil error:&err];
            if (!lib) { NSLog(@"Metal compile failed: %@", err); return c; }
            c.eq = [c.dev newComputePipelineStateWithFunction:[lib newFunctionWithName:@"equityKernel"] error:&err];
            c.cmp = [c.dev newComputePipelineStateWithFunction:[lib newFunctionWithName:@"compareKernel"] error:&err];
            if (!c.eq || !c.cmp) { NSLog(@"Metal pipeline failed: %@", err); return c; }
            c.q = [c.dev newCommandQueue];
            c.ok = c.q != nil;
        }
        return c;
    }();
    return c;
}

int cardIdx(const Card &c) { return static_cast<int>(c.suit) * 13 + static_cast<int>(c.rank) - 2; }
unsigned long long bit(const Card &c) { return 1ULL << cardIdx(c); }

void run(id<MTLComputePipelineState> p, NSUInteger w, NSUInteger h, NSUInteger tgw,
         void (^bind)(id<MTLComputeCommandEncoder>)) {
    Ctx &c = ctx();
    id<MTLCommandBuffer> cb = [c.q commandBuffer];
    id<MTLComputeCommandEncoder> e = [cb computeCommandEncoder];
    [e setComputePipelineState:p];
    bind(e);
    [e dispatchThreads:MTLSizeMake(w, h, 1) threadsPerThreadgroup:MTLSizeMake(tgw, 1, 1)];
    [e endEncoding];
    [cb commit];
    [cb waitUntilCompleted];
}
}

bool metalAvailable() { return ctx().ok; }

std::vector<EquityResult> metalEquityBatch(const std::vector<EquityJob> &jobs) {
    std::vector<EquityResult> res(jobs.size(), EquityResult{0, 0, 0});
    if (jobs.empty() || !metalAvailable()) return res;
    @autoreleasepool {
        std::vector<GJob> gj(jobs.size());
        std::vector<uint16_t> combos;
        std::random_device rd;
        int maxTrials = 1;
        for (size_t n = 0; n < jobs.size(); ++n) {
            const EquityJob &j = jobs[n];
            unsigned long long known = bit(j.hero[0]) | bit(j.hero[1]);
            for (const Card &c : j.board) known |= bit(c);
            GJob &g = gj[n];
            g = GJob{};
            g.heroMask = bit(j.hero[0]) | bit(j.hero[1]);
            g.boardMask = known & ~g.heroMask;
            g.need = 5u - static_cast<uint32_t>(j.board.size());
            g.trials = static_cast<uint32_t>(std::max(0, j.trials));
            g.seed = j.seed ? j.seed : ((unsigned long long)rd() << 32) | rd();
            g.comboOff = static_cast<uint32_t>(combos.size());
            for (const auto &p : j.villainCombos) {
                if (bit(p.first) & known || bit(p.second) & known || p.first == p.second) continue;
                combos.push_back(static_cast<uint16_t>(cardIdx(p.first) | cardIdx(p.second) << 8));
            }
            if (combos.size() == g.comboOff) {
                for (int a = 0; a < 52; ++a)
                    for (int b = a + 1; b < 52; ++b)
                        if (!((1ULL << a | 1ULL << b) & known))
                            combos.push_back(static_cast<uint16_t>(a | b << 8));
            }
            g.comboCnt = static_cast<uint32_t>(combos.size()) - g.comboOff;
            maxTrials = std::max(maxTrials, j.trials);
        }
        // Threads per job: ~8 trials each, in whole 32-wide simdgroups.
        uint32_t X = std::min<uint32_t>(16384, std::max<uint32_t>(32, (maxTrials + 7) / 8));
        X = (X + 31) / 32 * 32;
        for (GJob &g : gj) g.slice = std::max<uint32_t>(1, (g.trials + X - 1) / X);

        Ctx &c = ctx();
        id<MTLBuffer> bj = [c.dev newBufferWithBytes:gj.data() length:gj.size() * sizeof(GJob) options:MTLResourceStorageModeShared];
        id<MTLBuffer> bc = [c.dev newBufferWithBytes:combos.data() length:combos.size() * 2 options:MTLResourceStorageModeShared];
        id<MTLBuffer> bo = [c.dev newBufferWithLength:jobs.size() * 8 options:MTLResourceStorageModeShared];
        std::memset([bo contents], 0, jobs.size() * 8);
        run(c.eq, X, jobs.size(), 32, ^(id<MTLComputeCommandEncoder> e) {
            [e setBuffer:bj offset:0 atIndex:0];
            [e setBuffer:bc offset:0 atIndex:1];
            [e setBuffer:bo offset:0 atIndex:2];
            [e setBytes:&X length:sizeof(X) atIndex:3];
        });
        const uint32_t *o = static_cast<const uint32_t *>([bo contents]);
        for (size_t n = 0; n < jobs.size(); ++n)
            res[n] = EquityResult{(int)o[2 * n], (int)o[2 * n + 1], (int)gj[n].trials};
    }
    return res;
}

std::vector<int> metalCompare(const std::vector<std::array<Card, 9>> &deals) {
    std::vector<int> out(deals.size(), 0);
    if (deals.empty() || !metalAvailable()) return out;
    @autoreleasepool {
        std::vector<uint8_t> in(deals.size() * 16, 0);
        for (size_t n = 0; n < deals.size(); ++n)
            for (int i = 0; i < 9; ++i) in[n * 16 + i] = static_cast<uint8_t>(cardIdx(deals[n][i]));
        Ctx &c = ctx();
        id<MTLBuffer> bi = [c.dev newBufferWithBytes:in.data() length:in.size() options:MTLResourceStorageModeShared];
        id<MTLBuffer> bo = [c.dev newBufferWithLength:deals.size() options:MTLResourceStorageModeShared];
        run(c.cmp, deals.size(), 1, 32, ^(id<MTLComputeCommandEncoder> e) {
            [e setBuffer:bi offset:0 atIndex:0];
            [e setBuffer:bo offset:0 atIndex:1];
        });
        const int8_t *o = static_cast<const int8_t *>([bo contents]);
        for (size_t n = 0; n < deals.size(); ++n) out[n] = o[n];
    }
    return out;
}
