// Level 6 beam search over full 6-emitter instruction lines.
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

double WH = 3.0, W1 = 1.0, W2 = 0.3, WL = 0.0, WTM = 0.0, WTS = 0.0;
int TAILN = 40;
vector<string> forced;
vector<string> prefixLines, prefixOut;  // compact ("FB-T--") and printable forms  // per tick: 6 chars, '?' = free, else the forced instruction

template <int NW> struct Solver {
    typedef BS<NW> B;
    vector<B> line;                // [e*RING+pos]
    vector<B> reach1, reach2;      // [(e*RING+pos)*2+act]
    vector<char> allowed;          // [e*RING+pos] position usable
    B Pm, Hm;
    struct Node {
        unsigned char pos[6];
        unsigned char act, copies;
        B M;
        int parent;
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
        // Positions: within the firing range of the emitter or one step beyond.
        allowed.assign(6 * RING, 0);
        for (int e = 0; e < 6; e++)
            for (int p = 0; p < RING; p++) {
                bool ok = false;
                for (int d = -1; d <= 1; d++)
                    if (G.fires[e * RING + (p + d + RING) % RING]) ok = true;
                allowed[e * RING + p] = ok;
            }
        cov.assign(6 * NP, -1);
        for (int e = 0; e < 6; e++)
            for (int q = 0; q < RING; q++)
                if (G.fires[e * RING + q])
                    for (int c : G.lineCells[e * RING + q])
                        if (c < NP) cov[e * NP + c] = q;
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
                        // inactive: toggle costs one tick but cannot move in that tick
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

    // lineDist[e][pos][act]: rail moves (+1 if a toggle is needed) to the nearest line that holds a
    // missing pattern cell, recomputed per parent (its missing set approximates the child's).
    vector<int> cov;  // [e*NP+x] ring position of emitter e covering pattern cell x (-1 none)
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

    double evaluate(const Node& n) {
        B miss;
        for (int k = 0; k < NW; k++) miss.w[k] = Pm.w[k] & ~n.M.w[k];
        int pm = NP - pc(miss);
        B hb;
        for (int k = 0; k < NW; k++) hb.w[k] = Hm.w[k] & n.M.w[k];
        int hm = pc(hb);
        // potential: missing cells that two emitters can hit within 1 / 2 ticks
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
        double tail = 0;
        int nmiss = NP - pm;
        if ((WTM > 0 || WTS > 0) && nmiss > 0 && nmiss <= TAILN) {
            int mx = 0, sm = 0;
            for (int k = 0; k < NW; k++) {
                u64 w = miss.w[k];
                while (w) {
                    int x = k * 64 + __builtin_ctzll(w);
                    w &= w - 1;
                    int a1 = 99, a2 = 99;
                    for (int e = 0; e < 6; e++) {
                        int q = cov[e * NP + x];
                        if (q < 0) continue;
                        int d = ringdist(n.pos[e], q) + (((n.act >> e) & 1) ? 0 : 1);
                        if (d < a1) a2 = a1, a1 = d;
                        else if (d < a2) a2 = d;
                    }
                    mx = max(mx, a2);
                    sm += a2;
                }
            }
            tail = WTM * mx + WTS * (double)sm / nmiss;
        }
        return n.copies * 1000.0 * NP + 4.0 * pm - WH * hm + W1 * p1 + W2 * p2 - WL * lg - tail;
    }

    struct Cand {
        double score;
        int parent;
        unsigned short ins;
    };

    vector<string> run(int width, u64 seed, int maxDepth) {
        rng.seed(seed);
        init();
        Node root;
        for (int e = 0; e < 6; e++) root.pos[e] = e * R;
        root.act = 0;
        root.copies = 0;
        memset(root.M.w, 0, sizeof root.M.w);
        root.parent = -1;
        root.ins = 0;
        root.score = 0;
        // replay a fixed prefix program (suffix re-optimisation)
        for (auto& s : prefixLines) {
            unsigned short ins = 0;
            for (int e = 0; e < 6; e++) {
                char ch = s[e];
                int op = ch == 'F' ? 1 : ch == 'B' ? 2 : ch == 'T' ? 3 : 0;
                ins |= op << (2 * e);
            }
            Node c = apply(root, ins);
            root = c;
        }
        root.parent = -1;
        if (root.copies >= CNT) return {""};
        levels.clear();
        levels.push_back({root});
        vector<Cand> cands;
        for (int depth = 0; depth < maxDepth; depth++) {
            auto& cur = levels.back();
            cands.clear();
            int found = -1;
            unsigned short foundIns = 0;
            for (int pi = 0; pi < (int)cur.size() && found < 0; pi++) {
                const Node& par = cur[pi];
                {
                    B miss;
                    for (int k = 0; k < NW; k++) miss.w[k] = Pm.w[k] & ~par.M.w[k];
                    if (pc(miss) == 0) miss = Pm;  // next copy starts from scratch
                    computeLineDist(miss);
                }
                // options per emitter
                int nopt[6];
                unsigned char opos[6][4], oact[6][4], oins[6][4];
                for (int e = 0; e < 6; e++) {
                    int k = 0;
                    int p = par.pos[e], a = (par.act >> e) & 1;
                    int f = (p + 1) % RING, b = (p - 1 + RING) % RING;
                    if (depth < (int)forced.size() && forced[depth][e] != '?') {
                        char fc = forced[depth][e];
                        if (fc == '-') { opos[e][k] = p; oact[e][k] = a; oins[e][k] = 0; }
                        else if (fc == 'F') { opos[e][k] = f; oact[e][k] = a; oins[e][k] = 1; }
                        else if (fc == 'B') { opos[e][k] = b; oact[e][k] = a; oins[e][k] = 2; }
                        else { opos[e][k] = p; oact[e][k] = !a; oins[e][k] = 3; }
                        nopt[e] = 1;
                        continue;
                    }
                    opos[e][k] = p; oact[e][k] = a; oins[e][k] = 0; k++;
                    if (allowed[e * RING + f]) { opos[e][k] = f; oact[e][k] = a; oins[e][k] = 1; k++; }
                    if (allowed[e * RING + b]) { opos[e][k] = b; oact[e][k] = a; oins[e][k] = 2; k++; }
                    opos[e][k] = p; oact[e][k] = !a; oins[e][k] = 3; k++;
                    nopt[e] = k;
                }
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
                    for (int q = 0; q < 6; q++) {
                        ins |= oins[q][choice[q]] << (2 * q);
                        child.pos[q] = opos[q][choice[q]];
                        act |= oact[q][choice[q]] << q;
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
                        child.copies++;
                        for (int k = 0; k < NW; k++) child.M.w[k] &= ~Pm.w[k];
                        if (child.copies >= CNT) {
                            found = pi;
                            foundIns = ins;
                            return;
                        }
                    }
                    double sc = evaluate(child) + (rng() & 1023) * 1e-4;
                    cands.push_back({sc, pi, ins});
                };
                for (choice[0] = 0; choice[0] < nopt[0]; choice[0]++) { stepLevel(0, choice[0]);
                for (choice[1] = 0; choice[1] < nopt[1]; choice[1]++) { stepLevel(1, choice[1]);
                for (choice[2] = 0; choice[2] < nopt[2]; choice[2]++) { stepLevel(2, choice[2]);
                for (choice[3] = 0; choice[3] < nopt[3]; choice[3]++) { stepLevel(3, choice[3]);
                for (choice[4] = 0; choice[4] < nopt[4]; choice[4]++) { stepLevel(4, choice[4]);
                for (choice[5] = 0; choice[5] < nopt[5]; choice[5]++) { stepLevel(5, choice[5]);
                    leaf();
                }}}}}}
            }
            if (found >= 0) {
                vector<string> prog;
                prog.push_back(insStr(foundIns));
                int idx = found;
                for (int d = (int)levels.size() - 1; d > 0; d--) {
                    prog.push_back(insStr(levels[d][idx].ins));
                    idx = levels[d][idx].parent;
                }
                reverse(prog.begin(), prog.end());
                prog.insert(prog.begin(), prefixOut.begin(), prefixOut.end());
                return prog;
            }
            // select top candidates, materialize, dedup
            if (cands.empty()) return {};
            size_t keep = min(cands.size(), (size_t)width * 3);
            nth_element(cands.begin(), cands.begin() + keep - 1, cands.end(),
                        [](const Cand& a, const Cand& b) { return a.score > b.score; });
            cands.resize(keep);
            sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) { return a.score > b.score; });
            vector<Node> next;
            unordered_set<u64> seen;
            for (auto& cd : cands) {
                if ((int)next.size() >= width) break;
                Node ch = apply(cur[cd.parent], cd.ins);
                ch.parent = cd.parent;
                ch.ins = cd.ins;
                ch.score = cd.score;
                u64 h = hashNode(ch);
                if (!seen.insert(h).second) continue;
                next.push_back(ch);
            }
            levels.push_back(move(next));
        }
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

