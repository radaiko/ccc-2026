// Return-constrained beam (retbeam): paths from a start configuration with empty matter that submit NC copies,
// the last one exactly at a target configuration (start == target -> closed cycle).
// Usage: beam <input file> <pattern index> <width> <seed> [wh w1 w2 wl]
// Prints the program (one line per tick) on stdout, "NONE" if not found.
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <functional>
#include <map>
#include <random>
#include <string>
#include <unordered_set>
#include <vector>
using namespace std;
typedef unsigned long long u64;

static const int DR[6] = {0, 1, 1, 0, -1, -1}, DC[6] = {2, 1, -1, -2, -1, 1};
static const int NBR[6] = {0, 0, 1, 1, -1, -1}, NBC[6] = {2, -2, 1, -1, 1, -1};

int R, H, Wd, CNT, RING;
vector<string> pat;
int NREL, NP;  // relevant cells: first NP are pattern cells, then halo

template <int NW> struct BS {
    u64 w[NW];
};

struct Geo {
    vector<pair<int, int>> ring;
    vector<vector<int>> lineCells;  // [e*RING+pos] -> relevant cell indices
    vector<char> fires;             // [e*RING+pos] -> beam hits any interior cell
};
Geo G;

int ringdist(int a, int b) {
    int d = abs(a - b);
    return min(d, RING - d);
}

void build() {
    H = 2 * R + 1;
    Wd = 4 * R + 1;
    vector<string> g(H, string(Wd, ' '));
    for (int i = 0; i < H; i++) {
        int k = abs(i - R), n = 2 * R + 1 - k;
        for (int j = 0; j < n; j++) g[i][k + 2 * j] = (k == R || j == 0 || j == n - 1) ? '*' : 'O';
    }
    int i = R, c = 0;
    int sd[6][2] = {{-1, 1}, {0, 2}, {1, 1}, {1, -1}, {0, -2}, {-1, -1}};
    for (int s = 0; s < 6; s++)
        for (int t = 0; t < R; t++) {
            G.ring.push_back({i, c});
            i += sd[s][0];
            c += sd[s][1];
        }
    RING = 6 * R;
    map<pair<int, int>, int> rel;
    vector<pair<int, int>> pc;
    for (int y = 0; y < H; y++)
        for (int x = 0; x < Wd; x++)
            if (pat[y][x] == 'M') pc.push_back({y, x});
    for (auto& p : pc) rel[p] = rel.size();
    NP = pc.size();
    for (auto& p : pc)
        for (int d = 0; d < 6; d++) {
            int y = p.first + NBR[d], x = p.second + NBC[d];
            if (y < 0 || y >= H || x < 0 || x >= Wd || g[y][x] != 'O') continue;
            if (pat[y][x] == 'M') continue;
            if (!rel.count({y, x})) rel[{y, x}] = rel.size();
        }
    NREL = rel.size();
    G.lineCells.assign(6 * RING, {});
    G.fires.assign(6 * RING, 0);
    for (int e = 0; e < 6; e++)
        for (int p = 0; p < RING; p++) {
            int y = G.ring[p].first + DR[e], x = G.ring[p].second + DC[e];
            while (y >= 0 && y < H && x >= 0 && x < Wd && g[y][x] == 'O') {
                G.fires[e * RING + p] = 1;
                auto it = rel.find({y, x});
                if (it != rel.end()) G.lineCells[e * RING + p].push_back(it->second);
                y += DR[e];
                x += DC[e];
            }
        }
}

double WH = 3.0, W1 = 1.0, W2 = 0.3, WL = 0.5, WR = 1.0;
int K = 6, NC = 1, PERPID = 0, FREE = 0, GOAL = 0;
struct Pair {
    unsigned char spos[6], sact, tpos[6], tact;
};
vector<Pair> pairs;

