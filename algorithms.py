import math
import heapq
from collections import deque

def parse_file(filename):
    # reads the map file — first line is origin, second is semicolon-separated
    # destinations, then node coords and edges follow
    with open(filename, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    origin = int(lines[0])
    destinations = [int(d) for d in lines[1].split(';')]

    nodes, edges = {}, {}
    for line in lines[2:]:
        if ':' in line:
            # looks like "3:(9,11)" — a node with coordinates
            node_id, coord = line.split(':')
            node_id = int(node_id.strip())
            coord = coord.strip().strip('()')
            x, y = coord.split(',')
            nodes[node_id] = (float(x), float(y))
            edges.setdefault(node_id, [])
        else:
            # looks like "1,2,9" — an edge from node 1 to node 2 costing 9
            parts = line.split(',')
            n1, n2, cost = int(parts[0]), int(parts[1]), float(parts[2])
            edges.setdefault(n1, [])
            edges.setdefault(n2, [])
            edges[n1].append((n2, cost))

    return origin, destinations, nodes, edges

def heuristic(node, destinations, nodes):
    # straight-line distance to the closest goal — used by GBFS, A*, and CUS2
    x1, y1 = nodes[node]
    return min(
        math.sqrt((nodes[d][0] - x1) ** 2 + (nodes[d][1] - y1) ** 2)
        for d in destinations
    )

def sorted_neighbours(node, edges):
    # always expand neighbours in ascending node-ID order so results are deterministic
    return sorted(edges.get(node, []), key=lambda x: x[0])

def DFS(origin, destinations, nodes, edges):
    # classic depth-first: dive as deep as possible before backtracking
    dest_set = set(destinations)
    stack = [(origin, [origin], 0)]
    visited = set()
    created = {origin}

    while stack:
        node, path, cost = stack.pop()
        if node in visited:
            continue
        visited.add(node)

        if node in dest_set:
            return node, len(created), path, cost

        # push neighbours in reverse so the smallest ID is explored first
        for neighbour, edge_cost in reversed(sorted_neighbours(node, edges)):
            if neighbour not in visited:
                created.add(neighbour)
                stack.append((neighbour, path + [neighbour], cost + edge_cost))

    return None, len(created), None, 0

def BFS(origin, destinations, nodes, edges):
    # breadth-first: explores level by level, guarantees shortest path
    dest_set = set(destinations)
    queue = deque([(origin, [origin], 0)])
    visited = {origin}
    created = {origin}

    while queue:
        node, path, cost = queue.popleft()

        if node in dest_set:
            return node, len(created), path, cost

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            if neighbour not in visited:
                visited.add(neighbour)
                created.add(neighbour)
                queue.append((neighbour, path + [neighbour], cost + edge_cost))

    return None, len(created), None, 0

def GBFS(origin, destinations, nodes, edges):
    # greedy best-first: always chases the node that looks closest to the goal
    # fast but not guaranteed to find the cheapest path
    dest_set = set(destinations)
    counter = 0
    heap = [(heuristic(origin, destinations, nodes), counter, origin, [origin], 0)]
    visited = set()
    created = {origin}

    while heap:
        h, _, node, path, cost = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)

        if node in dest_set:
            return node, len(created), path, cost

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            if neighbour not in visited:
                created.add(neighbour)
                counter += 1
                hn = heuristic(neighbour, destinations, nodes)
                heapq.heappush(heap, (hn, counter, neighbour,
                                      path + [neighbour], cost + edge_cost))

    return None, len(created), None, 0

def AS(origin, destinations, nodes, edges):
    # A*: balances actual cost so far (g) and estimated remaining distance (h),
    # giving the optimal path as long as the heuristic never overestimates
    dest_set = set(destinations)
    counter = 0
    heap = [(heuristic(origin, destinations, nodes), counter, origin, [origin], 0)]
    visited = {}   # node → best g seen so far
    created = {origin}

    while heap:
        f, _, node, path, g = heapq.heappop(heap)
        if node in visited and visited[node] <= g:
            continue
        visited[node] = g

        if node in dest_set:
            return node, len(created), path, g

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            new_g = g + edge_cost
            if neighbour not in visited or visited[neighbour] > new_g:
                created.add(neighbour)
                counter += 1
                hn = heuristic(neighbour, destinations, nodes)
                heapq.heappush(heap, (new_g + hn, counter, neighbour,
                                      path + [neighbour], new_g))

    return None, len(created), None, 0

