// Level 6 periodic program search (simulated annealing).
// After a submission the pattern and its halo hold no matter, so the steady state is the emitter
// configuration alone: a cyclic program of k lines that returns to its start configuration and submits
// on its last tick yields one copy every k ticks.
// Usage: cycle <input> <index> <kmax> <iters> <seed>
// Prints the full program (prefix + periods) for the best k found, or NONE.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <random>
#include <string>
#include <vector>
using namespace std;
typedef unsigned long long u64;

static const int DR[6] = {0, 1, 1, 0, -1, -1}, DC[6] = {2, 1, -1, -2, -1, 1};
static const int NBR[6] = {0, 0, 1, 1, -1, -1}, NBC[6] = {2, -2, 1, -1, 1, -1};
const int MW = 8;

int R, H, Wd, CNT, RING, NREL, NP, NW;
vector<string> pat;
vector<pair<int, int>> ringc;
vector<char> fires, allowed;
vector<array<u64, MW>> line;
u64 Pm[MW], Hm[MW];

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
            ringc.push_back({i, c});
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
            if (y < 0 || y >= H || x < 0 || x >= Wd || g[y][x] != 'O' || pat[y][x] == 'M') continue;
            if (!rel.count({y, x})) rel[{y, x}] = rel.size();
        }
    NREL = rel.size();
    NW = (NREL + 63) / 64;
    memset(Pm, 0, sizeof Pm);
    memset(Hm, 0, sizeof Hm);
    for (int q = 0; q < NREL; q++) (q < NP ? Pm : Hm)[q >> 6] |= 1ULL << (q & 63);
    line.assign(6 * RING, {});
    fires.assign(6 * RING, 0);
    for (int e = 0; e < 6; e++)
        for (int p = 0; p < RING; p++) {
            int y = ringc[p].first + DR[e], x = ringc[p].second + DC[e];
            while (y >= 0 && y < H && x >= 0 && x < Wd && g[y][x] == 'O') {
                fires[e * RING + p] = 1;
                auto it = rel.find({y, x});
                if (it != rel.end()) line[e * RING + p][it->second >> 6] |= 1ULL << (it->second & 63);
                y += DR[e];
                x += DC[e];
            }
        }
    allowed.assign(6 * RING, 0);
    for (int e = 0; e < 6; e++)
        for (int p = 0; p < RING; p++)
            for (int d = -1; d <= 1; d++)
                if (fires[e * RING + (p + d + RING) % RING]) allowed[e * RING + p] = 1;
}

struct Cyc {
    int k;
    int p0[6];
    int a0[6];
    vector<array<char, 6>> ins;  // 0 '-', 1 F, 2 B, 3 T
};

// offset of ring position p relative to emitter e's corner, in [-3R, 3R)
int offs(int e, int p) { return ((p - e * R) % RING + RING + 3 * R) % RING - 3 * R; }

// Run lines from a given state; returns cost (0 = submission on the last line).
double runLines(const vector<array<char, 6>>& lines, int* pos, int* act, u64* M, int* copies) {
    int bad = 0, cp = 0;
    bool lastSub = false;
    for (size_t t = 0; t < lines.size(); t++) {
        u64 s0[MW] = {0}, s1[MW] = {0}, s2[MW] = {0};
        for (int e = 0; e < 6; e++) {
            int op = lines[t][e];
            if (op == 1) pos[e] = (pos[e] + 1) % RING;
            else if (op == 2) pos[e] = (pos[e] + RING - 1) % RING;
            else if (op == 3) act[e] ^= 1;
            if (!allowed[e * RING + pos[e]]) bad++;
            if (act[e] && fires[e * RING + pos[e]]) {
                const auto& L = line[e * RING + pos[e]];
                for (int q = 0; q < NW; q++) {
                    s2[q] |= s1[q] & L[q];
                    s1[q] |= s0[q] & L[q];
                    s0[q] |= L[q];
                }
            }
        }
        bool full = true, clean = true;
        for (int q = 0; q < NW; q++) {
            M[q] = (M[q] | (s1[q] & ~s2[q])) & ~s2[q];
            if ((M[q] & Pm[q]) != Pm[q]) full = false;
            if (M[q] & Hm[q]) clean = false;
        }
        lastSub = false;
        if (full && clean) {
            cp++;
            lastSub = true;
            for (int q = 0; q < NW; q++) M[q] &= ~Pm[q];
        }
    }
    if (copies) *copies += cp;
    if (bad) return 1000.0 * bad;
    if (lastSub) return 0;
    int miss = 0, halo = 0;
    for (int q = 0; q < NW; q++) {
        miss += __builtin_popcountll(Pm[q] & ~M[q]);
        halo += __builtin_popcountll(Hm[q] & M[q]);
    }
    return miss + 1.0 * halo + 0.5;
}

