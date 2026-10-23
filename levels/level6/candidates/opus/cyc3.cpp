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

// ---- periodic 3-tick cycles X -> Y -> Z -> X, Z clean (submits) ----
// Per emitter state: line index (or -1 = off) plus, for off states, the line index of its position (pl).
int L;
struct St {
    int ln;  // -1 off
    int pl;  // position line index (for off states: where it sits; -1 = parked/irrelevant)
};
int zc[6];          // Z line per emitter (-1 off)
BS TZ, DZ, need;
long long nodes = 0;
int found = 0, maxSol = 1;
vector<array<St, 2>> opts[6];  // (x, y) options per emitter given Z
array<St, 2> pick[6];

BS lineOr(int e, int ln) {
    BS b;
    memset(b.w, 0, sizeof b.w);
    if (ln >= 0) b = lines[e][ln].second;
    return b;
}

void report3() {
    printf("CYCLE3\n");
    for (int which = 0; which < 3; which++) {
        printf("%d", which);
        for (int e = 0; e < 6; e++) {
            St s;
            if (which == 2) s = {zc[e], -1};
            else s = pick[e][which];
            // position: own line, else position line, else z line, else corner
            int pl = s.ln >= 0 ? s.ln : s.pl;
            if (pl < 0) pl = zc[e] >= 0 ? zc[e] : -1;
            if (pl < 0)
                for (int w = 0; w < 2; w++)
                    if (pick[e][w].ln >= 0) pl = pick[e][w].ln;
            int pos = pl >= 0 ? lines[e][pl].first : e * R;
            printf(" %d %d", pos, s.ln >= 0 ? 1 : 0);
        }
        printf("\n");
    }
    fflush(stdout);
    found++;
}

void buildOpts(int e) {
    opts[e].clear();
    int z = zc[e];
    if (z >= 0) {
        // y in N(z): (z,on),(z+-1,on),(z,off); x in N(y) & N(z)
        auto ok = [&](int l) { return l >= 0 && l < L; };
        opts[e].push_back({St{z, -1}, St{z, -1}});
        if (ok(z - 1)) opts[e].push_back({St{z - 1, -1}, St{z, -1}});
        if (ok(z + 1)) opts[e].push_back({St{z + 1, -1}, St{z, -1}});
        opts[e].push_back({St{-1, z}, St{z, -1}});
        for (int d : {-1, 1})
            if (ok(z + d)) {
                opts[e].push_back({St{z + d, -1}, St{z + d, -1}});
                opts[e].push_back({St{z, -1}, St{z + d, -1}});
            }
        opts[e].push_back({St{-1, z}, St{-1, z}});
        opts[e].push_back({St{z, -1}, St{-1, z}});
    } else {
        opts[e].push_back({St{-1, -1}, St{-1, -1}});
        for (int l = 0; l < L; l++) {
            opts[e].push_back({St{l, -1}, St{-1, l}});
            opts[e].push_back({St{l, -1}, St{l, -1}});
            opts[e].push_back({St{-1, l}, St{l, -1}});
        }
    }
}

void dfsXY(int e, BS x0, BS x1, BS x2, BS y0, BS y1, BS y2, const vector<BS>& reachX, const vector<BS>& reachY) {
    if (found >= maxSol) return;
    nodes++;
    for (int q = 0; q < NW; q++) {
        // burnt at Y and not recoverable
        if (need.w[q] & y2.w[q]) return;
        u64 xOk = x1.w[q] & ~x2.w[q], yOk = y1.w[q] & ~y2.w[q];
        u64 open = need.w[q] & ~xOk & ~yOk;
        // cells still missing must be reachable in X (if X not yet burnt) or in Y
        u64 canX = ~x2.w[q] & reachX[e].w[q], canY = reachY[e].w[q];
        if (open & ~(canX | canY)) return;
    }
    if (e == 6) {
        for (int q = 0; q < NW; q++) {
            u64 tx = x1.w[q] & ~x2.w[q], ty = y1.w[q] & ~y2.w[q];
            u64 my = (tx | ty) & ~y2.w[q];
            if (need.w[q] & ~my) return;
            if (Hm[q] & my & ~DZ.w[q]) return;
        }
        report3();
        return;
    }
    for (auto& o : opts[e]) {
        pick[e] = o;
        BS nx0 = x0, nx1 = x1, nx2 = x2, ny0 = y0, ny1 = y1, ny2 = y2;
        if (o[0].ln >= 0) {
            const BS& b = lines[e][o[0].ln].second;
            for (int q = 0; q < NW; q++) {
                nx2.w[q] |= nx1.w[q] & b.w[q];
                nx1.w[q] |= nx0.w[q] & b.w[q];
                nx0.w[q] |= b.w[q];
            }
        }
        if (o[1].ln >= 0) {
            const BS& b = lines[e][o[1].ln].second;
            for (int q = 0; q < NW; q++) {
                ny2.w[q] |= ny1.w[q] & b.w[q];
                ny1.w[q] |= ny0.w[q] & b.w[q];
                ny0.w[q] |= b.w[q];
            }
        }
        dfsXY(e + 1, nx0, nx1, nx2, ny0, ny1, ny2, reachX, reachY);
    }
}

void dfsZ(int e, BS s0, BS s1, BS s2, int active) {
    if (found >= maxSol) return;
    for (int q = 0; q < NW; q++)
        if (Pm[q] & s2.w[q]) return;
    if (e == 6) {
        if (active < 2) return;  // Z must do something (a 2-tick copy was ruled out separately)
        bool any = false;
        for (int q = 0; q < NW; q++) {
            TZ.w[q] = s1.w[q] & ~s2.w[q];
            DZ.w[q] = s2.w[q];
            if (Hm[q] & TZ.w[q]) return;
            need.w[q] = Pm[q] & ~TZ.w[q];
            if (need.w[q]) any = true;
        }
        if (!any) return;  // static; found by cyc2
        for (int f = 0; f < 6; f++) buildOpts(f);
        vector<BS> reachX(7), reachY(7);
        memset(reachX[6].w, 0, sizeof reachX[6].w);
        memset(reachY[6].w, 0, sizeof reachY[6].w);
        for (int f = 5; f >= 0; f--) {
            reachX[f] = reachX[f + 1];
            reachY[f] = reachY[f + 1];
            for (auto& o : opts[f]) {
                if (o[0].ln >= 0)
                    for (int q = 0; q < NW; q++) reachX[f].w[q] |= lines[f][o[0].ln].second.w[q];
                if (o[1].ln >= 0)
                    for (int q = 0; q < NW; q++) reachY[f].w[q] |= lines[f][o[1].ln].second.w[q];
            }
        }
        BS z;
        memset(z.w, 0, sizeof z.w);
        dfsXY(0, z, z, z, z, z, z, reachX, reachY);
        return;
    }
    for (int o = -1; o < L; o++) {
        zc[e] = o;
        if (o < 0) {
            dfsZ(e + 1, s0, s1, s2, active);
        } else {
            const BS& b = lines[e][o].second;
            BS n0, n1, n2;
            for (int q = 0; q < NW; q++) {
                n2.w[q] = s2.w[q] | (s1.w[q] & b.w[q]);
                n1.w[q] = s1.w[q] | (s0.w[q] & b.w[q]);
                n0.w[q] = s0.w[q] | b.w[q];
            }
            dfsZ(e + 1, n0, n1, n2, active + 1);
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
    dfsZ(0, z, z, z, 0);
    fprintf(stderr, "found %d nodes %lld\n", found, nodes);
    if (!found) puts("NONE");
}
