import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(path):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class BotConfig:
    token: str
    backend_api_url: str
    mini_app_url: str
    proxy_url: str | None


def get_config():
    project_root = Path(__file__).resolve().parent.parent
    load_env_file(project_root / ".env")

    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set.")

    return BotConfig(
        token=token,
        backend_api_url=os.getenv("BACKEND_API_URL", "http://127.0.0.1:8000").rstrip("/"),
        mini_app_url=os.getenv("MINI_APP_URL", ""),
        proxy_url=os.getenv("PROXY_URL"),
    )
