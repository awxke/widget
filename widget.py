import os
import threading
import time
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from datetime import datetime
import ctypes

from theme import (BG, ACCENT, TEXT, TEXT_DIM, BTN_BG, FONT_TIME,
                   FONT_SECT, FONT_BTN)
from config import load_config, save_config
from weather import fetch_weather, geocode_city, WEATHER_EMOJI
from launcher import open_url, open_game, extract_exe_icon
from ui_helpers import AnimatedButton, section_header, glow_wrap
from calendar_view import CalendarView
import autostart


class DesktopWidget:
    MIN_W, MIN_H = 280, 280
    MAX_W, MAX_H = 800, 800

    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = load_config()
        self.weather_data = None
        self._locked = False
        self._resize_start = None
        self._icon_cache = {}
        self._closing = False

        self._setup_window()
        self._build_ui()
        self._start_clock()
        self._start_weather_loop()
        self._send_to_bottom()
        self._start_restore_watch()

    # ---------- окно ----------
    def _setup_window(self):
        r = self.root
        r.overrideredirect(True)
        r.configure(bg=BG)
        r.geometry("360x360+80+80")
        r.attributes("-topmost", False)
        r.attributes("-toolwindow", True)
        self._drag_x = 0
        self._drag_y = 0

    def _start_drag(self, event):
        if self._locked:
            return
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _do_drag(self, event):
        if self._locked:
            return
        self.root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    # ---------- ресайз ----------
    def _start_resize(self, event):
        self._resize_start = (event.x_root, event.y_root,
                              self.root.winfo_width(), self.root.winfo_height())

    def _do_resize(self, event):
        if not self._resize_start:
            return
        sx, sy, sw, sh = self._resize_start
        dx = event.x_root - sx
        dy = event.y_root - sy
        w = max(self.MIN_W, min(self.MAX_W, sw + dx))
        h = max(self.MIN_H, min(self.MAX_H, sh + dy))
        self.root.geometry(f"{w}x{h}")

    def _end_resize(self, event):
        self._resize_start = None

    # ---------- «на рабочем столе» ----------
    def _send_to_bottom(self):
        try:
            HWND_BOTTOM = 1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            user32 = ctypes.windll.user32
            hwnd = user32.GetAncestor(self.root.winfo_id(), 2)
            user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        except Exception:
            pass

    def _start_restore_watch(self):
        def worker():
            user32 = ctypes.windll.user32
            SW_SHOWNOACTIVATE = 4
            while not self._closing:
                try:
                    hwnd = user32.GetAncestor(self.root.winfo_id(), 2)
                    if hwnd and not user32.IsWindowVisible(hwnd):
                        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
                        self.root.after(0, self._send_to_bottom)
                except Exception:
                    pass
                time.sleep(0.25)

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_lock(self):
        self._locked = not self._locked
        self.lock_btn.config(
            text="🔒" if self._locked else "🔓",
            fg=ACCENT if self._locked else TEXT_DIM
        )

    def _toggle_autostart(self):
        try:
            enabled = autostart.toggle_autostart()
            self.autostart_btn.config(fg=ACCENT if enabled else TEXT_DIM)
        except Exception as e:
            messagebox.showerror("Автозапуск", f"Не удалось:\n{e}", parent=self.root)

    def _close(self):
        self._closing = True
        self.root.destroy()

    # ---------- UI ----------
    def _build_ui(self):
        r = self.root

        header = tk.Frame(r, bg=BG)
        header.pack(fill="x", padx=10, pady=(8, 0))
        header.bind("<Button-1>", self._start_drag)
        header.bind("<B1-Motion>", self._do_drag)

        self.time_label = tk.Label(header, text="", font=FONT_TIME, fg=TEXT, bg=BG)
        self.time_label.pack(side="left")
        self.time_label.bind("<Button-1>", self._start_drag)
        self.time_label.bind("<B1-Motion>", self._do_drag)

        btn_box = tk.Frame(header, bg=BG)
        btn_box.pack(side="right")

        self.autostart_btn = tk.Button(
            btn_box, text="⚡", font=("Segoe UI", 9),
            fg=(ACCENT if autostart.is_autostart_enabled() else TEXT_DIM),
            bg=BG, activebackground=ACCENT, activeforeground=BG,
            bd=0, padx=4, command=self._toggle_autostart
        )
        self.autostart_btn.pack(side="left")

        self.lock_btn = tk.Button(
            btn_box, text="🔓", font=("Segoe UI", 9),
            fg=TEXT_DIM, bg=BG, activebackground=ACCENT, activeforeground=BG,
            bd=0, padx=4, command=self._toggle_lock
        )
        self.lock_btn.pack(side="left")

        tk.Button(
            btn_box, text="×", font=("Segoe UI", 12, "bold"),
            fg=TEXT_DIM, bg=BG, activebackground="#ff4466", activeforeground=BG,
            bd=0, padx=4, command=self._close
        ).pack(side="left")

        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self._build_left(left)
        self.calendar = CalendarView(right, self.config, self.root)

        self.root.after(0, lambda: self._render_list("games"))
        self.root.after(0, lambda: self._render_list("sites"))

        grip = tk.Label(r, text="◢", font=("Segoe UI", 10),
                        fg=ACCENT, bg=BG, cursor="bottom_right_corner")
        grip.place(relx=1.0, rely=1.0, x=-4, y=-4, anchor="se")
        grip.bind("<Button-1>", self._start_resize)
        grip.bind("<B1-Motion>", self._do_resize)
        grip.bind("<ButtonRelease-1>", self._end_resize)

    def _build_left(self, parent):
        section_header(parent, "ИГРЫ", lambda: self._add_entry("games"))
        self.games_frame = tk.Frame(parent, bg=BG)
        self.games_frame.pack(fill="x")

        section_header(parent, "САЙТЫ", lambda: self._add_entry("sites"))
        self.sites_frame = tk.Frame(parent, bg=BG)
        self.sites_frame.pack(fill="x")

        tk.Label(parent, text="ПОГОДА", font=FONT_SECT,
                 fg=ACCENT, bg=BG).pack(anchor="w", pady=(8, 0))

        outer, inner = glow_wrap(parent)
        outer.pack(fill="x", pady=(2, 0))

        weather_box = tk.Frame(inner, bg=BTN_BG)
        weather_box.pack(fill="x")

        self.weather_label = tk.Label(
            weather_box, text="...", font=("Segoe UI", 9),
            fg=TEXT, bg=BTN_BG, anchor="w", padx=8, pady=6
        )
        self.weather_label.pack(side="left", fill="x", expand=True)

        tk.Button(
            weather_box, text="⚙", font=("Segoe UI", 9),
            fg=ACCENT, bg=BTN_BG, activebackground=ACCENT, activeforeground=BG,
            bd=0, padx=4, command=self._edit_weather_city
        ).pack(side="right")

    # ---------- иконки ----------
    def _get_icon(self, item: dict, kind: str):
        if kind != "games":
            return None
        path = item.get("path", "")
        if not path or path.startswith(("http://", "https://")):
            return None
        if path in self._icon_cache:
            return self._icon_cache[path]
        icon = extract_exe_icon(path, size=16)
        if icon:
            self._icon_cache[path] = icon
        return icon

    # ---------- списки ----------
    def _render_list(self, kind: str):
        frame = self.games_frame if kind == "games" else self.sites_frame
        for w in frame.winfo_children():
            w.destroy()

        items = self.config[kind]
        if not items:
            tk.Label(frame, text="— пусто —", font=("Segoe UI", 7),
                     fg=TEXT_DIM, bg=BG).pack(anchor="w")
            return

        for i, item in enumerate(items):
            row = tk.Frame(frame, bg=BG)
            row.pack(fill="x", pady=1)

            outer, inner = glow_wrap(row)
            outer.pack(side="left", fill="x", expand=True)

            icon = self._get_icon(item, kind)
            if icon:
                b = tk.Button(
                    inner, text=" " + item["name"], image=icon,
                    compound="left", anchor="w",
                    font=FONT_BTN, fg=TEXT, bg=BTN_BG,
                    activebackground=ACCENT, activeforeground=BG,
                    bd=0, padx=6, pady=2, cursor="hand2",
                    command=lambda e=item: open_game(e)
                )
            else:
                b = AnimatedButton(
                    inner, text=item["name"], anchor="w",
                    font=FONT_BTN, fg=TEXT, bg=BTN_BG,
                    activebackground=ACCENT, activeforeground=BG,
                    bd=0, padx=6, pady=3, cursor="hand2",
                    command=(lambda e=item: open_game(e)) if kind == "games"
                    else (lambda e=item: open_url(e["url"]))
                )
            b.pack(fill="x")
            b.bind("<Button-3>", lambda ev, k=kind, idx=i: self._confirm_delete(k, idx))

            del_btn = tk.Button(
                row, text="×", font=("Segoe UI", 9, "bold"),
                fg=TEXT_DIM, bg=BG,
                activebackground="#ff4466", activeforeground=BG,
                bd=0, padx=4,
                command=lambda k=kind, idx=i: self._confirm_delete(k, idx)
            )
            del_btn.pack(side="right", padx=(4, 0))

        frame.update_idletasks()

    def _add_entry(self, kind: str):
        name = simpledialog.askstring("Добавить", "Название:", parent=self.root)
        if not name:
            return

        if kind == "sites":
            url = simpledialog.askstring("Добавить", "URL:", parent=self.root)
            if not url:
                return
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            entry = {"name": name, "url": url}
        else:
            path = filedialog.askopenfilename(
                title="Выбери exe или ярлык",
                filetypes=[("Исполняемые / ярлыки", "*.exe *.lnk *.bat"),
                           ("Все файлы", "*.*")],
                parent=self.root,
            )
            if not path:
                manual = simpledialog.askstring(
                    "Или URL", "Если игра браузерная — вставь ссылку:",
                    parent=self.root,
                )
                if not manual:
                    return
                if not manual.startswith(("http://", "https://")):
                    manual = "https://" + manual
                entry = {"name": name, "path": manual}
            else:
                entry = {"name": name, "path": os.path.normpath(path)}

        self.config[kind].append(entry)
        save_config(self.config)
        self._render_list(kind)

    def _confirm_delete(self, kind: str, index: int):
        try:
            name = self.config[kind][index]["name"]
        except IndexError:
            return
        if messagebox.askyesno("Удалить", f"Удалить «{name}»?", parent=self.root):
            del self.config[kind][index]
            save_config(self.config)
            self._render_list(kind)

    # ---------- погода ----------
    def _edit_weather_city(self):
        city = simpledialog.askstring(
            "Город", "Название города:",
            initialvalue=self.config["weather"]["city"],
            parent=self.root,
        )
        if not city:
            return
        geo = geocode_city(city)
        if not geo:
            messagebox.showerror("Ошибка", "Город не найден", parent=self.root)
            return
        self.config["weather"] = geo
        save_config(self.config)
        threading.Thread(target=self._refresh_weather_once, daemon=True).start()

    def _refresh_weather_once(self):
        w = self.config["weather"]
        self.weather_data = fetch_weather(w["lat"], w["lon"])
        self.root.after(0, self._update_weather_label)

    def _update_weather_label(self):
        w = self.config["weather"]
        d = self.weather_data
        if d is None:
            self.weather_label.config(text=f"{w['city']} — —")
            return
        emoji = WEATHER_EMOJI.get(d["code"], "🌡️")
        self.weather_label.config(text=f"{w['city']} {emoji} {d['temp']}°")

    # ---------- циклы ----------
    def _start_clock(self):
        def tick():
            self.time_label.config(text=datetime.now().strftime("%H:%M"))
            self.root.after(1000, tick)
        tick()

    def _start_weather_loop(self):
        def worker():
            while True:
                self._refresh_weather_once()
                time.sleep(600)
        threading.Thread(target=worker, daemon=True).start()