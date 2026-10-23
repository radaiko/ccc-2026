from collections import deque
from heapq import heappop, heappush


def bfs(start, neighbors, goal=None):
    """neighbors(node) -> iterable of nodes. Returns (dist, parent) dicts, or the
    distance to the first node satisfying goal(node) if goal is given (None if unreachable)."""
    dist = {start: 0}
    parent = {start: None}
    q = deque([start])
    while q:
        u = q.popleft()
        if goal and goal(u):
            return dist[u]
        for v in neighbors(u):
            if v not in dist:
                dist[v] = dist[u] + 1
                parent[v] = u
                q.append(v)
    return None if goal else (dist, parent)


def dijkstra(start, neighbors, goal=None):
    """neighbors(node) -> iterable of (node, cost). Same return shape as bfs."""
    dist = {start: 0}
    parent = {start: None}
    pq = [(0, 0, start)]
    tie = 1  # avoids comparing nodes on equal cost
    while pq:
        d, _, u = heappop(pq)
        if d > dist[u]:
            continue
        if goal and goal(u):
            return d
        for v, w in neighbors(u):
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heappush(pq, (nd, tie, v))
                tie += 1
    return None if goal else (dist, parent)


def path_to(parent, end):
    path = []
    while end is not None:
        path.append(end)
        end = parent[end]
    return path[::-1]
