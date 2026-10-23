// Level 6 periodic program search (simulated annealing).
// After a submission the pattern and its halo hold no matter, so the steady state is the emitter
// configuration alone. Program = free prefix (m lines) + a closed cycle (k lines) repeated.
// Valid iff (a) the cycle run from its start configuration with empty relevant matter submits on its
// last line, and (b) the prefix alone, or prefix + one cycle, submits on its last line.
// Usage: cycle <input> <index> <kmax> <iters> <seed> [restarts] [bound]
#include <algorithm>
#include <array>
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
typedef array<char, 6> Line;  // 0 '-', 1 F, 2 B, 3 T

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

struct State {
    int pos[6], act[6];
    u64 M[MW];
    int copies;
    bool lastSub;
    int bad;
};

void initState(State& s) {
    for (int e = 0; e < 6; e++) s.pos[e] = e * R, s.act[e] = 0;
    memset(s.M, 0, sizeof s.M);
    s.copies = 0;
    s.lastSub = false;
    s.bad = 0;
}

inline void tick(State& s, const Line& l) {
    u64 s0[MW] = {0}, s1[MW] = {0}, s2[MW] = {0};
    for (int e = 0; e < 6; e++) {
        int op = l[e];
        if (op == 1) s.pos[e] = s.pos[e] + 1 == RING ? 0 : s.pos[e] + 1;
        else if (op == 2) s.pos[e] = s.pos[e] == 0 ? RING - 1 : s.pos[e] - 1;
        else if (op == 3) s.act[e] ^= 1;
        if (!allowed[e * RING + s.pos[e]]) s.bad++;
        if (s.act[e] && fires[e * RING + s.pos[e]]) {
            const auto& L = line[e * RING + s.pos[e]];
            for (int q = 0; q < NW; q++) {
                s2[q] |= s1[q] & L[q];
                s1[q] |= s0[q] & L[q];
                s0[q] |= L[q];
            }
        }
    }
    bool full = true, clean = true;
    for (int q = 0; q < NW; q++) {
        s.M[q] = (s.M[q] | (s1[q] & ~s2[q])) & ~s2[q];
        if ((s.M[q] & Pm[q]) != Pm[q]) full = false;
        if (s.M[q] & Hm[q]) clean = false;
    }
    s.lastSub = false;
    if (full && clean) {
        s.copies++;
        s.lastSub = true;
        for (int q = 0; q < NW; q++) s.M[q] &= ~Pm[q];
    }
}

double missCost(const State& s) {
    if (s.lastSub) return 0;
    int miss = 0, halo = 0;
    for (int q = 0; q < NW; q++) {
        miss += __builtin_popcountll(Pm[q] & ~s.M[q]);
        halo += __builtin_popcountll(Hm[q] & s.M[q]);
    }
    return miss + halo + 0.5;
}

struct Prog {
    vector<Line> pre, cyc;
};

bool closed(const vector<Line>& cyc) {
    for (int e = 0; e < 6; e++) {
        int d = 0, t = 0;
        for (auto& l : cyc) {
            if (l[e] == 1) d++;
            if (l[e] == 2) d--;
            if (l[e] == 3) t++;
        }
        if (d || t % 2) return false;
    }
    return true;
}

// Invalidity cost (0 = valid); *length = program length for CNT copies when valid.
double evaluate(const Prog& p, int* length) {
    State s;
    initState(s);
    for (auto& l : p.pre) tick(s, l);
    double coldA = missCost(s);
    int copiesA = s.copies;
    State start = s;
    for (auto& l : p.cyc) tick(s, l);
    double coldB = missCost(s);
    int copiesB = s.copies;
    if (s.bad) return 1000.0 * s.bad;
    State st = start;
    memset(st.M, 0, sizeof st.M);
    st.copies = 0;
    for (auto& l : p.cyc) tick(st, l);
    double steady = missCost(st);
    int per = max(1, st.copies);
    int m = p.pre.size(), k = p.cyc.size();
    int lenA = 1 << 29, lenB = 1 << 29;
    if (coldA == 0) lenA = m + max(0, (CNT - copiesA + per - 1) / per) * k;
    if (coldB == 0) lenB = m + k + max(0, (CNT - copiesB + per - 1) / per) * k;
    *length = min(lenA, lenB);
    return steady + min(coldA, coldB);
}

mt19937_64 rng;
double urand() { return (rng() >> 11) * (1.0 / 9007199254740992.0); }

// Edit that keeps the cycle closed (net displacement 0, even toggles per emitter).
void mutateCycle(vector<Line>& c) {
    int k = c.size();
    int e = rng() % 6;
    int kind = rng() % 3;
    int t1 = rng() % k, t2 = rng() % k;
    char& x = c[t1][e];
    char& y = c[t2][e];
    if (kind == 0 || t1 == t2) {
        swap(x, y);
    } else if (kind == 1) {
        if (x == 0 && y == 0) {
            int w = rng() % 3;
            if (w == 0) x = 1, y = 2;
            else if (w == 1) x = 2, y = 1;
            else x = 3, y = 3;
        } else if ((x == 1 && y == 2) || (x == 2 && y == 1) || (x == 3 && y == 3)) {
            x = 0, y = 0;
        } else {
            swap(x, y);
        }
    } else {
        swap(c[t1][e], c[(t1 + 1) % k][e]);
    }
}

