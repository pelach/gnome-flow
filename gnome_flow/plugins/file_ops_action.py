import fnmatch
import os
import shutil
from pathlib import Path
from gi.repository import Gio

MODE = "action"
CATEGORY = "file"
CATEGORY_TITLE = "Files & Folders"
CATEGORY_ICON = "folder-open-symbolic"
TYPE = "file_ops"
LABEL = "File & Folder Operations"
DESCRIPTION = "Move, copy, rename, trash, or delete files/folders. Supports {context} and wildcard filters."

SCHEMA = [
    {
        "key": "operation",
        "type": "choice",
        "title": "Operation",
        "options": [
            ("move", "Move to Destination Folder"),
            ("copy", "Copy to Destination Folder"),
            ("rename", "Rename (in same folder)"),
            ("trash", "Move to Trash"),
            ("delete", "Delete Permanently"),
        ],
        "default": "move",
    },
    {
        "key": "source",
        "type": "entry",
        "title": "Source File or Folder Path (default: {context})",
        "default": "{context}",
    },
    {
        "key": "destination",
        "type": "entry",
        "title": "Destination Folder (or New Name for Rename)",
        "default": "",
    },
    {
        "key": "pattern",
        "type": "entry",
        "title": "Optional Filename Filter (e.g. *.pdf;*.deb, empty = all)",
        "default": "",
    },
    {
        "key": "collision",
        "type": "choice",
        "title": "If Target Already Exists",
        "options": [
            ("rename", "Keep Both (append _1, _2...)"),
            ("overwrite", "Overwrite Existing"),
            ("skip", "Skip Operation"),
        ],
        "default": "rename",
    },
]

_OP_LABELS = {
    "move": "Move",
    "copy": "Copy",
    "rename": "Rename",
    "trash": "Trash",
    "delete": "Delete",
}


def format_subtitle(params: dict) -> str:
    op = params.get("operation", "move")
    src = params.get("source", "{context}").strip() or "{context}"
    dst = params.get("destination", "").strip()
    flt = params.get("pattern", "").strip()
    suffix = f" [{flt}]" if flt else ""

    if op in ("trash", "delete"):
        return f"{_OP_LABELS.get(op, op)}: {src}{suffix}"
    return f"{_OP_LABELS.get(op, op)}: {src} → {dst or '(unset)'}{suffix}"


def _matches_pattern(name: str, pattern_str: str) -> bool:
    if not pattern_str:
        return True
    patterns = [p.strip() for p in pattern_str.replace(",", ";").split(";") if p.strip()]
    return any(fnmatch.fnmatch(name.lower(), pat.lower()) for pat in patterns)


def _resolve_collision(target: Path, policy: str) -> Path | None:
    if not target.exists():
        return target
    if policy == "skip":
        return None
    if policy == "overwrite":
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
        return target

    # policy == "rename": fájlnév_1.kiterjesztés
    stem = target.stem
    suffix = target.suffix
    parent = target.parent
    counter = 1
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def run(params: dict, context: str = "") -> dict | bool:
    op = params.get("operation", "move")
    raw_src = (params.get("source", "{context}").strip() or context).strip()
    raw_dst = params.get("destination", "").strip()
    pattern = params.get("pattern", "").strip()
    collision = params.get("collision", "rename")

    if not raw_src:
        print("[GNOME Flow] File operation skipped: empty source path.")
        return False

    src = Path(os.path.expanduser(raw_src))
    if not src.exists():
        print(f"[GNOME Flow] File operation skipped: source not found ({src}).")
        return False

    if not _matches_pattern(src.name, pattern):
        return False

    try:
        if op == "trash":
            gfile = Gio.File.new_for_path(str(src))
            return gfile.trash(None)

        if op == "delete":
            if src.is_dir() and not src.is_symlink():
                shutil.rmtree(src)
            else:
                src.unlink()
            return True

        if not raw_dst:
            print(f"[GNOME Flow] File operation '{op}' requires a destination.")
            return False

        dst_expanded = Path(os.path.expanduser(raw_dst))

        if op == "rename":
            # Ha csak új nevet adtak meg útvonal nélkül, a forrás mappáján belül nevezi át
            target = dst_expanded if dst_expanded.is_absolute() else (src.parent / raw_dst)
            target.parent.mkdir(parents=True, exist_ok=True)
            final_target = _resolve_collision(target, collision)
            if not final_target:
                return False
            src.rename(final_target)
            return {"context": str(final_target)}

        # 'move' vagy 'copy' célmappába
        dst_expanded.mkdir(parents=True, exist_ok=True)
        target = dst_expanded / src.name
        final_target = _resolve_collision(target, collision)
        if not final_target:
            return False

        if op == "move":
            shutil.move(str(src), str(final_target))
        elif op == "copy":
            if src.is_dir() and not src.is_symlink():
                shutil.copytree(src, final_target)
            else:
                shutil.copy2(src, final_target)

        return {"context": str(final_target)}

    except Exception as e:
        print(f"[GNOME Flow] File operation '{op}' error: {e}")
        return False