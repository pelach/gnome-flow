MODE = "trigger"
CATEGORY = "dbus"
TYPE = "drive_mounted"
LABEL = "Drive Mounted"
DESCRIPTION = "Fires when a USB drive, SD card, or external disk is mounted. Passes mount path as {context}."

SCHEMA = [
    {"key": "filter", "type": "entry", "title": "Optional Path / Label Filter (empty = any)", "default": ""},
]

def format_subtitle(params: dict) -> str:
    return params.get("filter", "").strip() or "Any removable drive"