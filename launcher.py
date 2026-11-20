import os
import subprocess
from tkinter import messagebox

try:
    from PIL import Image, ImageTk
    import ctypes
    from ctypes import wintypes
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def open_url(url: str):
    import webbrowser
    webbrowser.open_new(url)


def open_game(entry: dict):
    path = entry.get("path", "")
    if not path:
        return
    if path.startswith(("http://", "https://")):
        open_url(path)
        return
    exe = os.path.normpath(path)
    if not os.path.exists(exe):
        messagebox.showerror("Ошибка", f"Файл не найден:\n{exe}")
        return
    try:
        subprocess.Popen([exe], cwd=os.path.dirname(exe))
    except Exception as e:
        messagebox.showerror("Ошибка запуска", f"{exe}\n\n{e}")


def extract_exe_icon(exe_path: str, size: int = 16):
    """
    Извлекает иконку из exe/lnk через WinAPI и возвращает ImageTk.PhotoImage
    или None, если не удалось.
    """
    if not HAS_PIL or not os.path.exists(exe_path):
        return None
    if not exe_path.lower().endswith((".exe", ".lnk")):
        return None

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    shell32 = ctypes.windll.shell32

    hicon = None
    try:
        if exe_path.lower().endswith(".lnk"):
            # SHGetFileInfo для ярлыков
            SHGFI_ICON = 0x100
            SHGFI_SMALLICON = 0x1

            class SHFILEINFOW(ctypes.Structure):
                _fields_ = [
                    ("hIcon", ctypes.c_void_p),
                    ("iIcon", ctypes.c_int),
                    ("dwAttributes", wintypes.DWORD),
                    ("szDisplayName", ctypes.c_wchar * 260),
                    ("szTypeName", ctypes.c_wchar * 80),
                ]

            info = SHFILEINFOW()
            flags = SHGFI_ICON | SHGFI_SMALLICON
            res = shell32.SHGetFileInfoW(exe_path, 0, ctypes.byref(info),
                                         ctypes.sizeof(info), flags)
            if res:
                hicon = info.hIcon
        else:
            # ExtractIconExW живёт в shell32.dll, не в user32.dll
            h = ctypes.c_void_p()
            n = shell32.ExtractIconExW(exe_path, 0, ctypes.byref(h), None, 1)
            if n > 0 and h.value:
                hicon = h.value

        if not hicon:
            return None

        # HICON → ICONINFO
        class ICONINFO(ctypes.Structure):
            _fields_ = [
                ("fIcon", wintypes.BOOL),
                ("xHotspot", wintypes.DWORD),
                ("yHotspot", wintypes.DWORD),
                ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p),
            ]

        ii = ICONINFO()
        if not user32.GetIconInfo(hicon, ctypes.byref(ii)):
            return None

        class BITMAP(ctypes.Structure):
            _fields_ = [
                ("bmType", ctypes.c_long),
                ("bmWidth", ctypes.c_long),
                ("bmHeight", ctypes.c_long),
                ("bmWidthBytes", ctypes.c_long),
                ("bmPlanes", ctypes.c_ushort),
                ("bmBitsPixel", ctypes.c_ushort),
                ("bmBits", ctypes.c_void_p),
            ]

        bm = BITMAP()
        if not gdi32.GetObjectW(ii.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm)):
            return None

        w, h = bm.bmWidth, bm.bmHeight
        if w <= 0 or h <= 0:
            return None

        # Рисуем иконку на чёрном фоне
        hdc = user32.GetDC(0)
        memdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        old = gdi32.SelectObject(memdc, bmp)

        brush = gdi32.CreateSolidBrush(0x000000)
        rect = wintypes.RECT(0, 0, w, h)
        user32.FillRect(memdc, ctypes.byref(rect), brush)

        # DI_NORMAL = 0x0003
        user32.DrawIconEx(memdc, 0, 0, hicon, w, h, 0, None, 0x0003)

        # ВАЖНО: отцепить bmp от DC до GetDIBits, иначе rows=0
        gdi32.SelectObject(memdc, old)

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bi.biWidth = w
        bi.biHeight = -h
        bi.biPlanes = 1
        bi.biBitCount = 32
        bi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        rows = gdi32.GetDIBits(memdc, bmp, 0, h, buf, ctypes.byref(bi), 0)

        # cleanup
        gdi32.DeleteObject(bmp)
        gdi32.DeleteObject(brush)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(0, hdc)
        gdi32.DeleteObject(ii.hbmColor)
        gdi32.DeleteObject(ii.hbmMask)
        user32.DestroyIcon(hicon)

        if rows == 0:
            return None

        img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1)
        img = img.resize((size, size), Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    except Exception:
        if hicon:
            try:
                user32.DestroyIcon(hicon)
            except Exception:
                pass
        return None