from pathlib import Path
from gi.repository import Gio

MODE = "action"
CATEGORY = "display"
CATEGORY_TITLE = "Display"
CATEGORY_ICON = "preferences-desktop-display-symbolic"
TYPE = "set_wallpaper"
LABEL = "Set Wallpaper"
DESCRIPTION = "Change the desktop background image (applies to both light and dark themes)."

SCHEMA = [
    {
        "key": "path",
        "type": "str",
        "title": "Image File Path (e.g. /home/pch/Pictures/wall.jpg)",
        "default": "",
    }
]


def format_subtitle(params: dict) -> str:
    p = params.get("path", "").strip()
    return Path(p).name if p else "No image selected"


def run(params: dict, context: str = "") -> bool:
    raw_path = params.get("path", "").strip()
    if not raw_path:
        return False

    path = Path(raw_path).expanduser().resolve()
    if not path.is_file():
        return False

    uri = path.as_uri()
    settings = Gio.Settings.new("org.gnome.desktop.background")
    settings.set_string("picture-uri", uri)
    settings.set_string("picture-uri-dark", uri)
    Gio.Settings.sync()
    return True