int offs(int e, int p);
vector<array<char, 6>> prefixLines(const Cyc& c) {
    int need[6], len = 0;
    for (int e = 0; e < 6; e++) {
        need[e] = abs(offs(e, c.p0[e])) + (c.a0[e] ? 1 : 0);
        len = max(len, need[e]);
    }
    vector<array<char, 6>> prog(len, {0, 0, 0, 0, 0, 0});
    for (int e = 0; e < 6; e++) {
        int d = offs(e, c.p0[e]);
        int start = len - need[e];
        for (int s = 0; s < abs(d); s++) prog[start + s][e] = d > 0 ? 1 : 2;
        if (c.a0[e]) prog[len - 1][e] = 3;
    }
    return prog;
}

// Steady period from empty relevant matter, plus the cold start (prefix + first period).
bool closed(const Cyc& c);
double evalCyc(const Cyc& c, int* copies = nullptr) {
    if (!closed(c)) return 5000;
    u64 M[MW] = {0};
    int pos[6], act[6], cp = 0;
    for (int e = 0; e < 6; e++) pos[e] = c.p0[e], act[e] = c.a0[e];
    double steady = runLines(c.ins, pos, act, M, &cp);
    if (steady >= 1000) return steady;
    vector<array<char, 6>> cold = prefixLines(c);
    cold.insert(cold.end(), c.ins.begin(), c.ins.end());
    u64 M2[MW] = {0};
    int cpos[6], cact[6] = {0};
    for (int e = 0; e < 6; e++) cpos[e] = e * R;
    double coldc = runLines(cold, cpos, cact, M2, copies);
    return steady + 0.7 * coldc;
}

// ticks needed to bring emitters from the initial corners to the cycle start, rotated to phase j
int prefixCost(const Cyc& c) {
    int m = 0;
    for (int e = 0; e < 6; e++) m = max(m, abs(offs(e, c.p0[e])) + (c.a0[e] ? 1 : 0));
    return m;
}

mt19937_64 rng;
double urand() { return (rng() >> 11) * (1.0 / 9007199254740992.0); }

Cyc randomCyc(int k) {
    Cyc c;
    c.k = k;
    c.ins.assign(k, {0, 0, 0, 0, 0, 0});
    for (int e = 0; e < 6; e++) {
        c.p0[e] = (e * R + (int)(rng() % (2 * R - 1)) - (R - 1) + RING) % RING;
        c.a0[e] = rng() & 1;
    }
    return c;
}

void mutate(Cyc& c) {
    int e = rng() % 6;
    int kind = rng() % 6;
    int k = c.k;
    if (kind == 0 && k >= 2) {  // swap two instructions of one emitter
        int t1 = rng() % k, t2 = rng() % k;
        swap(c.ins[t1][e], c.ins[t2][e]);
    } else if (kind == 1 && k >= 2) {  // insert/remove a cancelling pair
        int t1 = rng() % k, t2 = rng() % k;
        if (t1 == t2) return;
        char& x = c.ins[t1][e];
        char& y = c.ins[t2][e];
        if (x == 0 && y == 0) {
            int w = rng() % 3;
            if (w == 0) x = 1, y = 2;
            else if (w == 1) x = 2, y = 1;
            else x = 3, y = 3;
        } else if ((x == 1 && y == 2) || (x == 2 && y == 1) || (x == 3 && y == 3)) {
            x = 0, y = 0;
        }
    } else if (kind == 2) {  // shift start position
        c.p0[e] = (c.p0[e] + (rng() & 1 ? 1 : RING - 1)) % RING;
    } else if (kind == 3) {  // flip initial activity
        c.a0[e] ^= 1;
    } else if (kind == 4 && k >= 2) {  // move an instruction to a neighbouring tick
        int t1 = rng() % k, t2 = (t1 + 1) % k;
        swap(c.ins[t1][e], c.ins[t2][e]);
    } else {  // reverse one move and the opposite move of the same emitter elsewhere
        int t1 = rng() % k, t2 = rng() % k;
        char& x = c.ins[t1][e];
        char& y = c.ins[t2][e];
        if (t1 != t2 && ((x == 1 && y == 2) || (x == 2 && y == 1))) swap(x, y);
        else if (t1 != t2 && x == 1 && y == 1) { x = 2; y = 2; c.p0[e] = (c.p0[e] + 4) % RING; }
        else if (t1 != t2 && x == 2 && y == 2) { x = 1; y = 1; c.p0[e] = (c.p0[e] + RING - 4) % RING; }
    }
}

// Net displacement zero and even toggles per emitter.
bool closed(const Cyc& c) {
    for (int e = 0; e < 6; e++) {
        int d = 0, t = 0;
        for (int i = 0; i < c.k; i++) {
            if (c.ins[i][e] == 1) d++;
            if (c.ins[i][e] == 2) d--;
            if (c.ins[i][e] == 3) t++;
        }
        if (d % RING || t % 2) return false;
    }
    return true;
}

bool anneal(int k, long iters, Cyc& out) {
    Cyc cur = randomCyc(k);
    double cc = evalCyc(cur) + 0.02 * prefixCost(cur);
    Cyc best = cur;
    double bc = cc;
    double T0 = 2.0, T1 = 0.05;
    for (long it = 0; it < iters; it++) {
        double T = T0 * pow(T1 / T0, (double)it / iters);
        Cyc nx = cur;
        int nm = 1 + (rng() % 3 == 0) + (rng() % 6 == 0);
        for (int m = 0; m < nm; m++) mutate(nx);
        double nc = evalCyc(nx) + 0.02 * prefixCost(nx);
        if (nc <= cc || urand() < exp((cc - nc) / T)) {
            cur = nx;
            cc = nc;
            if (cc < bc) {
                bc = cc;
                best = cur;
            }
        }
    }
    out = best;
    return evalCyc(best) == 0;
}