def CUS1(origin, destinations, nodes, edges):
    # iterative deepening DFS, runs DFS with depth limit 0, then 1, then 2...
    # combines DFS low memory use with BFS's completeness guarantee
    dest_set = set(destinations)
    created = {origin}

    def dls(node, path, depth, visited_in_path):
        # depth-limited search, returns a result tuple or None if depth exceeded
        if node in dest_set:
            cost = sum(
                next(c for n2, c in edges.get(path[i], []) if n2 == path[i + 1])
                for i in range(len(path) - 1)
            )
            return node, path, cost
        if depth == 0:
            return None
        for neighbour, _ in sorted_neighbours(node, edges):
            if neighbour not in visited_in_path:
                created.add(neighbour)
                result = dls(neighbour, path + [neighbour],
                             depth - 1, visited_in_path | {neighbour})
                if result is not None:
                    return result
        return None

    for depth in range(len(nodes) + 1):
        result = dls(origin, [origin], depth, {origin})
        if result is not None:
            goal, path, cost = result
            return goal, len(created), path, cost

    return None, len(created), None, 0

def CUS2(origin, destinations, nodes, edges):
    # weighted A* (W=1.5), inflates the heuristic to find a solution faster, trading off a bit of optimality for speed
    dest_set = set(destinations)
    W = 1.5
    counter = 0
    heap = [(heuristic(origin, destinations, nodes) * W, counter, origin, [origin], 0)]
    visited = {}
    created = {origin}

    while heap:
        f, _, node, path, g = heapq.heappop(heap)
        if node in visited and visited[node] <= g:
            continue
        visited[node] = g

        if node in dest_set:
            return node, len(created), path, g

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            new_g = g + edge_cost
            if neighbour not in visited or visited[neighbour] > new_g:
                created.add(neighbour)
                counter += 1
                hn = heuristic(neighbour, destinations, nodes)
                heapq.heappush(heap, (new_g + W * hn, counter, neighbour,
                                      path + [neighbour], new_g))

    return None, len(created), None, 0

# maps CLI method name → function
METHODS = {
    'DFS':  DFS,
    'BFS':  BFS,
    'GBFS': GBFS,
    'AS':   AS,
    'CUS1': CUS1,
    'CUS2': CUS2,
}

# Generator algorithms (step-by-step, used by the GUI)
def DFS_gen(origin, destinations, nodes, edges):
    dest_set = set(destinations)
    stack = [(origin, [origin], 0)]
    visited = set()
    created = {origin}
    parent_map = {origin: None}

    while stack:
        node, path, cost = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        yield ('visit', node, path, cost, dict(parent_map))

        if node in dest_set:
            yield ('done', node, path, cost, len(created))
            return

        for neighbour, edge_cost in reversed(sorted_neighbours(node, edges)):
            if neighbour not in visited:
                created.add(neighbour)
                parent_map.setdefault(neighbour, node)
                yield ('frontier', neighbour, node, dict(parent_map))
                stack.append((neighbour, path + [neighbour], cost + edge_cost))

    yield ('no_solution', len(created))

def BFS_gen(origin, destinations, nodes, edges):
    dest_set = set(destinations)
    queue = deque([(origin, [origin], 0)])
    visited = {origin}
    created = {origin}
    parent_map = {origin: None}

    while queue:
        node, path, cost = queue.popleft()
        yield ('visit', node, path, cost, dict(parent_map))

        if node in dest_set:
            yield ('done', node, path, cost, len(created))
            return

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            if neighbour not in visited:
                visited.add(neighbour)
                created.add(neighbour)
                parent_map[neighbour] = node
                yield ('frontier', neighbour, node, dict(parent_map))
                queue.append((neighbour, path + [neighbour], cost + edge_cost))

    yield ('no_solution', len(created))

def GBFS_gen(origin, destinations, nodes, edges):
    dest_set = set(destinations)
    counter = 0
    heap = [(heuristic(origin, destinations, nodes), counter, origin, [origin], 0)]
    visited = set()
    created = {origin}
    parent_map = {origin: None}

    while heap:
        h, _, node, path, cost = heapq.heappop(heap)
        if node in visited:
            continue
        visited.add(node)
        yield ('visit', node, path, cost, dict(parent_map))

        if node in dest_set:
            yield ('done', node, path, cost, len(created))
            return

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            if neighbour not in visited:
                created.add(neighbour)
                parent_map.setdefault(neighbour, node)
                counter += 1
                hn = heuristic(neighbour, destinations, nodes)
                yield ('frontier', neighbour, node, dict(parent_map))
                heapq.heappush(heap, (hn, counter, neighbour,
                                      path + [neighbour], cost + edge_cost))

    yield ('no_solution', len(created))

