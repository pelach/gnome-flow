MODE = "action"
CATEGORY = "file"
TYPE = "open_path"
LABEL = "Open Path / URL"
DESCRIPTION = "Open a file, folder, or URL (supports {context})."

SCHEMA = [
    {"key": "path", "type": "path_picker", "title": "Path or URL (or {context})", "default": "{context}"},
]

def format_subtitle(params: dict) -> str:
    return params.get("path", "{context}")