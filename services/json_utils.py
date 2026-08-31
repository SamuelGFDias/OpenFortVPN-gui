import json
import os
from typing import Any


def load_json(path: str, default: Any) -> Any:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
