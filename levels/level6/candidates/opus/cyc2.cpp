// Exact search for static configurations (1 line per copy) and 2-tick cycles (C1 dirty, C2 clean).
// Configuration: per emitter off or a line of its axis. Cycle C1 -> C2 -> C1 with adjacent states per
// emitter (same line, neighbouring line, or toggle at the same line; off in both = irrelevant).
// From empty matter: after C1 M = T1; after C2 M = (T1 | T2) & ~D2. Valid iff P & D2 = 0, H & T2 = 0,
// P & ~T2 subset of T1, H & T1 subset of D2.
// Usage: cyc2 <input> <index> [maxSolutions]
// Prints "STATIC" + 6 ring positions/acts, or "CYCLE2" + two configurations; one per line:
// "<k> pos0 act0 ... pos5 act5" (k = 1 or 2 configurations).
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
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
u64 Pm[MW], Hm[MW];

struct BS {
    u64 w[MW];
};
// options per emitter: list of (ring position, line bitset); index 0 = off
vector<vector<pair<int, BS>>> lines(6);

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
    for (int e = 0; e < 6; e++) {
        // firing positions in rail order around the corner: offsets -(R-1)..R-1
        for (int o = -(R - 1); o <= R - 1; o++) {
            int p = ((e * R + o) % RING + RING) % RING;
            BS b;
            memset(b.w, 0, sizeof b.w);
            int y = ringc[p].first + DR[e], x = ringc[p].second + DC[e];
            while (y >= 0 && y < H && x >= 0 && x < Wd && g[y][x] == 'O') {
                auto it = rel.find({y, x});
                if (it != rel.end()) b.w[it->second >> 6] |= 1ULL << (it->second & 63);
                y += DR[e];
                x += DC[e];
            }
            lines[e].push_back({p, b});
        }
    }
}

int L;  // lines per emitter
int c2[6], c1[6];  // -1 off, else line index
BS T2, D2, need;
long long nodes = 0;
int found = 0, maxSol = 1;

void report(int k) {
    // print C1 and C2 as ring positions; an emitter off in both is parked at its corner
    printf("%s\n", k == 1 ? "STATIC" : "CYCLE2");
    for (int which = 0; which < k; which++) {
        int* cfg = (k == 1 || which == 1) ? c2 : c1;
        printf("%d", which);
        for (int e = 0; e < 6; e++) {
            int ln = cfg[e];
            int other = (k == 2) ? (which == 0 ? c2[e] : c1[e]) : -1;
            int pos;
            if (ln >= 0) pos = lines[e][ln].first;
            else if (other >= 0) pos = lines[e][other].first;  // toggled at the same place
            else pos = e * R;
            printf(" %d %d", pos, ln >= 0 ? 1 : 0);
        }
        printf("\n");
    }
    fflush(stdout);
    found++;
}

// DFS over C1 emitters; s0,s1,s2 hit accumulators
void dfs1(int e, BS s0, BS s1, BS s2, const vector<BS>& reachRest) {
    if (found >= maxSol) return;
    nodes++;
    // prune: need cells with >=3 hits; need cells unreachable to exactly 2
    for (int q = 0; q < NW; q++) {
        if (need.w[q] & s2.w[q]) return;
        u64 lacking = need.w[q] & ~s1.w[q];
        if (lacking & ~reachRest[e].w[q]) return;
    }
    if (e == 6) {
        for (int q = 0; q < NW; q++) {
            u64 t1 = s1.w[q] & ~s2.w[q];
            if (need.w[q] & ~t1) return;
            if (Hm[q] & t1 & ~D2.w[q]) return;
        }
        report(2);
        return;
    }
    // options for emitter e in C1
    vector<int> opts;
    if (c2[e] >= 0) {
        opts.push_back(-1);
        for (int d = -1; d <= 1; d++)
            if (c2[e] + d >= 0 && c2[e] + d < L) opts.push_back(c2[e] + d);
    } else {
        opts.push_back(-1);
        for (int l = 0; l < L; l++) opts.push_back(l);
    }
    for (int o : opts) {
        c1[e] = o;
        if (o < 0) {
            dfs1(e + 1, s0, s1, s2, reachRest);
        } else {
            const BS& b = lines[e][o].second;
            BS n0, n1, n2;
            for (int q = 0; q < NW; q++) {
                n2.w[q] = s2.w[q] | (s1.w[q] & b.w[q]);
                n1.w[q] = s1.w[q] | (s0.w[q] & b.w[q]);
                n0.w[q] = s0.w[q] | b.w[q];
            }
            dfs1(e + 1, n0, n1, n2, reachRest);
        }
    }
}

void dfs2(int e, BS s0, BS s1, BS s2) {
    if (found >= maxSol) return;
    for (int q = 0; q < NW; q++)
        if (Pm[q] & s2.w[q]) return;  // a pattern cell burnt at C2
    if (e == 6) {
        for (int q = 0; q < NW; q++) {
            T2.w[q] = s1.w[q] & ~s2.w[q];
            D2.w[q] = s2.w[q];
            if (Hm[q] & T2.w[q]) return;
            need.w[q] = Pm[q] & ~T2.w[q];
        }
        bool empty = true;
        for (int q = 0; q < NW; q++)
            if (need.w[q]) empty = false;
        if (empty) {
            report(1);
            return;
        }
        // reachable sets for the rest of C1 emitters
        vector<BS> reachRest(7);
        memset(reachRest[6].w, 0, sizeof reachRest[6].w);
        for (int f = 5; f >= 0; f--) {
            reachRest[f] = reachRest[f + 1];
            if (c2[f] >= 0) {
                for (int d = -1; d <= 1; d++)
                    if (c2[f] + d >= 0 && c2[f] + d < L)
                        for (int q = 0; q < NW; q++) reachRest[f].w[q] |= lines[f][c2[f] + d].second.w[q];
            } else {
                for (int l = 0; l < L; l++)
                    for (int q = 0; q < NW; q++) reachRest[f].w[q] |= lines[f][l].second.w[q];
            }
        }
        BS z;
        memset(z.w, 0, sizeof z.w);
        dfs1(0, z, z, z, reachRest);
        return;
    }
    for (int o = -1; o < L; o++) {
        c2[e] = o;
        if (o < 0) {
            dfs2(e + 1, s0, s1, s2);
        } else {
            const BS& b = lines[e][o].second;
            BS n0, n1, n2;
            for (int q = 0; q < NW; q++) {
                n2.w[q] = s2.w[q] | (s1.w[q] & b.w[q]);
                n1.w[q] = s1.w[q] | (s0.w[q] & b.w[q]);
                n0.w[q] = s0.w[q] | b.w[q];
            }
            dfs2(e + 1, n0, n1, n2);
        }
    }
}

int main(int argc, char** argv) {
    ifstream in(argv[1]);
    int idx = atoi(argv[2]);
    if (argc > 3) maxSol = atoi(argv[3]);
    int n;
    in >> n;
    for (int t = 0; t <= idx; t++) {
        int rows, cols;
        in >> R >> rows >> cols >> CNT;
        pat.assign(rows, "");
        for (auto& s : pat) in >> s;
    }
    build();
    L = 2 * R - 1;
    BS z;
    memset(z.w, 0, sizeof z.w);
    dfs2(0, z, z, z);
    fprintf(stderr, "found %d nodes %lld\n", found, nodes);
    if (!found) puts("NONE");
}
