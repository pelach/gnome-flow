from gi.repository import Gio

MODE = "action"
CATEGORY = "system"
TYPE = "set_dnd"
LABEL = "Do Not Disturb (DND)"
DESCRIPTION = "Enable, disable, or toggle GNOME notification banners."

SCHEMA = [
    {
        "key": "state",
        "type": "choice",
        "title": "DND State",
        "options": [
            ("toggle", "Toggle Do Not Disturb"),
            ("on", "Turn On (Hide Banners)"),
            ("off", "Turn Off (Show Banners)"),
        ],
        "default": "toggle",
    }
]


def format_subtitle(params: dict) -> str:
    labels = {
        "toggle": "Toggle DND",
        "on": "Turn On DND",
        "off": "Turn Off DND",
    }
    return labels.get(params.get("state", "toggle"), "Toggle DND")


def run(params: dict, context: str = "") -> bool:
    settings = Gio.Settings.new("org.gnome.desktop.notifications")
    state = params.get("state", "toggle")
    # show-banners = False jelenti a DND bekapcsolt állapotát
    if state == "toggle":
        current_banners = settings.get_boolean("show-banners")
        settings.set_boolean("show-banners", not current_banners)
    else:
        settings.set_boolean("show-banners", state == "off")
    Gio.Settings.sync()
    return True