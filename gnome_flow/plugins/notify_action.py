MODE = "action"
CATEGORY = "system"
TYPE = "notify"
LABEL = "Send Notification"

SCHEMA = [
    {"key": "title", "type": "entry", "title": "Notification Title", "default": "GNOME Flow"}, 
    {"key": "body", "type": "entry", "title": "Notification Body", "default": "Triggered: {context}"}
]

def format_subtitle(params: dict) -> str:
    title = params.get("title", "GNOME Flow").strip()
    body = params.get("body", "").strip()
    return f"{title}: {body}" if body else title