MODE = "trigger"
CATEGORY = "keyboard"
TYPE = "shortcut"
LABEL = "Shortcut Pressed"
DESCRIPTION = "Select modifiers and press a key to trigger this flow anywhere on the desktop."

SCHEMA = [
    {"key": "accel", "type": "shortcut_capture", "title": "Shortcut", "default": "F1"},
]

def format_subtitle(params: dict) -> str:
    return params.get("accel", "F1").replace("<", "").replace(">", "+")