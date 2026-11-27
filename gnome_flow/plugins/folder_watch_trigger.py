MODE = "trigger"
CATEGORY = "file"
TYPE = "dir_changed"
LABEL = "Folder Watcher"
DESCRIPTION = "Watches a directory for specific file events. Passes the affected path as {context}."

SCHEMA = [
    {"key": "watch", "type": "folder_watch", "title": "Watch Settings"},
]

def format_subtitle(params: dict) -> str:
    evs = ", ".join(e.capitalize() for e in params.get("events", ["added"]))
    return f"[{evs}] {params.get('path', '~')}"