import os
import configparser
from pathlib import Path


APP_NAME = "jetdreamterminal"

def _xdg(data_home: str, config_home: str) -> tuple[Path, Path]:
    base_data = Path(data_home) / APP_NAME
    base_config = Path(config_home) / APP_NAME
    base_data.mkdir(parents=True, exist_ok=True)
    base_config.mkdir(parents=True, exist_ok=True)
    return base_data, base_config

DATA_DIR, CONFIG_DIR = _xdg(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
)

DB_PATH = DATA_DIR / "sessions.db"
LOG_PATH = DATA_DIR / "app.log"
KEY_PATH = CONFIG_DIR / "key.bin"
CONFIG_PATH = CONFIG_DIR / "config.ini"
KNOWN_HOSTS = Path.home() / ".ssh" / "known_hosts"


def load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if CONFIG_PATH.exists():
        cfg.read(str(CONFIG_PATH))
    return cfg


def save_config(cfg: configparser.ConfigParser):
    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)
