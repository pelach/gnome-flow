import subprocess

MODE = "action"
CATEGORY = "system"
CATEGORY_TITLE = "System & Notify"
CATEGORY_ICON = "preferences-system-symbolic"
TYPE = "session_control"
LABEL = "Session & Power State"
DESCRIPTION = "Lock the screen, suspend the system, or log out of the current GNOME session."

SCHEMA = [
    {
        "key": "action",
        "type": "choice",
        "title": "Session Action",
        "options": [
            ("lock", "Lock Screen"),
            ("suspend", "Suspend (Sleep)"),
            ("logout", "Log Out (No Prompt)"),
        ],
        "default": "lock",
    },
]

_ACTION_LABELS = {
    "lock": "Lock Screen",
    "suspend": "Suspend System",
    "logout": "Log Out",
}


def format_subtitle(params: dict) -> str:
    act = params.get("action", "lock")
    return _ACTION_LABELS.get(act, act)


def run(params: dict, context: str = "") -> bool:
    act = params.get("action", "lock")
    try:
        if act == "lock":
            subprocess.run(["loginctl", "lock-session"], check=False)
            return True
        if act == "suspend":
            subprocess.run(["systemctl", "suspend"], check=False)
            return True
        if act == "logout":
            subprocess.run(["gnome-session-quit", "--logout", "--no-prompt"], check=False)
            return True
    except Exception as e:
        print(f"[GNOME Flow] Session action '{act}' error: {e}")
    return False