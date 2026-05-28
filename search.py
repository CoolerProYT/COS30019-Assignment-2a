import sys
import os

from algorithms import parse_file, print_result, METHODS

MAPS_DIR = os.path.join(os.path.dirname(__file__), "maps")

def resolve_file(filename):
    # if the file exists as typed, use it, otherwise try the maps/ folder
    # so users can just write "Map1.txt" instead of "maps/Map1.txt"
    if os.path.exists(filename):
        return filename
    candidate = os.path.join(MAPS_DIR, filename)
    if os.path.exists(candidate):
        return candidate
    return filename

def run_cli(filename, method_name):
    # validates inputs, runs the chosen algorithm, and prints the result
    if method_name not in METHODS:
        print(f"Unknown method '{method_name}'. Choose from: {', '.join(METHODS.keys())}")
        sys.exit(1)

    filename = resolve_file(filename)
    try:
        origin, destinations, nodes, edges = parse_file(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")
        sys.exit(1)

    goal, num_nodes, path, path_cost = METHODS[method_name](
        origin, destinations, nodes, edges
    )
    print_result(method_name, origin, goal, num_nodes, path, path_cost)

def run_gui(preload_file=None):
    # tkinter is imported here so CLI mode doesn't need a display at all
    import tkinter as tk
    from gui import SearchGUI

    root = tk.Tk()
    app  = SearchGUI(root)

    if preload_file:
        try:
            preload_file = resolve_file(preload_file)
            app.origin, app.destinations, app.nodes, app.edges = parse_file(preload_file)
            app.filename = preload_file
            app.file_lbl.config(text=preload_file.split("\\")[-1])
            app._reset()
            app.status_var.set(f"Loaded {preload_file.split(chr(92))[-1]}")
        except Exception:
            pass  # if the file is bad, just open an empty GUI — no crash

    root.mainloop()

def main():
    args = sys.argv[1:]

    # no arguments, or --gui flag then open the visual interface
    if not args or args[0] == '--gui':
        preload = args[1] if len(args) >= 2 else None
        run_gui(preload)
        return

    # two arguments then run CLI mode
    if len(args) >= 2:
        run_cli(filename=args[0], method_name=args[1].upper())
        return

    print("Usage: python search.py <filename> <method>")
    print(f"       python search.py --gui [filename]")
    print(f"Methods: {', '.join(METHODS.keys())}")
    sys.exit(1)

if __name__ == '__main__':
    main()
