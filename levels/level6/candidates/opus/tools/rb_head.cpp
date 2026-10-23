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

