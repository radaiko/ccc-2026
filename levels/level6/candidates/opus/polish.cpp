// Level 6 program polisher: shortens a valid program by local edits, keeping it valid.
// Usage: polish <input> <index> <seed> < program  -> prints the shortened program
// Edits: truncate after the last needed submission, delete a line, merge two adjacent lines,
// delete a line and change one instruction within a small window around it.
#include <algorithm>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <vector>
using namespace std;
typedef unsigned long long u64;
typedef array<char, 6> Line;

static const int DR[6] = {0, 1, 1, 0, -1, -1}, DC[6] = {2, 1, -1, -2, -1, 1};
static const int NBR[6] = {0, 0, 1, 1, -1, -1}, NBC[6] = {2, -2, 1, -1, 1, -1};
const int MW = 8;

int R, H, Wd, CNT, RING, NREL, NP, NW;
vector<string> pat;
vector<pair<int, int>> ringc;
vector<char> fires;
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
}

// Returns the 1-based line index at which the CNT-th copy is submitted, or 0.
int simulate(const vector<Line>& prog) {
    u64 M[MW] = {0};
    int pos[6], act[6] = {0};
    for (int e = 0; e < 6; e++) pos[e] = e * R;
    int cp = 0;
    for (size_t t = 0; t < prog.size(); t++) {
        const Line& l = prog[t];
        u64 s0[MW] = {0}, s1[MW] = {0}, s2[MW] = {0};
        for (int e = 0; e < 6; e++) {
            if (l[e] == 1) pos[e] = pos[e] + 1 == RING ? 0 : pos[e] + 1;
            else if (l[e] == 2) pos[e] = pos[e] == 0 ? RING - 1 : pos[e] - 1;
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
            if (++cp >= CNT) return t + 1;
            for (int q = 0; q < NW; q++) M[q] &= ~Pm[q];
        }
    }
    return 0;
}

bool accept(vector<Line>& prog, const vector<Line>& cand) {
    int end = simulate(cand);
    if (!end) return false;
    vector<Line> c(cand.begin(), cand.begin() + end);
    if (c.size() < prog.size()) {
        prog = c;
        return true;
    }
    return false;
}

int main(int argc, char** argv) {
    ifstream in(argv[1]);
    int idx = atoi(argv[2]);
    mt19937_64 rng(atoll(argv[3]));
    int window = argc > 4 ? atoi(argv[4]) : 3;
    int n;
    in >> n;
    for (int t = 0; t <= idx; t++) {
        int rows, cols;
        in >> R >> rows >> cols >> CNT;
        pat.assign(rows, "");
        for (auto& s : pat) in >> s;
    }
    build();
    vector<Line> prog;
    string s;
    while (getline(cin, s)) {
        istringstream ss(s);
        Line l;
        string tok;
        int e = 0;
        while (ss >> tok && e < 6) l[e++] = tok == "F" ? 1 : tok == "B" ? 2 : tok == "T" ? 3 : 0;
        if (e == 6) prog.push_back(l);
    }
    int end = simulate(prog);
    if (!end) {
        puts("INVALID");
        return 0;
    }
    prog.resize(end);
    bool changed = true;
    while (changed) {
        changed = false;
        // delete one line
        for (int t = (int)prog.size() - 1; t >= 0; t--) {
            if (t >= (int)prog.size()) continue;
            vector<Line> c = prog;
            c.erase(c.begin() + t);
            if (accept(prog, c)) changed = true;
        }
        // merge adjacent compatible lines
        for (int t = (int)prog.size() - 2; t >= 0; t--) {
            if (t + 1 >= (int)prog.size()) continue;
            Line m;
            bool ok = true;
            for (int e = 0; e < 6 && ok; e++) {
                if (prog[t][e] && prog[t + 1][e]) ok = false;
                m[e] = prog[t][e] ? prog[t][e] : prog[t + 1][e];
            }
            if (!ok) continue;
            vector<Line> c = prog;
            c[t] = m;
            c.erase(c.begin() + t + 1);
            if (accept(prog, c)) changed = true;
        }
        // delete a line and repair with one instruction change nearby
        if (!changed) {
            vector<int> order(prog.size());
            for (int t = 0; t < (int)prog.size(); t++) order[t] = t;
            shuffle(order.begin(), order.end(), rng);
            for (int t : order) {
                if (t >= (int)prog.size()) continue;
                vector<Line> c = prog;
                c.erase(c.begin() + t);
                bool done = false;
                for (int u = max(0, t - window); u < min((int)c.size(), t + window) && !done; u++)
                    for (int e = 0; e < 6 && !done; e++)
                        for (int v = 0; v < 4 && !done; v++) {
                            if (c[u][e] == v) continue;
                            char old = c[u][e];
                            c[u][e] = v;
                            if (accept(prog, c)) done = true;
                            else c[u][e] = old;
                        }
                if (done) {
                    changed = true;
                    break;
                }
            }
        }
    }
    for (auto& l : prog) {
        string o;
        for (int e = 0; e < 6; e++) {
            if (e) o += ' ';
            o += "-FBT"[(int)l[e]];
        }
        puts(o.c_str());
    }
}
