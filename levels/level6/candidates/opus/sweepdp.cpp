// Row sweep with exact puncher planning.
// Emitters a and a+3 sit on the same line of axis a and paint it whole (2 hits) one line per tick,
// alternating sweep direction between copies. The four other emitters punch halo cells on the painted
// line (3 hits). Planned by DP over the joint state of one puncher axis (2 emitters) with the other
// axis fixed, alternating. Hard constraints: a puncher never hits a pattern cell of the painted line,
// two punchers never cross (2 hits) on a halo cell of a line already painted in the current copy,
// two punchers of one axis never share a line.
// Usage: sweepdp <input> <index> <axis 0..2> <reverse 0/1> <rounds> <copiesToPlan>
// Prints: "UNKILLED <n>" then the full program (all copies planned).
#include <algorithm>
#include <array>
#include <climits>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>
using namespace std;

static const int DR[6] = {0, 1, 1, 0, -1, -1}, DC[6] = {2, 1, -1, -2, -1, 1};
static const int NBR[6] = {0, 0, 1, 1, -1, -1}, NBC[6] = {2, -2, 1, -1, 1, -1};

int R, H, Wd, CNT, RING;
vector<string> pat, g;
vector<pair<int, int>> ringc;
map<pair<int, int>, int> ringIdx;
// cells
vector<pair<int, int>> cells;
map<pair<int, int>, int> cellId;
vector<int> role;                 // 1 pattern, 2 halo, 0 other
vector<array<int, 3>> lineOf;     // per cell, per axis: ring position of emitter `axis` covering it
vector<int> lineE;                // [e*RING+p] -> line id (ring pos of emitter e%3) or -1
map<array<int, 4>, int> cross;    // (axis1,line1,axis2,line2) -> cell

int offs(int e, int p) { return ((p - e * R) % RING + RING + 3 * R) % RING - 3 * R; }

void build() {
    H = 2 * R + 1;
    Wd = 4 * R + 1;
    g.assign(H, string(Wd, ' '));
    for (int i = 0; i < H; i++) {
        int k = abs(i - R), n = 2 * R + 1 - k;
        for (int j = 0; j < n; j++) g[i][k + 2 * j] = (k == R || j == 0 || j == n - 1) ? '*' : 'O';
    }
    int i = R, c = 0;
    int sd[6][2] = {{-1, 1}, {0, 2}, {1, 1}, {1, -1}, {0, -2}, {-1, -1}};
    for (int s = 0; s < 6; s++)
        for (int t = 0; t < R; t++) {
            ringIdx[{i, c}] = ringc.size();
            ringc.push_back({i, c});
            i += sd[s][0];
            c += sd[s][1];
        }
    RING = 6 * R;
    for (int y = 0; y < H; y++)
        for (int x = 0; x < Wd; x++)
            if (g[y][x] == 'O') {
                cellId[{y, x}] = cells.size();
                cells.push_back({y, x});
            }
    role.assign(cells.size(), 0);
    for (size_t q = 0; q < cells.size(); q++) {
        auto [y, x] = cells[q];
        if (pat[y][x] == 'M') role[q] = 1;
    }
    for (size_t q = 0; q < cells.size(); q++) {
        if (role[q] == 1) continue;
        auto [y, x] = cells[q];
        for (int d = 0; d < 6; d++) {
            int yy = y + NBR[d], xx = x + NBC[d];
            if (yy >= 0 && yy < H && xx >= 0 && xx < Wd && pat[yy][xx] == 'M') role[q] = 2;
        }
    }
    lineOf.assign(cells.size(), {-1, -1, -1});
    for (size_t q = 0; q < cells.size(); q++)
        for (int a = 0; a < 3; a++) {
            int y = cells[q].first, x = cells[q].second;
            while (!ringIdx.count({y, x})) y -= DR[a], x -= DC[a];
            lineOf[q][a] = ringIdx[{y, x}];
        }
    lineE.assign(6 * RING, -1);
    for (int e = 0; e < 6; e++)
        for (int p = 0; p < RING; p++) {
            int y = ringc[p].first + DR[e], x = ringc[p].second + DC[e];
            if (y >= 0 && y < H && x >= 0 && x < Wd && g[y][x] == 'O') lineE[e * RING + p] = lineOf[cellId[{y, x}]][e % 3];
        }
    for (size_t q = 0; q < cells.size(); q++)
        for (int a = 0; a < 3; a++)
            for (int b = 0; b < 3; b++)
                if (a != b) cross[{a, lineOf[q][a], b, lineOf[q][b]}] = q;
}

int crossCell(int a, int la, int b, int lb) {
    auto it = cross.find({a, la, b, lb});
    return it == cross.end() ? -1 : it->second;
}

struct ES {
    int pos, act;
};