// Free edit of the prefix (it determines the cycle's start configuration).
void mutatePrefix(vector<Line>& p) {
    int m = p.size();
    int e = rng() % 6;
    int kind = rng() % 4;
    int t1 = rng() % m;
    if (kind == 0) {
        p[t1][e] = rng() % 4;
    } else if (kind == 1) {
        swap(p[t1][e], p[rng() % m][e]);
    } else if (kind == 2) {
        swap(p[t1][e], p[(t1 + 1) % m][e]);
    } else {
        if (p[t1][e] == 1) p[t1][e] = 2;
        else if (p[t1][e] == 2) p[t1][e] = 1;
        else p[t1][e] = rng() & 1 ? 1 : 2;
    }
}

Prog randomProg(int k, int m) {
    Prog p;
    p.cyc.assign(k, {0, 0, 0, 0, 0, 0});
    p.pre.assign(m, {0, 0, 0, 0, 0, 0});
    for (int e = 0; e < 6; e++) {
        int act = rng() & 1;
        int maxd = max(0, min(R - 1, m - act));
        int d = maxd ? (int)(rng() % (2 * maxd + 1)) - maxd : 0;
        int need = abs(d) + act;
        int start = m - need;
        for (int s = 0; s < abs(d); s++) p.pre[start + s][e] = d > 0 ? 1 : 2;
        if (act) p.pre[m - 1][e] = 3;
    }
    return p;
}

double objective(const Prog& p, int* len) {
    double inv = evaluate(p, len);
    if (inv > 0) return 100.0 + 10.0 * inv;
    return *len;
}

bool anneal(int k, int m, long iters, Prog& out, int& outLen) {
    Prog cur = randomProg(k, m);
    int len;
    double cc = objective(cur, &len);
    Prog best = cur;
    double bc = cc;
    double T0 = 6.0, T1 = 0.2;
    for (long it = 0; it < iters; it++) {
        double T = T0 * pow(T1 / T0, (double)it / iters);
        Prog nx = cur;
        int nm = 1 + (rng() % 3 == 0) + (rng() % 6 == 0);
        for (int q = 0; q < nm; q++) {
            if (rng() % 2) mutatePrefix(nx.pre);
            else mutateCycle(nx.cyc);
        }
        double nc = objective(nx, &len);
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
    return evaluate(best, &outLen) == 0;
}

string str(const Line& a) {
    string s;
    for (int e = 0; e < 6; e++) {
        if (e) s += ' ';
        s += "-FBT"[(int)a[e]];
    }
    return s;
}

int simulate(const vector<Line>& prog) {
    State s;
    initState(s);
    for (auto& l : prog) tick(s, l);
    return s.copies;
}

vector<Line> assemble(const Prog& p) {
    vector<Line> prog = p.pre;
    int guard = 0;
    while (simulate(prog) < CNT && guard++ < CNT + 3) prog.insert(prog.end(), p.cyc.begin(), p.cyc.end());
    if (simulate(prog) < CNT) return {};
    while (prog.size() > 1) {
        Line last = prog.back();
        prog.pop_back();
        if (simulate(prog) < CNT) {
            prog.push_back(last);
            break;
        }
    }
    return prog;
}

int main(int argc, char** argv) {
    ifstream in(argv[1]);
    int idx = atoi(argv[2]), kmax = atoi(argv[3]);
    long iters = atol(argv[4]);
    rng.seed(atoll(argv[5]));
    int restarts = argc > 6 ? atoi(argv[6]) : 3;
    int bound = argc > 7 ? atoi(argv[7]) : 1 << 30;
    int n;
    in >> n;
    for (int t = 0; t <= idx; t++) {
        int rows, cols;
        in >> R >> rows >> cols >> CNT;
        pat.assign(rows, "");
        for (auto& s : pat) in >> s;
    }
    build();
    vector<Line> best;
    for (int k = 1; k <= kmax; k++) {
        int lim = best.empty() ? bound : min(bound, (int)best.size());
        if ((long)k * (CNT - 1) + 2 >= lim) break;
        for (int rs = 0; rs < restarts; rs++) {
            int m = (int)(rng() % R) + 2 + (rs % 3) * (R / 2);
            Prog p;
            int len;
            if (anneal(k, m, iters, p, len)) {
                auto prog = assemble(p);
                if (!prog.empty() && (best.empty() || prog.size() < best.size())) best = prog;
                fprintf(stderr, "k=%d m=%d valid, program %zu\n", k, m, prog.size());
            }
        }
    }
    if (best.empty()) {
        puts("NONE");
        return 0;
    }
    for (auto& l : best) puts(str(l).c_str());
}
