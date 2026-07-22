import json
from copy import deepcopy
from pathlib import Path


def read_json(path: str, default):
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        write_json(path, default)
        return deepcopy(default)
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        write_json(path, default)
        return deepcopy(default)


def write_json(path: str, data) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")