int main(int argc, char** argv) {
    if (argc < 5) {
        fprintf(stderr, "usage\n");
        return 1;
    }
    ifstream in(argv[1]);
    int idx = atoi(argv[2]), width = atoi(argv[3]);
    u64 seed = atoll(argv[4]);
    if (argc > 5) WH = atof(argv[5]);
    if (argc > 6) W1 = atof(argv[6]);
    if (argc > 7) W2 = atof(argv[7]);
    if (argc > 8) WL = atof(argv[8]);
    int maxDepth = argc > 9 ? atoi(argv[9]) : 1000;
    if (getenv("PREFIX")) {
        ifstream ps(getenv("PREFIX"));
        string a, b, c, d, e, f;
        while (ps >> a >> b >> c >> d >> e >> f) {
            prefixLines.push_back(a + b + c + d + e + f);
            prefixOut.push_back(a + " " + b + " " + c + " " + d + " " + e + " " + f);
        }
    }
    if (getenv("WTM")) WTM = atof(getenv("WTM"));
    if (getenv("WTS")) WTS = atof(getenv("WTS"));
    if (getenv("TAILN")) TAILN = atoi(getenv("TAILN"));
    if (argc > 10) {
        ifstream fs(argv[10]);
        string s;
        while (fs >> s) forced.push_back(s);
    }
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
    switch (nw) {
#define C(K) case K: { Solver<K> s; prog = s.run(width, seed, maxDepth); break; }
        C(1) C(2) C(3) C(4) C(5) C(6) C(7) C(8)
#undef C
        default: fprintf(stderr, "too many cells %d\n", NREL); return 1;
    }
    if (prog.empty()) {
        puts("NONE");
        return 0;
    }
    for (auto& s : prog) puts(s.c_str());
}
