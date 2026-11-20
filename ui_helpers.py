import tkinter as tk
from theme import (BG, ACCENT, ACCENT_D, BTN_BG, BTN_HOVER, FONT_SECT,
                   GLOW_INNER, GLOW_OUTER)


def glow_wrap(parent, outer=GLOW_OUTER, mid=GLOW_INNER):
    """
    Возвращает (outer_frame, inner_frame).
    Кладёшь содержимое в inner_frame — получаешь двухслойный ореол.
    """
    outer_f = tk.Frame(parent, bg=outer, padx=1, pady=1)
    inner_f = tk.Frame(outer_f, bg=mid, padx=1, pady=1)
    inner_f.pack(fill="both", expand=True)
    return outer_f, inner_f


class AnimatedButton(tk.Button):
    def __init__(self, master, anim_ms=140, **kw):
        self._base_bg = kw.get("bg", BTN_BG)
        self._hover_bg = kw.pop("hover_bg", BTN_HOVER)
        self._anim_ms = anim_ms
        self._steps = 8
        self._job = None
        super().__init__(master, **kw)
        self.bind("<Enter>", lambda e: self._animate_to(self._hover_bg))
        self.bind("<Leave>", lambda e: self._animate_to(self._base_bg))

    @staticmethod
    def _hex2rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _rgb2hex(rgb):
        return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)

    def _animate_to(self, target_hex: str):
        if self._job:
            self.after_cancel(self._job)
        start = self._hex2rgb(self.cget("bg"))
        end = self._hex2rgb(target_hex)
        step = [0]

        def tick():
            step[0] += 1
            t = step[0] / self._steps
            cur = tuple(start[i] + (end[i] - start[i]) * t for i in range(3))
            try:
                self.config(bg=self._rgb2hex(cur))
            except tk.TclError:
                return
            if step[0] < self._steps:
                self._job = self.after(max(8, self._anim_ms // self._steps), tick)

        tick()


def section_header(parent, title, add_cb):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=(0, 1))
    tk.Label(row, text=title, font=FONT_SECT,
             fg=ACCENT, bg=BG).pack(side="left")
    tk.Button(
        row, text="+", font=("Segoe UI", 10, "bold"),
        fg=ACCENT, bg=BG, activebackground=ACCENT, activeforeground=BG,
        bd=0, padx=4, command=add_cb
    ).pack(side="right")