import calendar
import tkinter as tk
from datetime import date
from tkinter import simpledialog

from theme import (BG, ACCENT, ACCENT_D, TEXT, TEXT_DIM, CIRCLE, BORDER,
                   BTN_HOVER, FONT_CAL, FONT_CAL_WD, FONT_MONTH, FONT_EVENT,
                   WEEKDAYS, MONTHS_RU)
from config import save_config


class CalendarView:
    """Календарь с квадратными ячейками и описанием при наведении."""

    def __init__(self, parent, config, root):
        self.parent = parent
        self.config = config
        self.root = root
        self.year = date.today().year
        self.month = date.today().month

        self._build()

    def _build(self):
        head = tk.Frame(self.parent, bg=BG)
        head.pack(fill="x")

        tk.Button(head, text="‹", font=("Segoe UI", 10, "bold"),
                  fg=ACCENT, bg=BG, bd=0, padx=4,
                  command=lambda: self._shift(-1)).pack(side="left")

        self.month_label = tk.Label(head, text="", font=FONT_MONTH,
                                    fg=TEXT, bg=BG)
        self.month_label.pack(side="left", expand=True)

        tk.Button(head, text="›", font=("Segoe UI", 10, "bold"),
                  fg=ACCENT, bg=BG, bd=0, padx=4,
                  command=lambda: self._shift(1)).pack(side="right")

        self.grid_frame = tk.Frame(self.parent, bg=BG)
        self.grid_frame.pack(fill="x", pady=(2, 0))

        # Описание дня при наведении
        self.event_label = tk.Label(
            self.parent, text="", font=FONT_EVENT,
            fg=ACCENT, bg=BG, anchor="w", justify="left",
            wraplength=160, height=2
        )
        self.event_label.pack(fill="x", pady=(4, 0))

        self.render()

    def _shift(self, delta: int):
        m = self.month + delta
        y = self.year
        if m < 1:
            m = 12; y -= 1
        elif m > 12:
            m = 1; y += 1
        self.month, self.year = m, y
        self.render()

    def render(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        self.month_label.config(text=f"{MONTHS_RU[self.month-1]} {self.year}")

        for i, wd in enumerate(WEEKDAYS):
            tk.Label(self.grid_frame, text=wd, font=FONT_CAL_WD,
                     fg=TEXT_DIM, bg=BG).grid(row=0, column=i, padx=1, pady=1)

        first_wd, days_in_month = calendar.monthrange(self.year, self.month)
        today = date.today()
        row = 1
        col = first_wd

        for day in range(1, days_in_month + 1):
            d = date(self.year, self.month, day)
            is_today = (d == today)
            key = d.isoformat()
            has_event = key in self.config["events"]

            # квадратная рамка через relief + bd
            cell = tk.Label(
                self.grid_frame, text=str(day),
                font=FONT_CAL, width=2, height=1,
                fg=(BG if (has_event or is_today) else TEXT),
                bg=(CIRCLE if has_event else ACCENT_D if is_today else BG),
                relief="solid", bd=1,
                highlightthickness=0,
            )
            cell.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")

            cell.bind("<Button-1>", lambda e, dd=d: self._on_click(dd))
            cell.bind("<Enter>", lambda e, dd=d, c=cell, he=has_event, it=is_today:
                      self._on_hover(dd, c, he, it))
            cell.bind("<Leave>", lambda e, c=cell, he=has_event, it=is_today:
                      self._on_leave(c, he, it))

            col += 1
            if col > 6:
                col = 0
                row += 1

        self._update_event_label_today()

    def _on_hover(self, d: date, cell: tk.Label, has_event: bool, is_today: bool):
        if not has_event and not is_today:
            cell.config(bg=BTN_HOVER)
        ev = self.config["events"].get(d.isoformat())
        if ev:
            self.event_label.config(text=f"{d.strftime('%d.%m')} — {ev}")

    def _on_leave(self, cell: tk.Label, has_event: bool, is_today: bool):
        cell.config(bg=(CIRCLE if has_event else ACCENT_D if is_today else BG))
        self._update_event_label_today()

    def _on_click(self, d: date):
        key = d.isoformat()
        current = self.config["events"].get(key, "")
        text = simpledialog.askstring(
            f"Событие на {d.strftime('%d.%m.%Y')}",
            "Подпись (пусто — удалить):",
            initialvalue=current, parent=self.root
        )
        if text is None:
            return
        if text.strip():
            self.config["events"][key] = text.strip()
        else:
            self.config["events"].pop(key, None)
        save_config(self.config)
        self.render()

    def _update_event_label_today(self):
        ev = self.config["events"].get(date.today().isoformat())
        self.event_label.config(text=f"● {ev}" if ev else "")