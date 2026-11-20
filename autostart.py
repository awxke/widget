import os
import sys
from pathlib import Path

BAT_NAME = "widget_autostart.bat"


def startup_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def bat_path() -> Path:
    return startup_dir() / BAT_NAME


def is_autostart_enabled() -> bool:
    return bat_path().exists()


def enable_autostart():
    """Создаёт .bat в Startup, запускающий pythonw main.py."""
    main_py = Path(__file__).parent / "main.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    content = (
        "@echo off\r\n"
        f'cd /d "{main_py.parent}"\r\n'
        f'start "" "{pythonw}" "{main_py}"\r\n'
    )
    startup_dir().mkdir(parents=True, exist_ok=True)
    with open(bat_path(), "w", encoding="utf-8", newline="") as f:
        f.write(content)


def disable_autostart():
    p = bat_path()
    if p.exists():
        p.unlink()


def toggle_autostart() -> bool:
    if is_autostart_enabled():
        disable_autostart()
        return False
    enable_autostart()
    return True