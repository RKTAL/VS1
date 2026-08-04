# TETRIS - Classic arcade puzzle game
# Controls: Left/Right move, Up rotate, Down soft drop, Space hard drop
#           C = hold piece, P = pause, R = restart

import tkinter as tk
import random
import json
from pathlib import Path

COLS, ROWS = 10, 20
CELL = 26
W = COLS * CELL
H = ROWS * CELL
DATA = Path(__file__).parent / "tetris_data.json"

# Tetromino shapes
SHAPES = {
    'I': [(0,0),(0,1),(0,2),(0,3)],
    'O': [(0,0),(0,1),(1,0),(1,1)],
    'T': [(0,1),(1,0),(1,1),(1,2)],
    'S': [(1,0),(1,1),(0,1),(0,2)],
    'Z': [(0,0),(0,1),(1,1),(1,2)],
    'J': [(0,0),(1,0),(1,1),(1,2)],
    'L': [(0,2),(1,0),(1,1),(1,2)],
}
COLORS = {
    'I': '#00d4ff', 'O': '#ffd700', 'T': '#aa44ff',
    'S': '#44ff88', 'Z': '#ff4466', 'J': '#4488ff', 'L': '#ff8844',
}


class Tetris:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TETRIS")
        self.root.resizable(False, False)
        self.root.configure(bg="#111")
        self.hs = self._load()

        # Main canvas
        self.cv = tk.Canvas(self.root, width=W, height=H, bg="#000",
                            highlightthickness=0)
        self.cv.grid(row=0, column=0, rowspan=3, padx=(10, 6), pady=10)

        # Side panel
        self.side = tk.Frame(self.root, bg="#111")
        self.side.grid(row=0, column=1, sticky="n", pady=10)

        tk.Label(self.side, text="SCORE", fg="#555", bg="#111",
                 font=("Consolas", 9)).pack(anchor="w")
        self.sc_lbl = tk.Label(self.side, text="0", fg="#8c8", bg="#111",
                               font=("Consolas", 18, "bold"))
        self.sc_lbl.pack(anchor="w")

        tk.Label(self.side, text="LEVEL", fg="#555", bg="#111",
                 font=("Consolas", 9)).pack(anchor="w", pady=(10, 0))
        self.lv_lbl = tk.Label(self.side, text="1", fg="#cc8", bg="#111",
                               font=("Consolas", 14, "bold"))
        self.lv_lbl.pack(anchor="w")

        tk.Label(self.side, text="BEST", fg="#555", bg="#111",
                 font=("Consolas", 9)).pack(anchor="w", pady=(10, 0))
        self.hs_lbl = tk.Label(self.side, text=str(self.hs), fg="#aaa",
                               bg="#111", font=("Consolas", 14, "bold"))
        self.hs_lbl.pack(anchor="w")

        tk.Label(self.side, text="NEXT", fg="#555", bg="#111",
                 font=("Consolas", 9)).pack(anchor="w", pady=(14, 4))
        self.nx_cv = tk.Canvas(self.side, width=120, height=80, bg="#000",
                               highlightthickness=0)
        self.nx_cv.pack(anchor="w")

        tk.Label(self.side, text="HOLD (C)", fg="#555", bg="#111",
                 font=("Consolas", 9)).pack(anchor="w", pady=(14, 4))
        self.ho_cv = tk.Canvas(self.side, width=120, height=80, bg="#000",
                               highlightthickness=0)
        self.ho_cv.pack(anchor="w")

        # Controls
        tk.Label(self.root, text="\u2190\u2192 move   \u2191 rotate   \u2193 drop\n"
                 "SPACE hard drop   C hold   P pause\nR restart",
                 fg="#444", bg="#111", font=("Consolas", 9),
                 justify="left").grid(row=3, column=0, sticky="w", padx=10)

        self.reset()
        self.root.bind("<Key>", self._key)
        self.root.focus_set()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    # --- Setup ---
    def reset(self):
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.speed = 700
        self.paused = False
        self.dead = False
        self.hold = None
        self.hold_used = False
        self.bag = []
        self.falling = None
        self.ghost = None
        self.timer_id = None
        self._next_piece()
        self._spawn_piece()
        self._draw()
        self._tick()

    def _load(self):
        try:
            if DATA.exists():
                return json.loads(DATA.read_text()).get("hs", 0)
        except: pass
        return 0

    def _save(self):
        try:
            DATA.write_text(json.dumps({"hs": self.hs}))
        except: pass

    # --- Piece management ---
    def _next_piece(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        self.next = self.bag.pop()

    def _spawn_piece(self):
        kind = self.next
        self._next_piece()
        x = COLS // 2 - 1
        self.falling = {"kind": kind, "pos": [x, 0],
                        "cells": [list(c) for c in SHAPES[kind]]}
        self.ghost = self._calc_ghost()
        if self._collide(self.falling["pos"], self.falling["cells"]):
            self._game_over()

    def _rotated(self, cells):
        return [[-c[1], c[0]] for c in cells]

    def _collide(self, pos, cells):
        px, py = pos
        for c in cells:
            x, y = px + c[0], py + c[1]
            if x < 0 or x >= COLS or y >= ROWS:
                return True
            if y >= 0 and self.grid[y][x]:
                return True
        return False

    def _calc_ghost(self):
        pos = list(self.falling["pos"])
        while not self._collide([pos[0], pos[1] + 1], self.falling["cells"]):
            pos[1] += 1
        return pos

    # --- Movement ---
    def _move(self, dx):
        if self.dead or self.paused:
            return
        f = self.falling
        pos = [f["pos"][0] + dx, f["pos"][1]]
        if not self._collide(pos, f["cells"]):
            f["pos"] = pos
            self.ghost = self._calc_ghost()
            self._draw()

    def _rotate(self):
        if self.dead or self.paused:
            return
        f = self.falling
        cells = self._rotated(f["cells"])
        # Wall kicks
        for kick in (0, -1, 1, -2, 2):
            pos = [f["pos"][0] + kick, f["pos"][1]]
            if not self._collide(pos, cells):
                f["cells"] = cells
                f["pos"] = pos
                self.ghost = self._calc_ghost()
                self._draw()
                return

    def _drop(self):
        f = self.falling
        f["pos"][1] += 1
        if self._collide(f["pos"], f["cells"]):
            f["pos"][1] -= 1
            self._lock()

    def _hard_drop(self):
        if self.dead or self.paused:
            return
        f = self.falling
        g = self.ghost
        dist = g[1] - f["pos"][1]
        f["pos"] = list(g)
        self.score += dist * 2
        self._lock()

    def _lock(self):
        f = self.falling
        px, py = f["pos"]
        for c in f["cells"]:
            x, y = px + c[0], py + c[1]
            if y >= 0:
                self.grid[y][x] = f["kind"]
        self._clear_lines()
        self.hold_used = False
        self._spawn_piece()
        self._draw()

    def _clear_lines(self):
        cleared = 0
        for y in range(ROWS - 1, -1, -1):
            if all(self.grid[y]):
                del self.grid[y]
                self.grid.insert(0, [None] * COLS)
                cleared += 1
        if cleared:
            self.lines += cleared
            self.score += [0, 100, 300, 500, 800][cleared] * self.level
            self.level = self.lines // 10 + 1
            self.speed = max(120, 700 - (self.level - 1) * 60)
            if self.score > self.hs:
                self.hs = self.score
                self._save()
            self._update_panel()

    # --- Hold ---
    def _do_hold(self):
        if self.dead or self.paused or self.hold_used:
            return
        kind = self.falling["kind"]
        if self.hold is None:
            self.hold = kind
            self._spawn_piece()
        else:
            self.hold, kind = kind, self.hold
            x = COLS // 2 - 1
            self.falling = {"kind": kind, "pos": [x, 0],
                            "cells": [list(c) for c in SHAPES[kind]]}
            if self._collide(self.falling["pos"], self.falling["cells"]):
                self._game_over()
        self.hold_used = True
        self.ghost = self._calc_ghost()
        self._draw()

    # --- Game over ---
    def _game_over(self):
        self.dead = True
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        if self.score > self.hs:
            self.hs = self.score
            self._save()
            self._update_panel()
        self._draw()
        self.cv.create_text(W // 2, H // 2 - 12, text="GAME OVER",
                            fill="#c66", font=("Consolas", 24, "bold"))
        self.cv.create_text(W // 2, H // 2 + 18,
                            text=f"Score: {self.score}",
                            fill="#aaa", font=("Consolas", 13))
        self.cv.create_text(W // 2, H // 2 + 42,
                            text="Press R to restart", fill="#555",
                            font=("Consolas", 11))

    # --- Keys ---
    def _key(self, e):
        if e.keysym in ("r", "R"):
            self.reset()
            return
        if e.keysym in ("p", "P"):
            self.paused = not self.paused
            if self.paused:
                self._overlay("PAUSED")
            else:
                self._draw()
            return
        if self.dead:
            return
        if e.keysym == "Left":
            self._move(-1)
        elif e.keysym == "Right":
            self._move(1)
        elif e.keysym == "Up":
            self._rotate()
        elif e.keysym == "Down":
            self._drop()
        elif e.keysym == "space":
            self._hard_drop()
        elif e.keysym in ("c", "C"):
            self._do_hold()

    def _overlay(self, text):
        self._draw()
        self.cv.create_text(W // 2, H // 2, text=text, fill="#aaa",
                            font=("Consolas", 22, "bold"))

    # --- Loop ---
    def _tick(self):
        if not self.dead and not self.paused:
            self._drop()
        if not self.dead:
            self.timer_id = self.root.after(self.speed, self._tick)

    # --- Drawing ---
    def _draw(self):
        self.cv.delete("all")
        # Grid lines
        for x in range(COLS + 1):
            self.cv.create_line(x * CELL, 0, x * CELL, H, fill="#0a0a0a")
        for y in range(ROWS + 1):
            self.cv.create_line(0, y * CELL, W, y * CELL, fill="#0a0a0a")
        # Locked pieces
        for y in range(ROWS):
            for x in range(COLS):
                k = self.grid[y][x]
                if k:
                    self._cell(x, y, COLORS[k])
        # Ghost
        if self.falling and self.ghost:
            gx, gy = self.ghost
            for c in self.falling["cells"]:
                self._cell(gx + c[0], gy + c[1], "#333", outline=True)
        # Falling piece
        if self.falling:
            px, py = self.falling["pos"]
            color = COLORS[self.falling["kind"]]
            for c in self.falling["cells"]:
                self._cell(px + c[0], py + c[1], color)
        # Next piece preview
        self.nx_cv.delete("all")
        if hasattr(self, "next"):
            self._preview(self.nx_cv, self.next)
        # Hold preview
        self.ho_cv.delete("all")
        if self.hold:
            self._preview(self.ho_cv, self.hold, dim=self.hold_used)

    def _cell(self, x, y, color, outline=False):
        px, py = x * CELL, y * CELL
        m = 1
        self.cv.create_rectangle(px + m, py + m, px + CELL - m, py + CELL - m,
                                 fill=color, outline="#000", width=1)
        if outline:
            self.cv.create_rectangle(px + m, py + m, px + CELL - m,
                                     py + CELL - m, outline="#555",
                                     width=1)

    def _preview(self, cv, kind, dim=False):
        cells = SHAPES[kind]
        # Normalize to fit
        min_x = min(c[0] for c in cells)
        max_x = max(c[0] for c in cells)
        min_y = min(c[1] for c in cells)
        max_y = max(c[1] for c in cells)
        nw = (max_x - min_x + 1) * 24
        nh = (max_y - min_y + 1) * 24
        ox = (120 - nw) / 2 - min_x * 24
        oy = (80 - nh) / 2 - min_y * 24
        color = COLORS[kind] if not dim else "#333"
        for c in cells:
            x = ox + c[0] * 24
            y = oy + c[1] * 24
            cv.create_rectangle(x + 1, y + 1, x + 23, y + 23,
                                fill=color, outline="#000")

    def _update_panel(self):
        self.sc_lbl.config(text=str(self.score))
        self.lv_lbl.config(text=str(self.level))
        self.hs_lbl.config(text=str(self.hs))

    def _close(self):
        self._save()
        self.root.destroy()


if __name__ == "__main__":
    Tetris()
