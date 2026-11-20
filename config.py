import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_CONFIG = {
    "games": [],
    "sites": [],
    "weather": {"lat": 47.2357, "lon": 39.7015, "city": "Ростов-на-Дону"},
    "events": {},
}


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k in ("games", "sites", "weather", "events"):
            cfg.setdefault(k, DEFAULT_CONFIG[k])
        return cfg
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)