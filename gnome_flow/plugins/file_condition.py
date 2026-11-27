MODE = "condition"
CATEGORY = "file"
TYPE = "file_exists"
LABEL = "Path Exists"

SCHEMA = [
    {"key": "path", "type": "path_picker", "title": "File or Folder Path", "default": ""}
]

def format_subtitle(params: dict) -> str:
    return params.get("path", "").strip() or "(unset)"