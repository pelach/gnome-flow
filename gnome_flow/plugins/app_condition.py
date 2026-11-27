MODE = "condition"
CATEGORY = "app"
TYPE = "app_running"
LABEL = "App is Running"
    
SCHEMA = [
    {"key": "process", "type": "app_picker", "title": "Process Name (e.g. code, chrome)", "default": ""}
]

def format_subtitle(params: dict) -> str:
    return params.get("process", "").strip() or "(unset)"