template <int NW> struct Solver {
    typedef BS<NW> B;
    vector<B> line;
    vector<B> reach1, reach2;
    vector<char> allowed;
    B Pm, Hm;
    struct Node {
        unsigned char pos[6];
        unsigned char act, copies;
        B M;
        int parent, pid;
        unsigned short ins;
        double score;
    };
    static int pc(const B& b) {
        int s = 0;
        for (int k = 0; k < NW; k++) s += __builtin_popcountll(b.w[k]);
        return s;
    }
    void init() {
        line.assign(6 * RING, B());
        for (auto& b : line) memset(b.w, 0, sizeof b.w);
        memset(Pm.w, 0, sizeof Pm.w);
        memset(Hm.w, 0, sizeof Hm.w);
        for (int i = 0; i < NREL; i++) (i < NP ? Pm : Hm).w[i >> 6] |= 1ULL << (i & 63);
        for (int k = 0; k < 6 * RING; k++)
            for (int c : G.lineCells[k]) line[k].w[c >> 6] |= 1ULL << (c & 63);
        allowed.assign(6 * RING, 0);
        for (int e = 0; e < 6; e++)
            for (int p = 0; p < RING; p++) {
                bool ok = false;
                for (int d = -1; d <= 1; d++)
                    if (G.fires[e * RING + (p + d + RING) % RING]) ok = true;
                allowed[e * RING + p] = ok;
            }
        // positions on the shorter arc between start and target (+-1) are usable too
        for (auto& pr : pairs)
            for (int e = 0; e < 6; e++) {
                int a = pr.spos[e], b = pr.tpos[e];
                int d = (b - a + RING) % RING;
                int step = d <= RING - d ? 1 : -1, n = min(d, RING - d);
                for (int s = -1; s <= n + 1; s++) allowed[e * RING + ((a + step * s) % RING + RING) % RING] = 1;
            }
        reach1.assign(6 * RING * 2, B());
        reach2.assign(6 * RING * 2, B());
        for (int e = 0; e < 6; e++)
            for (int p = 0; p < RING; p++)
                for (int a = 0; a < 2; a++) {
                    B r1, r2;
                    memset(r1.w, 0, sizeof r1.w);
                    memset(r2.w, 0, sizeof r2.w);
                    for (int d = -2; d <= 2; d++) {
                        int q = (p + d + RING) % RING;
                        int cost = abs(d) + (a ? 0 : 1);
                        for (int k = 0; k < NW; k++) {
                            if (cost <= 1) r1.w[k] |= line[e * RING + q].w[k];
                            if (cost <= 2) r2.w[k] |= line[e * RING + q].w[k];
                        }
                    }
                    reach1[(e * RING + p) * 2 + a] = r1;
                    reach2[(e * RING + p) * 2 + a] = r2;
                }
    }
    vector<vector<Node>> levels;
    mt19937_64 rng;
    struct Rec { int depth, pi; unsigned short ins; int pid; };
    map<u64, Rec> anchors;
    void printAnchors() {
        vector<pair<int, u64>> order;
        for (auto& kv : anchors) order.push_back({kv.second.depth, kv.first});
        sort(order.begin(), order.end());
        for (auto& o : order) {
            Rec& r = anchors[o.second];
            u64 key = o.second;
            int pos[6];
            for (int q = 5; q >= 0; q--) pos[q] = key & 255, key >>= 8;
            vector<string> prog;
            prog.push_back(insStr(r.ins));
            int idx = r.pi;
            for (int d = r.depth - 1; d > 0; d--) {
                prog.push_back(insStr(levels[d][idx].ins));
                idx = levels[d][idx].parent;
            }
            reverse(prog.begin(), prog.end());
            printf("ANCHOR %d %d", r.pid, r.depth);
            for (int q = 0; q < 6; q++) printf(" %d", pos[q]);
            printf(" %d\n", (int)key);
            for (auto& l : prog) puts(l.c_str());
        }
    }
    vector<int> lineDist;
    void computeLineDist(const B& miss) {
        lineDist.assign(6 * RING * 2, 99);
        for (int e = 0; e < 6; e++) {
            vector<char> useful(RING, 0);
            for (int p = 0; p < RING; p++) {
                const B& L = line[e * RING + p];
                for (int k = 0; k < NW; k++)
                    if (L.w[k] & miss.w[k]) useful[p] = 1;
            }
            for (int p = 0; p < RING; p++) {
                int best = 99;
                for (int q = 0; q < RING; q++)
                    if (useful[q]) best = min(best, ringdist(p, q));
                lineDist[(e * RING + p) * 2 + 1] = best;
                lineDist[(e * RING + p) * 2 + 0] = best + 1;
            }
        }
    }
    // ticks needed to reach the target configuration (moves and toggles exclude each other per emitter)
    static int needE(const Pair& pr, int e, int pos, int act) {
        return ringdist(pos, pr.tpos[e]) + (((act >> e) & 1) != ((pr.tact >> e) & 1));
    }
    // per pair: what the target configuration's own final tick does: T2 (made M), T3 (cleared)
    vector<B> gT2, gT3;
    vector<char> pairOk;
    void initGoal() {
        gT2.assign(pairs.size(), B());
        gT3.assign(pairs.size(), B());
        pairOk.assign(pairs.size(), 1);
        for (size_t i = 0; i < pairs.size(); i++) {
            B s0, s1, s2;
            memset(s0.w, 0, sizeof s0.w);
            memset(s1.w, 0, sizeof s1.w);
            memset(s2.w, 0, sizeof s2.w);
            for (int e = 0; e < 6; e++)
                if (((pairs[i].tact >> e) & 1) && G.fires[e * RING + pairs[i].tpos[e]]) {
                    const B& L = line[e * RING + pairs[i].tpos[e]];
                    for (int k = 0; k < NW; k++) {
                        s2.w[k] |= s1.w[k] & L.w[k];
                        s1.w[k] |= s0.w[k] & L.w[k];
                        s0.w[k] |= L.w[k];
                    }
                }
            for (int k = 0; k < NW; k++) {
                gT2[i].w[k] = s1.w[k] & ~s2.w[k];
                gT3[i].w[k] = s2.w[k];
                if ((gT3[i].w[k] & Pm.w[k]) || (gT2[i].w[k] & Hm.w[k])) pairOk[i] = 0;
            }
            if (!GOAL) {
                memset(gT2[i].w, 0, sizeof gT2[i].w);
                memset(gT3[i].w, 0, sizeof gT3[i].w);
            }
        }
    }
    double evaluate(const Node& n, int retSum) {
        B miss;
        bool last = n.copies + 1 == NC && !FREE;
        const B& T2 = gT2[n.pid];
        const B& T3 = gT3[n.pid];
        for (int k = 0; k < NW; k++) miss.w[k] = Pm.w[k] & ~n.M.w[k] & ~(last ? T2.w[k] : 0);
        int pm = NP - pc(miss);
        B hb;
        for (int k = 0; k < NW; k++) hb.w[k] = Hm.w[k] & n.M.w[k] & ~(last ? T3.w[k] : 0);
        int hm = pc(hb);
        B o1, t1, o2, t2;
        memset(o1.w, 0, sizeof o1.w);
        memset(t1.w, 0, sizeof t1.w);
        memset(o2.w, 0, sizeof o2.w);
        memset(t2.w, 0, sizeof t2.w);
        double lg = 0;
        for (int e = 0; e < 6; e++) {
            int a = (n.act >> e) & 1;
            const B& r1 = reach1[(e * RING + n.pos[e]) * 2 + a];
            const B& r2 = reach2[(e * RING + n.pos[e]) * 2 + a];
            for (int k = 0; k < NW; k++) {
                u64 m1 = r1.w[k] & miss.w[k], m2 = r2.w[k] & miss.w[k];
                t1.w[k] |= o1.w[k] & m1;
                o1.w[k] |= m1;
                t2.w[k] |= o2.w[k] & m2;
                o2.w[k] |= m2;
            }
        }
        int p1 = pc(t1), p2 = pc(t2);
        for (int e = 0; e < 6; e++) lg += lineDist[(e * RING + n.pos[e]) * 2 + ((n.act >> e) & 1)];
        return n.copies * 1000.0 * NP + 4.0 * pm - WH * hm + W1 * p1 + W2 * p2 - WL * lg - WR * retSum;
    }
    struct Cand {
        double score;
        int parent;
        unsigned short ins;
    };
    // returns program lines; outPid gets the pair index
    vector<string> run(int width, u64 seed, int& outPid) {
        rng.seed(seed);
        init();
        levels.clear();
        initGoal();
        vector<Node> roots;
        int nbad = 0;
        for (int i = 0; i < (int)pairs.size(); i++) {
            if (!pairOk[i] && !FREE) { nbad++; continue; }
            Node root;
            memcpy(root.pos, pairs[i].spos, 6);
            root.act = pairs[i].sact;
            root.copies = 0;
            memset(root.M.w, 0, sizeof root.M.w);
            root.parent = -1;
            root.pid = i;
            root.ins = 0;
            root.score = 0;
            roots.push_back(root);
        }
        if (nbad) fprintf(stderr, "%d of %d targets can never end a copy\n", nbad, (int)pairs.size());
        levels.push_back(roots);
        vector<Cand> cands;
        for (int depth = 0; depth < K; depth++) {
            auto& cur = levels.back();
            cands.clear();
            int found = -1;
            unsigned short foundIns = 0;
            int rem = K - depth - 1;  // ticks left after this one
            for (int pi = 0; pi < (int)cur.size() && found < 0; pi++) {
                const Node& par = cur[pi];
                const Pair& pr = pairs[par.pid];
                {
                    B miss;
                    bool last = par.copies + 1 == NC && !FREE;
                    for (int k = 0; k < NW; k++)
                        miss.w[k] = Pm.w[k] & ~par.M.w[k] & ~(last ? gT2[par.pid].w[k] : 0);
                    if (pc(miss) == 0) miss = Pm;
                    computeLineDist(miss);
                }
                int nopt[6];
                unsigned char opos[6][4], oact[6][4], oins[6][4];
                int oneed[6][4];
                bool dead = false;
                for (int e = 0; e < 6; e++) {
                    int k = 0;
                    int p = par.pos[e], a = (par.act >> e) & 1;
                    int f = (p + 1) % RING, b = (p - 1 + RING) % RING;
                    auto add = [&](int np, int na, int in) {
                        int nd = FREE ? 0 : ringdist(np, pr.tpos[e]) + (na != ((pr.tact >> e) & 1));
                        if (nd > rem) return;
                        opos[e][k] = np; oact[e][k] = na; oins[e][k] = in; oneed[e][k] = nd; k++;
                    };
                    add(p, a, 0);
                    if (allowed[e * RING + f]) add(f, a, 1);
                    if (allowed[e * RING + b]) add(b, a, 2);
                    add(p, !a, 3);
                    nopt[e] = k;
                    if (!k) dead = true;
                }
                if (dead) continue;
                B s0[7], s1[7], s2[7];
                memset(s0[0].w, 0, sizeof s0[0].w);
                memset(s1[0].w, 0, sizeof s1[0].w);
                memset(s2[0].w, 0, sizeof s2[0].w);
                int choice[6];
                Node child;
                auto stepLevel = [&](int e, int o) {
                    if (oact[e][o] && G.fires[e * RING + opos[e][o]]) {
                        const B& L = line[e * RING + opos[e][o]];
                        for (int k = 0; k < NW; k++) {
                            s2[e + 1].w[k] = s2[e].w[k] | (s1[e].w[k] & L.w[k]);
                            s1[e + 1].w[k] = s1[e].w[k] | (s0[e].w[k] & L.w[k]);
                            s0[e + 1].w[k] = s0[e].w[k] | L.w[k];
                        }
                    } else {
                        s0[e + 1] = s0[e];
                        s1[e + 1] = s1[e];
                        s2[e + 1] = s2[e];
                    }
                };
                auto leaf = [&]() {
                    unsigned short ins = 0;
                    unsigned char act = 0;
                    int retSum = 0;
                    for (int q = 0; q < 6; q++) {
                        ins |= oins[q][choice[q]] << (2 * q);
                        child.pos[q] = opos[q][choice[q]];
                        act |= oact[q][choice[q]] << q;
                        retSum += oneed[q][choice[q]];
                    }
                    child.act = act;
                    child.copies = par.copies;
                    bool full = true, clean = true;
                    for (int k = 0; k < NW; k++) {
                        u64 two = s1[6].w[k] & ~s2[6].w[k];
                        u64 m = (par.M.w[k] | two) & ~s2[6].w[k];
                        child.M.w[k] = m;
                        if ((m & Pm.w[k]) != Pm.w[k]) full = false;
                        if (m & Hm.w[k]) clean = false;
                    }
                    if (full && clean) {
                        if (child.copies + 1 == NC) {
                            if (FREE) {
                                u64 key = act;
                                for (int q = 0; q < 6; q++) key = key * 256 + child.pos[q];
                                if (!anchors.count(key)) anchors[key] = {depth + 1, pi, ins, par.pid};
                                return;
                            }
                            if (retSum == 0) {
                                found = pi;
                                foundIns = ins;
                            }
                            return;  // last copy must be at the target
                        }
                        child.copies++;
                        for (int k = 0; k < NW; k++) child.M.w[k] &= ~Pm.w[k];
                    }
                    if (rem == 0) return;
                    double sc = evaluate(child, retSum) + (rng() & 1023) * 1e-4;
                    cands.push_back({sc, pi, ins});
                };
                for (choice[0] = 0; choice[0] < nopt[0] && found < 0; choice[0]++) { stepLevel(0, choice[0]);
                for (choice[1] = 0; choice[1] < nopt[1] && found < 0; choice[1]++) { stepLevel(1, choice[1]);
                for (choice[2] = 0; choice[2] < nopt[2] && found < 0; choice[2]++) { stepLevel(2, choice[2]);
                for (choice[3] = 0; choice[3] < nopt[3] && found < 0; choice[3]++) { stepLevel(3, choice[3]);
                for (choice[4] = 0; choice[4] < nopt[4] && found < 0; choice[4]++) { stepLevel(4, choice[4]);
                for (choice[5] = 0; choice[5] < nopt[5] && found < 0; choice[5]++) { stepLevel(5, choice[5]);
                    leaf();
                }}}}}}
            }
            if (found >= 0) {
                vector<string> prog;
                prog.push_back(insStr(foundIns));
                int idx = found;
                outPid = cur[found].pid;
                for (int d = (int)levels.size() - 1; d > 0; d--) {
                    prog.push_back(insStr(levels[d][idx].ins));
                    idx = levels[d][idx].parent;
                }
                reverse(prog.begin(), prog.end());
                return prog;
            }
            if (cands.empty()) break;
            size_t keep = min(cands.size(), (size_t)width * 3);
            nth_element(cands.begin(), cands.begin() + keep - 1, cands.end(),
                        [](const Cand& a, const Cand& b) { return a.score > b.score; });
            cands.resize(keep);
            sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) { return a.score > b.score; });
            vector<Node> next;
            unordered_set<u64> seen;
            vector<int> perPid(pairs.size(), 0);
            for (auto& cd : cands) {
                if ((int)next.size() >= width) break;
                int pid = cur[cd.parent].pid;
                if (PERPID && perPid[pid] >= PERPID) continue;
                Node ch = apply(cur[cd.parent], cd.ins);
                ch.parent = cd.parent;
                ch.ins = cd.ins;
                ch.score = cd.score;
                u64 h = hashNode(ch);
                if (!seen.insert(h).second) continue;
                perPid[pid]++;
                next.push_back(ch);
            }
            levels.push_back(std::move(next));
        }
        if (FREE) printAnchors();
        return {};
    }
    static string insStr(unsigned short ins) {
        string s;
        for (int e = 0; e < 6; e++) {
            if (e) s += ' ';
            s += "-FBT"[(ins >> (2 * e)) & 3];
        }
        return s;
    }
    u64 hashNode(const Node& n) {
        u64 h = 1469598103934665603ULL;
        auto mix = [&](u64 v) { h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2); h *= 1099511628211ULL; };
        for (int e = 0; e < 6; e++) mix(n.pos[e]);
        mix(n.act);
        mix(n.copies);
        mix(n.pid);
        for (int k = 0; k < NW; k++) mix(n.M.w[k]);
        return h;
    }
    Node apply(const Node& par, unsigned short ins) {
        Node c = par;
        B s0, s1, s2;
        memset(s0.w, 0, sizeof s0.w);
        memset(s1.w, 0, sizeof s1.w);
        memset(s2.w, 0, sizeof s2.w);
        for (int e = 0; e < 6; e++) {
            int op = (ins >> (2 * e)) & 3;
            if (op == 1) c.pos[e] = (c.pos[e] + 1) % RING;
            else if (op == 2) c.pos[e] = (c.pos[e] + RING - 1) % RING;
            else if (op == 3) c.act ^= 1 << e;
            if (((c.act >> e) & 1) && G.fires[e * RING + c.pos[e]]) {
                const B& L = line[e * RING + c.pos[e]];
                for (int k = 0; k < NW; k++) {
                    s2.w[k] |= s1.w[k] & L.w[k];
                    s1.w[k] |= s0.w[k] & L.w[k];
                    s0.w[k] |= L.w[k];
                }
            }
        }
        bool full = true, clean = true;
        for (int k = 0; k < NW; k++) {
            u64 two = s1.w[k] & ~s2.w[k];
            c.M.w[k] = (c.M.w[k] | two) & ~s2.w[k];
            if ((c.M.w[k] & Pm.w[k]) != Pm.w[k]) full = false;
            if (c.M.w[k] & Hm.w[k]) clean = false;
        }
        if (full && clean) {
            c.copies++;
            for (int k = 0; k < NW; k++) c.M.w[k] &= ~Pm.w[k];
        }
        return c;
    }
};

