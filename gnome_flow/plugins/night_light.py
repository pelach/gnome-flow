from gi.repository import Gio

MODE = "action"
CATEGORY = "display"
CATEGORY_TITLE = "Display"
CATEGORY_ICON = "preferences-desktop-display-symbolic"
TYPE = "set_night_light"
LABEL = "Night Light"
DESCRIPTION = "Enable, disable, or toggle GNOME Night Light warm color temperature."

SCHEMA = [
    {
        "key": "state",
        "type": "choice",
        "title": "Night Light Mode",
        "options": [
            ("toggle", "Toggle Night Light"),
            ("on", "Turn On"),
            ("off", "Turn Off"),
        ],
        "default": "toggle",
    }
]


def format_subtitle(params: dict) -> str:
    labels = {
        "toggle": "Toggle Night Light",
        "on": "Turn On",
        "off": "Turn Off",
    }
    return labels.get(params.get("state", "toggle"), "Toggle")


def run(params: dict, context: str = "") -> bool:
    settings = Gio.Settings.new("org.gnome.settings-daemon.plugins.color")
    state = params.get("state", "toggle")
    if state == "toggle":
        current = settings.get_boolean("night-light-enabled")
        settings.set_boolean("night-light-enabled", not current)
    else:
        settings.set_boolean("night-light-enabled", state == "on")
    Gio.Settings.sync()
    return True