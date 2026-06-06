"""
utils/file_storage.py
---------------------
The ONLY place in the application that calls open().
All other modules use these helpers.

Writes are atomic: data goes to .tmp first, then os.replace()
so a crash never leaves a corrupt JSON file on disk.
"""

import json, os


def read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: dict) -> None:
    """Atomic write — .tmp then rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    os.replace(tmp, path)


def delete_file(path: str) -> None:
    os.remove(path)


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def list_json_files(directory: str) -> list[str]:
    if not os.path.isdir(directory):
        return []
    return [os.path.join(directory, f)
            for f in os.listdir(directory) if f.endswith(".json")]


def build_path(*parts: str) -> str:
    return os.path.normpath(os.path.join(*parts))