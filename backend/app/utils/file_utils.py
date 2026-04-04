from datetime import datetime
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
