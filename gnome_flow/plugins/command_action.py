MODE = "action"
CATEGORY = "system"
TYPE = "command"
LABEL = "Run Command"

SCHEMA = [
    {"key": "command", "type": "entry", "title": "Shell Command (supports {context})", "default": ""}
]

def format_subtitle(params: dict) -> str:
    return params.get("command", "").strip() or "(empty command)"