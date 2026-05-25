import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import deque

from algorithms import parse_file, GEN_METHODS


# ── Colour palette (Catppuccin Mocha) ─────────────────────────────────────────
C_BG       = "#1e1e2e"   # window background
C_CANVAS   = "#181825"   # canvas background
C_TEXT     = "#cdd6f4"   # normal text
C_SUBTEXT  = "#585b70"   # dimmed labels / edge cost numbers
C_PANEL    = "#313244"   # status bar / button backgrounds
C_DEFAULT  = "#6c7086"   # unvisited node
C_FRONTIER = "#f9e2af"   # node sitting in the frontier (queued but not expanded yet)
C_VISITED  = "#89b4fa"   # node that has already been expanded
C_CURRENT  = "#fab387"   # the node being expanded right now
C_SOLUTION = "#a6e3a1"   # nodes / edges that form the final solution path
C_DEST     = "#f38ba8"   # destination / goal nodes
C_ORIGIN   = "#cba6f7"   # starting node
C_EDGE     = "#45475a"   # default edge colour
C_EDGE_SOL = "#a6e3a1"   # edge colour when it's part of the solution


class SearchGUI:
    # spacing / size constants — tweak these if things look too cramped or too spread out
    PAD    = 44    # padding around the graph canvas so nodes aren't clipped
    NODE_R = 18    # radius of graph nodes
    TREE_R = 13    # radius of tree nodes (slightly smaller so the tree isn't huge)
    XGAP   = 56    # horizontal spacing between tree nodes
    YGAP   = 60    # vertical spacing between tree levels

    # (label, delay in milliseconds) — Step-only means the user drives manually
    SPEEDS = [("Slow", 900), ("Medium", 350), ("Fast", 80), ("Step-only", 0)]

    def __init__(self, root):
        self.root = root
        self.root.title("Search Algorithm Visualiser")
        self.root.configure(bg=C_BG)
        self.root.minsize(1200, 680)

        # loaded map data
        self.filename     = None
        self.origin       = None
        self.destinations = []
        self.nodes        = {}
        self.edges        = {}

        # playback state
        self.generator = None
        self.running   = False
        self.after_id  = None
        self.delay_ms  = 350

        # search state (updated on every event from the generator)
        self.visited    = set()
        self.frontier   = set()
        self.current    = None
        self.cur_path   = []
        self.sol_path   = []
        self.parent_map = {}
        self.finished   = False

        self._build_ui()

    # ── UI layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_topbar()
        self._build_main_panes()
        self._build_statusbar()
        self._build_legend()

        # redraw both canvases whenever the window is resized
        self.g_canvas.bind('<Configure>', lambda _: self._draw_graph())
        self.t_canvas.bind('<Configure>', lambda _: self._draw_tree())

    def _build_topbar(self):
        top = tk.Frame(self.root, bg=C_BG, pady=6)
        top.pack(fill='x', padx=10)

        tk.Label(top, text="Search Visualiser", font=("Segoe UI", 13, "bold"),
                 bg=C_BG, fg=C_TEXT).pack(side='left', padx=(0, 16))

        tk.Button(top, text="Open Map", command=self._load_file,
                  bg=C_PANEL, fg=C_TEXT, relief='flat', padx=10, pady=3,
                  font=("Segoe UI", 9)).pack(side='left', padx=3)

        self.file_lbl = tk.Label(top, text="no file loaded",
                                  bg=C_BG, fg=C_SUBTEXT, font=("Segoe UI", 9))
        self.file_lbl.pack(side='left', padx=8)

        tk.Label(top, text="Method:", bg=C_BG, fg=C_TEXT,
                 font=("Segoe UI", 9)).pack(side='left', padx=(18, 3))
        self.method_var = tk.StringVar(value='BFS')
        ttk.Combobox(top, textvariable=self.method_var, width=7,
                     values=list(GEN_METHODS.keys()),
                     state='readonly').pack(side='left', padx=3)

        tk.Label(top, text="Speed:", bg=C_BG, fg=C_TEXT,
                 font=("Segoe UI", 9)).pack(side='left', padx=(18, 3))
        self.speed_var = tk.StringVar(value='Medium')
        sp = ttk.Combobox(top, textvariable=self.speed_var, width=10,
                          values=[s[0] for s in self.SPEEDS], state='readonly')
        sp.pack(side='left', padx=3)
        sp.bind('<<ComboboxSelected>>', self._on_speed_change)

        # control buttons live on the right
        bf = tk.Frame(top, bg=C_BG)
        bf.pack(side='right', padx=6)
        self.btn_run = self._make_btn(bf, "▶  Run",    "#a6e3a1", self._toggle_run)
        self._make_btn(bf, "⏭  Step",   "#89b4fa", self._step)
        self._make_btn(bf, "↺  Reset",  "#f38ba8", self._reset)

    def _build_main_panes(self):
        panes = tk.Frame(self.root, bg=C_BG)
        panes.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        # left: environment graph
        gf = tk.Frame(panes, bg=C_BG)
        gf.pack(side='left', fill='both', expand=True)
        tk.Label(gf, text="Environment  (graph)", bg=C_BG, fg=C_TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor='w')
        self.g_canvas = tk.Canvas(gf, bg=C_CANVAS,
                                   highlightthickness=1, highlightbackground=C_PANEL)
        self.g_canvas.pack(fill='both', expand=True)

        # right: search tree (fixed width, scrollable)
        tf = tk.Frame(panes, bg=C_BG, width=430)
        tf.pack(side='right', fill='both')
        tf.pack_propagate(False)
        tk.Label(tf, text="Search Tree", bg=C_BG, fg=C_TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor='w')

        tc = tk.Frame(tf, bg=C_CANVAS, highlightthickness=1, highlightbackground=C_PANEL)
        tc.pack(fill='both', expand=True)

        sy = tk.Scrollbar(tc, orient='vertical')
        sy.pack(side='right', fill='y')
        sx = tk.Scrollbar(tc, orient='horizontal')
        sx.pack(side='bottom', fill='x')

        self.t_canvas = tk.Canvas(tc, bg=C_CANVAS, highlightthickness=0,
                                   yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.t_canvas.pack(fill='both', expand=True)
        sy.config(command=self.t_canvas.yview)
        sx.config(command=self.t_canvas.xview)

    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=C_PANEL, pady=3)
        sb.pack(fill='x', padx=10, pady=(0, 4))

        self.status_var = tk.StringVar(value="Load a map file to begin.")
        self.info_var   = tk.StringVar(value="")

        # left side: what the algorithm is currently doing
        tk.Label(sb, textvariable=self.status_var, bg=C_PANEL, fg=C_TEXT,
                 font=("Segoe UI", 9), anchor='w').pack(side='left', padx=10)

        # right side: solution summary (appears only when done)
        tk.Label(sb, textvariable=self.info_var, bg=C_PANEL, fg=C_SOLUTION,
                 font=("Segoe UI", 9, "bold"), anchor='e').pack(side='right', padx=10)

    def _build_legend(self):
        lf = tk.Frame(self.root, bg=C_BG)
        lf.pack(fill='x', padx=10, pady=(0, 6))

        for color, label in [
            (C_ORIGIN,   "Origin"),
            (C_DEST,     "Destination"),
            (C_CURRENT,  "Current"),
            (C_FRONTIER, "Frontier"),
            (C_VISITED,  "Visited"),
            (C_SOLUTION, "Solution"),
            (C_DEFAULT,  "Unvisited"),
        ]:
            dot = tk.Canvas(lf, width=12, height=12, bg=C_BG, highlightthickness=0)
            dot.create_oval(1, 1, 11, 11, fill=color, outline="")
            dot.pack(side='left', padx=(5, 2))
            tk.Label(lf, text=label, bg=C_BG, fg=C_TEXT,
                     font=("Segoe UI", 8)).pack(side='left', padx=(0, 8))

    def _make_btn(self, parent, text, color, cmd):
        # small helper so button creation isn't repeated six times
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg="#1e1e2e", relief='flat',
                      padx=10, pady=3, font=("Segoe UI", 9, "bold"))
        b.pack(side='left', padx=3)
        return b

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_speed_change(self, *_):
        # sync the delay_ms whenever the user picks a different speed
        name = self.speed_var.get()
        for label, ms in self.SPEEDS:
            if label == name:
                self.delay_ms = ms
                break

    def _load_file(self):
        fn = filedialog.askopenfilename(
            title="Select Map File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir="D:\\python\\ai_2a\\maps",
        )
        if not fn:
            return
        try:
            self.origin, self.destinations, self.nodes, self.edges = parse_file(fn)
            self.filename = fn
            self.file_lbl.config(text=fn.split("\\")[-1])
            self._reset()
            self.status_var.set(
                f"Loaded {fn.split(chr(92))[-1]}  —  "
                f"{len(self.nodes)} nodes | origin={self.origin} | dest={self.destinations}"
            )
        except Exception as e:
            messagebox.showerror("Parse Error", str(e))

    def _reset(self):
        # cancel any running animation and wipe all search state back to a clean slate
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.running    = False
        self.generator  = None
        self.visited    = set()
        self.frontier   = set()
        self.current    = None
        self.cur_path   = []
        self.sol_path   = []
        self.parent_map = {}
        self.finished   = False

        self.btn_run.config(text="▶  Run")
        self.info_var.set("")

        if self.filename:
            self.status_var.set(f"Ready — {self.filename.split(chr(92))[-1]}")
        else:
            self.status_var.set("Load a map file to begin.")

        self._draw_graph()
        self._draw_tree()

    def _toggle_run(self):
        # pressing Run while running pauses it; pressing again resumes
        if self.finished:
            return
        if self.running:
            self.running = False
            self.btn_run.config(text="▶  Run")
            return
        if not self._ensure_generator():
            return
        self.running = True
        self.btn_run.config(text="⏸  Pause")
        self._auto_step()

    def _auto_step(self):
        # keeps calling _do_step on a timer until paused, finished, or no more events
        if not self.running:
            return
        done = self._do_step()
        if done:
            self.running = False
            self.btn_run.config(text="▶  Run")
            return
        ms = max(1, self.delay_ms) if self.delay_ms > 0 else 1
        self.after_id = self.root.after(ms, self._auto_step)

    def _step(self):
        # manually advance exactly one event (useful for following the logic closely)
        if self.finished:
            return
        if not self._ensure_generator():
            return
        self._do_step()

    def _ensure_generator(self):
        # lazily create the generator the first time Run or Step is pressed
        if not self.nodes:
            messagebox.showwarning("No file", "Please load a map file first.")
            return False
        if self.generator is None:
            gen_fn = GEN_METHODS[self.method_var.get()]
            self.generator = gen_fn(self.origin, self.destinations,
                                    self.nodes, self.edges)
        return True

    def _do_step(self):
        # pull one event from the generator and update the visualisation state
        try:
            ev = next(self.generator)
        except StopIteration:
            self.finished = True
            self.status_var.set("Generator exhausted.")
            self._draw_graph()
            self._draw_tree()
            return True

        kind = ev[0]

        if kind == 'frontier':
            # a new node just got added to the queue / stack / heap
            _, nbr, par, pm = ev
            self.parent_map = pm
            self.frontier.add(nbr)
            self.status_var.set(f"Frontier ← node {nbr}  (parent: {par})")

        elif kind == 'visit':
            # a node is being expanded — move it from frontier to visited
            _, node, path, cost, pm = ev
            self.parent_map = pm
            self.current    = node
            self.cur_path   = path
            self.frontier.discard(node)
            self.visited.add(node)
            self.status_var.set(
                f"Expanding node {node}  |  path cost: {cost:.2f}  |  created: {len(pm)}"
            )

        elif kind == 'done':
            # we found a goal — highlight the winning path
            _, goal, path, cost, created = ev
            self.sol_path = path
            self.cur_path = path
            self.current  = goal
            self.finished = True
            pstr = ' → '.join(str(n) for n in path)
            self.status_var.set(f"Solution found!  {pstr}")
            self.info_var.set(
                f"Goal: {goal}  |  Cost: {cost:.2f}  |  Nodes created: {created}"
            )

        elif kind == 'no_solution':
            self.finished = True
            self.status_var.set("No solution found.")

        self._draw_graph()
        self._draw_tree()
        return self.finished

    # ── Graph drawing ──────────────────────────────────────────────────────────

    def _graph_xy(self, nid):
        # converts a node's map coordinates to canvas pixel coordinates.
        # Y is flipped so that higher map Y = higher on screen (standard math axes)
        w   = self.g_canvas.winfo_width()  or 500
        h   = self.g_canvas.winfo_height() or 400
        xs  = [p[0] for p in self.nodes.values()]
        ys  = [p[1] for p in self.nodes.values()]
        rx  = (max(xs) - min(xs)) or 1
        ry  = (max(ys) - min(ys)) or 1
        pad = self.PAD
        cx  = pad + (self.nodes[nid][0] - min(xs)) / rx * (w - 2 * pad)
        cy  = pad + (1 - (self.nodes[nid][1] - min(ys)) / ry) * (h - 2 * pad)
        return cx, cy

    def _node_color(self, nid):
        # priority order matters: solution > current > frontier > visited > origin > dest
        if self.sol_path and nid in self.sol_path:
            return C_SOLUTION
        if nid == self.current:
            return C_CURRENT
        if nid in self.frontier:
            return C_FRONTIER
        if nid in self.visited:
            return C_VISITED
        if nid == self.origin:
            return C_ORIGIN
        if nid in self.destinations:
            return C_DEST
        return C_DEFAULT

    def _draw_graph(self):
        c = self.g_canvas
        c.delete('all')

        if not self.nodes:
            c.create_text(
                (c.winfo_width() or 300) // 2,
                (c.winfo_height() or 200) // 2,
                text="Load a map file to begin",
                fill=C_SUBTEXT, font=("Segoe UI", 11)
            )
            return

        # highlight edges that are part of the solution path
        sol_edges = set()
        if len(self.sol_path) >= 2:
            sol_edges = set(zip(self.sol_path, self.sol_path[1:]))

        # draw edges first so nodes appear on top
        for n1, neighbours in self.edges.items():
            if n1 not in self.nodes:
                continue
            x1, y1 = self._graph_xy(n1)
            for n2, cost in neighbours:
                if n2 not in self.nodes:
                    continue
                x2, y2   = self._graph_xy(n2)
                is_sol   = (n1, n2) in sol_edges
                c.create_line(x1, y1, x2, y2,
                               fill=C_EDGE_SOL if is_sol else C_EDGE,
                               width=3 if is_sol else 1,
                               arrow='last', arrowshape=(9, 11, 4))
                # tiny cost label near the midpoint
                mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                c.create_text(mx + 3, my - 9, text=f"{cost:.0f}",
                               fill=C_SUBTEXT, font=("Segoe UI", 7))

        # draw nodes
        r        = self.NODE_R
        dest_set = set(self.destinations)
        for nid in self.nodes:
            x, y  = self._graph_xy(nid)
            color = self._node_color(nid)
            # extra ring around origin and destination nodes so they stand out
            if nid == self.origin or nid in dest_set:
                c.create_oval(x - r - 4, y - r - 4, x + r + 4, y + r + 4,
                               outline=color, width=2, fill="")
            c.create_oval(x - r, y - r, x + r, y + r,
                           fill=color, outline=C_BG, width=2)
            c.create_text(x, y, text=str(nid), fill=C_BG,
                          font=("Segoe UI", 9, "bold"))

    # ── Tree drawing ───────────────────────────────────────────────────────────

    def _tree_positions(self):
        # computes (x, y) grid coordinates for each node in the tree.
        # x is assigned by a post-order traversal (leaves get unique slots,
        # parents sit centred above their children), y is simply the depth.
        if not self.parent_map:
            return {}, {}

        # build a children map from the parent_map the algorithm gave us
        children = {n: [] for n in self.parent_map}
        for node, par in self.parent_map.items():
            if par is not None:
                children.setdefault(par, [])
                if node not in children[par]:
                    children[par].append(node)

        root = self.origin
        if root not in children:
            return {}, children

        # iterative post-order traversal to assign horizontal (x) positions
        x_pos   = {}
        counter = [0]
        stack   = [(root, False)]
        while stack:
            node, done = stack.pop()
            if done:
                kids = [k for k in children.get(node, []) if k in x_pos]
                if kids:
                    # centre the parent above its leftmost and rightmost children
                    x_pos[node] = (x_pos[kids[0]] + x_pos[kids[-1]]) / 2
                else:
                    x_pos[node] = counter[0]
                    counter[0] += 1
            else:
                stack.append((node, True))
                for ch in reversed(children.get(node, [])):
                    stack.append((ch, False))

        # BFS to assign depth (y) — root is 0, children are 1, grandchildren 2, ...
        depth = {root: 0}
        q     = deque([root])
        while q:
            n = q.popleft()
            for ch in children.get(n, []):
                depth[ch] = depth[n] + 1
                q.append(ch)

        positions = {n: (x_pos[n], depth.get(n, 0)) for n in x_pos}
        return positions, children

    def _draw_tree(self):
        c = self.t_canvas
        c.delete('all')

        if not self.parent_map:
            c.create_text(160, 80,
                          text="Tree appears here once search starts",
                          fill=C_SUBTEXT, font=("Segoe UI", 9), justify='center')
            return

        positions, children = self._tree_positions()
        if not positions:
            return

        XG = self.XGAP
        YG = self.YGAP
        r  = self.TREE_R

        # size the scroll region to fit the whole tree
        max_x = max(p[0] for p in positions.values())
        max_y = max(p[1] for p in positions.values())
        W = max((max_x + 1) * XG + 40, 400)
        H = max((max_y + 1) * YG + 60, 200)
        c.config(scrollregion=(0, 0, W, H))

        def px(nid):
            # converts grid (col, depth) into canvas pixels
            gx, gy = positions[nid]
            return gx * XG + 30, gy * YG + 30

        sol_set = set(self.sol_path)

        # draw edges between parent and child nodes
        for par, kids in children.items():
            if par not in positions:
                continue
            x1, y1 = px(par)
            for ch in kids:
                if ch not in positions:
                    continue
                x2, y2 = px(ch)
                # check if both endpoints are consecutive on the solution path
                is_sol = (
                    par in sol_set and ch in sol_set and self.sol_path
                    and any(
                        self.sol_path[i] == par and self.sol_path[i + 1] == ch
                        for i in range(len(self.sol_path) - 1)
                    )
                )
                c.create_line(x1, y1 + r, x2, y2 - r,
                               fill=C_EDGE_SOL if is_sol else C_EDGE,
                               width=2 if is_sol else 1)

        # draw nodes on top of edges
        for nid in positions:
            x, y  = px(nid)
            color = self._node_color(nid)
            c.create_oval(x - r, y - r, x + r, y + r,
                           fill=color, outline=C_BG, width=1)
            c.create_text(x, y, text=str(nid), fill=C_BG,
                          font=("Segoe UI", 8, "bold"))
            # "root" label under the origin node
            if positions[nid][1] == 0:
                c.create_text(x, y + r + 8, text="root",
                               fill=C_SUBTEXT, font=("Segoe UI", 7))