int main(int argc, char** argv) {
    ifstream in(argv[1]);
    int idx = atoi(argv[2]), A = atoi(argv[3]), rev = atoi(argv[4]), rounds = atoi(argv[5]);
    int copiesPlan = atoi(argv[6]);
    int n;
    in >> n;
    for (int t = 0; t <= idx; t++) {
        int rows, cols;
        in >> R >> rows >> cols >> CNT;
        pat.assign(rows, "");
        for (auto& s : pat) in >> s;
    }
    build();
    if (copiesPlan <= 0 || copiesPlan > CNT) copiesPlan = CNT;
    // rows of axis A containing pattern cells, as (posA, posA3)
    set<int> rowset;
    for (size_t q = 0; q < cells.size(); q++)
        if (role[q] == 1) rowset.insert(lineOf[q][A]);
    // line id -> ring position for emitter A+3
    map<int, int> posOther;
    for (int p = 0; p < RING; p++)
        if (lineE[(A + 3) * RING + p] >= 0) posOther[lineE[(A + 3) * RING + p]] = p;
    vector<int> rows(rowset.begin(), rowset.end());
    sort(rows.begin(), rows.end(), [&](int x, int y) { return offs(A, x) < offs(A, y); });
    if (rev) reverse(rows.begin(), rows.end());
    int ea = A, eb = A + 3;
    // pair schedule
    int da = offs(ea, rows[0]), db = offs(eb, posOther[rows[0]]);
    int travel = max(abs(da), abs(db));
    vector<array<char, 6>> prog;
    vector<int> rowAt;   // painted line per tick (-1 = none)
    vector<int> copyAt;  // copy index per tick
    vector<char> lastOfCopy;
    for (int t = 0; t < travel; t++) {
        array<char, 6> l = {'-', '-', '-', '-', '-', '-'};
        if (t < abs(da)) l[ea] = da > 0 ? 'F' : 'B';
        if (t < abs(db)) l[eb] = db > 0 ? 'F' : 'B';
        prog.push_back(l);
        rowAt.push_back(-1);
        copyAt.push_back(0);
        lastOfCopy.push_back(0);
    }
    vector<int> seq = rows;
    for (int cp = 0; cp < copiesPlan; cp++) {
        for (size_t i = 0; i < seq.size(); i++) {
            array<char, 6> l = {'-', '-', '-', '-', '-', '-'};
            if (cp == 0 && i == 0) {
                l[ea] = l[eb] = 'T';
            } else if (i > 0) {
                int pa = seq[i - 1], qa = seq[i];
                int dA = offs(ea, qa) - offs(ea, pa);
                int dB = offs(eb, posOther[qa]) - offs(eb, posOther[pa]);
                l[ea] = dA > 0 ? 'F' : dA < 0 ? 'B' : '-';
                l[eb] = dB > 0 ? 'F' : dB < 0 ? 'B' : '-';
            }
            prog.push_back(l);
            rowAt.push_back(seq[i]);
            copyAt.push_back(cp);
            lastOfCopy.push_back(i + 1 == seq.size());
        }
        reverse(seq.begin(), seq.end());
    }
    int T = prog.size();
    // painted-before sets: for tick t, rows painted earlier in the same copy
    vector<set<int>> paintedBefore(T);
    {
        set<int> cur;
        int curCopy = -1;
        for (int t = 0; t < T; t++) {
            if (copyAt[t] != curCopy) cur.clear(), curCopy = copyAt[t];
            paintedBefore[t] = cur;
            if (rowAt[t] >= 0) cur.insert(rowAt[t]);
        }
    }
    // halo cells per row
    map<int, vector<int>> haloOnRow;
    for (size_t q = 0; q < cells.size(); q++)
        if (role[q] == 2) haloOnRow[lineOf[q][A]].push_back(q);

    int axes[2] = {(A + 1) % 3, (A + 2) % 3};
    // plan[e][t] state after tick t
    vector<vector<ES>> plan(6, vector<ES>(T));
    for (int e = 0; e < 6; e++) {
        ES s = {e * R, 0};
        for (int t = 0; t < T; t++) plan[e][t] = s;
    }
    // per emitter state indexing: offsets -R..R, act 0/1
    int NO = 2 * R + 1;
    auto posOf = [&](int e, int o) { return ((e * R + o) % RING + RING) % RING; };
    auto lineAt = [&](int e, int pos, int act) { return act ? lineE[e * RING + pos] : -1; };

    long long bestTotal = LLONG_MAX;
    for (int round = 0; round < rounds * 2; round++) {
        int ax = axes[round % 2], fx = axes[(round + 1) % 2];
        int e1 = ax, e2 = ax + 3, f1 = fx, f2 = fx + 3;
        int NS = NO * 2;  // per emitter
        // per tick, per single-emitter state: bad flag, kill cell, crossing-bad with fixed punchers
        auto single = [&](int e, int t, int o, int act, int& kill) -> bool {
            kill = -1;
            int pos = posOf(e, o);
            int ln = lineAt(e, pos, act);
            if (ln < 0) return true;
            int row = rowAt[t];
            if (row >= 0) {
                int c = crossCell(A, row, ax, ln);
                if (c >= 0) {
                    if (role[c] == 1) return false;
                    if (role[c] == 2) kill = c;
                }
            }
            for (int f : {f1, f2}) {
                ES s = plan[f][t];
                int lf = lineAt(f, s.pos, s.act);
                if (lf < 0) continue;
                int c = crossCell(ax, ln, fx, lf);
                if (c < 0) continue;
                if (row >= 0 && lineOf[c][A] == row) continue;  // 4 hits: destroyed
                if (role[c] == 2 && paintedBefore[t].count(lineOf[c][A])) return false;
            }
            return true;
        };
        const long long INF = 1LL << 40;
        vector<vector<long long>> dp(T + 1, vector<long long>(NS * NS, INF));
        vector<vector<int>> from(T + 1, vector<int>(NS * NS, -1));
        auto enc = [&](int o, int a) { return (o + R) * 2 + a; };
        int s0 = enc(0, 0) * NS + enc(0, 0);
        dp[0][s0] = 0;
        for (int t = 0; t < T; t++) {
            // fixed kills
            set<int> fixedKill;
            int row = rowAt[t];
            if (row >= 0)
                for (int f : {f1, f2}) {
                    ES s = plan[f][t];
                    int lf = lineAt(f, s.pos, s.act);
                    if (lf < 0) continue;
                    int c = crossCell(A, row, fx, lf);
                    if (c >= 0 && role[c] == 2) fixedKill.insert(c);
                }
            vector<int> halos = row >= 0 ? haloOnRow[row] : vector<int>();
            // precompute single-state info
            vector<char> ok1(NS), ok2(NS);
            vector<int> k1(NS), k2(NS);
            for (int o = -R; o <= R; o++)
                for (int a = 0; a < 2; a++) {
                    int s = enc(o, a);
                    ok1[s] = single(e1, t, o, a, k1[s]);
                    ok2[s] = single(e2, t, o, a, k2[s]);
                }
            for (int s = 0; s < NS * NS; s++) {
                if (dp[t][s] >= INF) continue;
                int sa = s / NS, sb = s % NS;
                int oa = sa / 2 - R, aa = sa % 2, ob = sb / 2 - R, ab = sb % 2;
                for (int m1 = 0; m1 < 4; m1++) {
                    int na_o = oa + (m1 == 1) - (m1 == 2), na_a = m1 == 3 ? !aa : aa;
                    if (na_o < -R || na_o > R) continue;
                    int ns1 = enc(na_o, na_a);
                    if (!ok1[ns1]) continue;
                    for (int m2 = 0; m2 < 4; m2++) {
                        int nb_o = ob + (m2 == 1) - (m2 == 2), nb_a = m2 == 3 ? !ab : ab;
                        if (nb_o < -R || nb_o > R) continue;
                        int ns2 = enc(nb_o, nb_a);
                        if (!ok2[ns2]) continue;
                        int l1 = lineAt(e1, posOf(e1, na_o), na_a), l2 = lineAt(e2, posOf(e2, nb_o), nb_a);
                        if (l1 >= 0 && l1 == l2) continue;
                        long long cost = 0;
                        for (int h : halos)
                            if (h != k1[ns1] && h != k2[ns2] && !fixedKill.count(h)) cost += 1000;
                        cost += (m1 != 0) + (m2 != 0);  // prefer calm plans
                        int ns = ns1 * NS + ns2;
                        if (dp[t][s] + cost < dp[t + 1][ns]) {
                            dp[t + 1][ns] = dp[t][s] + cost;
                            from[t + 1][ns] = s;
                        }
                    }
                }
            }
        }
        int bs = -1;
        for (int s = 0; s < NS * NS; s++)
            if (dp[T][s] < INF && (bs < 0 || dp[T][s] < dp[T][bs])) bs = s;
        if (bs < 0) break;
        bestTotal = dp[T][bs];
        for (int t = T; t > 0; t--) {
            int sa = bs / NS, sb = bs % NS;
            plan[e1][t - 1] = {posOf(e1, sa / 2 - R), sa % 2};
            plan[e2][t - 1] = {posOf(e2, sb / 2 - R), sb % 2};
            bs = from[t][bs];
        }
    }
    // emit program
    for (int t = 0; t < T; t++)
        for (int k = 0; k < 2; k++)
            for (int e : {axes[k], axes[k] + 3}) {
                ES prev = t ? plan[e][t - 1] : ES{e * R, 0};
                ES cur = plan[e][t];
                char c = '-';
                if (cur.act != prev.act) c = 'T';
                else if (cur.pos == (prev.pos + 1) % RING) c = 'F';
                else if (cur.pos == (prev.pos + RING - 1) % RING) c = 'B';
                prog[t][e] = c;
            }
    printf("UNKILLED %lld\n", bestTotal == LLONG_MAX ? -1 : bestTotal / 1000);
    for (auto& l : prog) {
        string o;
        for (int e = 0; e < 6; e++) {
            if (e) o += ' ';
            o += l[e];
        }
        puts(o.c_str());
    }
}
