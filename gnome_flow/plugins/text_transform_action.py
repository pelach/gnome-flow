import os
import re
from pathlib import Path

MODE = "action"
CATEGORY = "text"
CATEGORY_TITLE = "Text & Data"
CATEGORY_ICON = "insert-text-symbolic"
TYPE = "text_transform"
LABEL = "Text & Data Transform"
DESCRIPTION = "Set, extract (Regex), replace, split, format, or save {context} text for the next step."

SCHEMA = [
    {
        "key": "operation",
        "type": "choice",
        "title": "Operation",
        "options": [
            ("set", "Set Text / Template"),
            ("regex", "Extract Match (Regex)"),
            ("replace", "Find & Replace"),
            ("split_pick", "Split Text & Pick Nth Item"),
            ("trim", "Trim Whitespace"),
            ("upper", "Convert to UPPERCASE"),
            ("lower", "Convert to lowercase"),
            ("save_file", "Save {context} to File"),
        ],
        "default": "regex",
    },
    {
        "key": "arg1",
        "type": "entry",
        "title": "Text / Pattern / Separator / File Path",
        "default": "",
    },
    {
        "key": "arg2",
        "type": "entry",
        "title": "Replacement Text or Item Index (0 = first, -1 = last)",
        "default": "",
    },
]

_OP_NAMES = {
    "set": "Set Text",
    "regex": "Regex Extract",
    "replace": "Replace",
    "split_pick": "Split & Pick",
    "trim": "Trim",
    "upper": "Uppercase",
    "lower": "Lowercase",
    "save_file": "Save to File",
}


def format_subtitle(params: dict) -> str:
    op = params.get("operation", "regex")
    a1 = params.get("arg1", "").strip()
    a2 = params.get("arg2", "").strip()
    name = _OP_NAMES.get(op, op)

    if op in ("trim", "upper", "lower"):
        return name
    if op == "replace":
        return f"{name}: '{a1}' → '{a2}'"
    if op == "split_pick":
        return f"{name} by '{a1}' [#{a2 or '0'}]"
    return f"{name}: {a1}" if a1 else name


def run(params: dict, context: str = "") -> dict | bool:
    op = params.get("operation", "regex")
    a1 = params.get("arg1", "")
    a2 = params.get("arg2", "")

    try:
        if op == "set":
            return {"context": a1}

        if op == "trim":
            return {"context": context.strip()}

        if op == "upper":
            return {"context": context.upper()}

        if op == "lower":
            return {"context": context.lower()}

        if op == "replace":
            return {"context": context.replace(a1, a2)}

        if op == "regex":
            if not a1:
                return False
            m = re.search(a1, context, flags=re.DOTALL)
            if not m:
                print(f"[GNOME Flow] Regex '{a1}' did not match.")
                return {"abort": True}
            # Ha van zárójelezett csoport (pl. <title>(.*?)</title>), a belső értéket adja vissza
            extracted = m.group(1) if m.lastindex else m.group(0)
            return {"context": extracted.strip()}

        if op == "split_pick":
            sep = a1.replace("\\n", "\n").replace("\\t", "\t") or "\n"
            parts = [p for p in context.split(sep) if p.strip()]
            if not parts:
                return {"abort": True}
            try:
                idx = int(a2.strip()) if a2.strip() else 0
            except ValueError:
                idx = 0
            if idx < -len(parts) or idx >= len(parts):
                return {"abort": True}
            return {"context": parts[idx].strip()}

        if op == "save_file":
            if not a1.strip():
                return False
            target = Path(os.path.expanduser(a1.strip()))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(context, encoding="utf-8")
            return True

    except Exception as e:
        print(f"[GNOME Flow] Text transform '{op}' error: {e}")
        return {"abort": True}

    return False