// usage: retbeam <input> <idx> <width> <seed> <K> <NC> <pairsFile> [WH W1 W2 WL WR]
// pairs file: one line per (start, target): sp0..sp5 sactmask tp0..tp5 tactmask
// output: "FOUND <pid> <len>" then the lines, or "NONE"
int main(int argc, char** argv) {
    if (argc < 8) {
        fprintf(stderr, "usage\n");
        return 1;
    }
    ifstream in(argv[1]);
    int idx = atoi(argv[2]), width = atoi(argv[3]);
    u64 seed = atoll(argv[4]);
    K = atoi(argv[5]);
    NC = atoi(argv[6]);
    {
        ifstream ps(argv[7]);
        int v[14];
        while (true) {
            bool ok = true;
            for (int i = 0; i < 14 && ok; i++)
                if (!(ps >> v[i])) ok = false;
            if (!ok) break;
            Pair p;
            for (int e = 0; e < 6; e++) p.spos[e] = v[e], p.tpos[e] = v[7 + e];
            p.sact = v[6];
            p.tact = v[13];
            pairs.push_back(p);
        }
    }
    if (argc > 8) WH = atof(argv[8]);
    if (argc > 9) W1 = atof(argv[9]);
    if (argc > 10) W2 = atof(argv[10]);
    if (argc > 11) WL = atof(argv[11]);
    if (argc > 12) WR = atof(argv[12]);
    if (getenv("PERPID")) PERPID = atoi(getenv("PERPID"));
    if (getenv("FREE")) FREE = atoi(getenv("FREE"));
    if (getenv("GOAL")) GOAL = atoi(getenv("GOAL"));
    int n;
    in >> n;
    for (int t = 0; t <= idx; t++) {
        int rows, cols;
        in >> R >> rows >> cols >> CNT;
        pat.assign(rows, "");
        for (auto& s : pat) in >> s;
    }
    build();
    int nw = (NREL + 63) / 64;
    vector<string> prog;
    int pid = -1;
    switch (nw) {
#define C(KK) case KK: { Solver<KK> s; prog = s.run(width, seed, pid); break; }
        C(1) C(2) C(3) C(4) C(5) C(6) C(7) C(8)
#undef C
        default: fprintf(stderr, "too many cells %d\n", NREL); return 1;
    }
    if (prog.empty()) {
        puts("NONE");
        return 0;
    }
    printf("FOUND %d %d\n", pid, (int)prog.size());
    for (auto& s : prog) puts(s.c_str());
}
