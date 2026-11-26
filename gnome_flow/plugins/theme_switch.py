from gi.repository import Gio

MODE = "action"
CATEGORY = "system"
TYPE = "set_color_scheme"
LABEL = "Set Desktop Theme"
DESCRIPTION = "Switch GNOME between Light Mode, Dark Mode, or toggle the current theme."

SCHEMA = [
    {
        "key": "scheme",
        "type": "choice",
        "title": "Appearance Mode",
        "options": [
            ("toggle", "Toggle Light / Dark"),
            ("prefer-dark", "Dark Mode"),
            ("default", "Light Mode"),
        ],
        "default": "toggle",
    }
]


def format_subtitle(params: dict) -> str:
    labels = {
        "toggle": "Toggle Light / Dark",
        "prefer-dark": "Dark Mode",
        "default": "Light Mode",
    }
    return labels.get(params.get("scheme", "toggle"), "Toggle")


def run(params: dict, context: str = "") -> bool:
    settings = Gio.Settings.new("org.gnome.desktop.interface")
    target = params.get("scheme", "toggle")
    if target == "toggle":
        current = settings.get_string("color-scheme")
        target = "default" if current == "prefer-dark" else "prefer-dark"
    settings.set_string("color-scheme", target)
    Gio.Settings.sync()
    return True