def AS_gen(origin, destinations, nodes, edges):
    dest_set = set(destinations)
    counter = 0
    heap = [(heuristic(origin, destinations, nodes), counter, origin, [origin], 0)]
    visited = {}
    created = {origin}
    parent_map = {origin: None}

    while heap:
        f, _, node, path, g = heapq.heappop(heap)
        if node in visited and visited[node] <= g:
            continue
        visited[node] = g
        yield ('visit', node, path, g, dict(parent_map))

        if node in dest_set:
            yield ('done', node, path, g, len(created))
            return

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            new_g = g + edge_cost
            if neighbour not in visited or visited[neighbour] > new_g:
                created.add(neighbour)
                parent_map.setdefault(neighbour, node)
                counter += 1
                hn = heuristic(neighbour, destinations, nodes)
                yield ('frontier', neighbour, node, dict(parent_map))
                heapq.heappush(heap, (new_g + hn, counter, neighbour,
                                      path + [neighbour], new_g))

    yield ('no_solution', len(created))

def CUS1_gen(origin, destinations, nodes, edges):
    # iterative deepening — replays at increasing depth limits and yields events
    # for each attempt so the GUI shows the backtracking behaviour
    dest_set = set(destinations)
    created = {origin}

    def dls(node, path, depth, visited_in_path, pm, events):
        events.append(('visit', node, list(path), 0, dict(pm)))

        if node in dest_set:
            cost = sum(
                next(c for n2, c in edges.get(path[i], []) if n2 == path[i + 1])
                for i in range(len(path) - 1)
            )
            events.append(('done', node, list(path), cost, len(created)))
            return True

        if depth == 0:
            return False

        for neighbour, _ in sorted_neighbours(node, edges):
            if neighbour not in visited_in_path:
                created.add(neighbour)
                new_pm = dict(pm)
                new_pm.setdefault(neighbour, node)
                events.append(('frontier', neighbour, node, dict(new_pm)))
                if dls(neighbour, path + [neighbour], depth - 1,
                       visited_in_path | {neighbour}, new_pm, events):
                    return True
        return False

    for depth in range(len(nodes) + 1):
        events = []
        if dls(origin, [origin], depth, {origin}, {origin: None}, events):
            yield from events
            return
        yield from events

    yield ('no_solution', len(created))

def CUS2_gen(origin, destinations, nodes, edges):
    dest_set = set(destinations)
    W = 1.5
    counter = 0
    heap = [(heuristic(origin, destinations, nodes) * W, counter, origin, [origin], 0)]
    visited = {}
    created = {origin}
    parent_map = {origin: None}

    while heap:
        f, _, node, path, g = heapq.heappop(heap)
        if node in visited and visited[node] <= g:
            continue
        visited[node] = g
        yield ('visit', node, path, g, dict(parent_map))

        if node in dest_set:
            yield ('done', node, path, g, len(created))
            return

        for neighbour, edge_cost in sorted_neighbours(node, edges):
            new_g = g + edge_cost
            if neighbour not in visited or visited[neighbour] > new_g:
                created.add(neighbour)
                parent_map.setdefault(neighbour, node)
                counter += 1
                hn = heuristic(neighbour, destinations, nodes)
                yield ('frontier', neighbour, node, dict(parent_map))
                heapq.heappush(heap, (new_g + W * hn, counter, neighbour,
                                      path + [neighbour], new_g))

    yield ('no_solution', len(created))

# maps method name → generator function (used by the GUI)
GEN_METHODS = {
    'DFS':  DFS_gen,
    'BFS':  BFS_gen,
    'GBFS': GBFS_gen,
    'AS':   AS_gen,
    'CUS1': CUS1_gen,
    'CUS2': CUS2_gen,
}

def print_result(method, origin, destination, num_nodes, path, path_cost):
    # pretty-prints the CLI result in the expected assignment format
    if path is None:
        print(f"{method} {origin}")
        print("No solution found.")
        return
    path_str = ' -> '.join(str(n) for n in path)
    print(f"> Starting Node: {origin}")
    print(f"> Destination Node: {destination}")
    print(f"> Number of nodes created: {num_nodes}")
    print(f"> Path: {path_str}")
    print(f"> Path Cost: {path_cost}")
