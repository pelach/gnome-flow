MODE = "condition"
CATEGORY = "system"
TYPE = "dark_mode"
LABEL = "Desktop Theme"

SCHEMA = [
    {"key": "dark", "type": "bool", "title": "Require Dark Mode Active", "default": True}
]

def format_subtitle(params: dict) -> str:
    return "Dark Mode" if params.get("dark", True) else "Light Mode"