string str(const array<char, 6>& a) {
    string s;
    for (int e = 0; e < 6; e++) {
        if (e) s += ' ';
        s += "-FBT"[(int)a[e]];
    }
    return s;
}

// Simulate a full program, return number of copies.
int simulate(const vector<array<char, 6>>& prog) {
    u64 M[MW] = {0};
    int pos[6], act[6] = {0};
    for (int e = 0; e < 6; e++) pos[e] = e * R;
    int cp = 0;
    for (auto& l : prog) {
        u64 s0[MW] = {0}, s1[MW] = {0}, s2[MW] = {0};
        for (int e = 0; e < 6; e++) {
            if (l[e] == 1) pos[e] = (pos[e] + 1) % RING;
            else if (l[e] == 2) pos[e] = (pos[e] + RING - 1) % RING;
            else if (l[e] == 3) act[e] ^= 1;
            if (act[e] && fires[e * RING + pos[e]]) {
                const auto& L = line[e * RING + pos[e]];
                for (int q = 0; q < NW; q++) {
                    s2[q] |= s1[q] & L[q];
                    s1[q] |= s0[q] & L[q];
                    s0[q] |= L[q];
                }
            }
        }
        bool full = true, clean = true;
        for (int q = 0; q < NW; q++) {
            M[q] = (M[q] | (s1[q] & ~s2[q])) & ~s2[q];
            if ((M[q] & Pm[q]) != Pm[q]) full = false;
            if (M[q] & Hm[q]) clean = false;
        }
        if (full && clean) {
            cp++;
            for (int q = 0; q < NW; q++) M[q] &= ~Pm[q];
        }
    }
    return cp;
}

// Build prefix (move inactive, toggle on at arrival) + periods, for every phase rotation; keep shortest.
vector<array<char, 6>> assemble(const Cyc& c) {
    vector<array<char, 6>> bestProg;
    for (int ph = 0; ph < c.k; ph++) {
        // rotated cycle starting at phase ph
        Cyc r = c;
        int pos[6], act[6];
        for (int e = 0; e < 6; e++) pos[e] = c.p0[e], act[e] = c.a0[e];
        for (int t = 0; t < ph; t++)
            for (int e = 0; e < 6; e++) {
                int op = c.ins[t][e];
                if (op == 1) pos[e] = (pos[e] + 1) % RING;
                else if (op == 2) pos[e] = (pos[e] + RING - 1) % RING;
                else if (op == 3) act[e] ^= 1;
            }
        for (int t = 0; t < c.k; t++) r.ins[t] = c.ins[(t + ph) % c.k];
        for (int e = 0; e < 6; e++) r.p0[e] = pos[e], r.a0[e] = act[e];
        vector<array<char, 6>> prog = prefixLines(r);
        int len = prog.size();
        int guard = 0;
        while (simulate(prog) < CNT && guard++ < CNT + 3)
            for (int t = 0; t < r.k; t++) prog.push_back(r.ins[t]);
        if (getenv("DBG")) fprintf(stderr, "phase %d prefix %d copies %d len %zu\n", ph, len, simulate(prog), prog.size());
        if (simulate(prog) < CNT) continue;
        // trim trailing lines that are not needed
        while (prog.size() > 1) {
            auto last = prog.back();
            prog.pop_back();
            if (simulate(prog) < CNT) {
                prog.push_back(last);
                break;
            }
        }
        if (bestProg.empty() || prog.size() < bestProg.size()) bestProg = prog;
    }
    return bestProg;
}

int main(int argc, char** argv) {
    ifstream in(argv[1]);
    int idx = atoi(argv[2]), kmax = atoi(argv[3]);
    long iters = atol(argv[4]);
    rng.seed(atoll(argv[5]));
    int restarts = argc > 6 ? atoi(argv[6]) : 4;
    int n;
    in >> n;
    for (int t = 0; t <= idx; t++) {
        int rows, cols;
        in >> R >> rows >> cols >> CNT;
        pat.assign(rows, "");
        for (auto& s : pat) in >> s;
    }
    build();
    vector<array<char, 6>> best;
    for (int k = 1; k <= kmax; k++) {
        for (int rs = 0; rs < restarts; rs++) {
            Cyc c;
            if (anneal(k, iters, c)) {
                auto prog = assemble(c);
                if (!prog.empty() && (best.empty() || prog.size() < best.size())) best = prog;
                fprintf(stderr, "k=%d valid, program %zu\n", k, prog.size());
            }
        }
        // stop once longer periods cannot win
        if (!best.empty() && (long)k * CNT >= (long)best.size()) break;
    }
    if (best.empty()) {
        puts("NONE");
        return 0;
    }
    for (auto& l : best) puts(str(l).c_str());
}
