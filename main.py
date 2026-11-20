import tkinter as tk
from widget import DesktopWidget


def main():
    root = tk.Tk()
    DesktopWidget(root)
    root.mainloop()


if __name__ == "__main__":
    main()