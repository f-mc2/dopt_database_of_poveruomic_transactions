import json
from pathlib import Path
from typing import Any, Dict


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def save_state(path: Path, state: Dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
