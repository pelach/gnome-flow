from datetime import datetime
from pathlib import Path
from gi.repository import Gio, GLib

MODE = "action"
CATEGORY = "display"
TYPE = "take_screenshot"
LABEL = "Take Screenshot"
DESCRIPTION = "Capture a full-screen or active window screenshot."

SCHEMA = [
    {
        "key": "target",
        "type": "choice",
        "title": "Capture Mode",
        "options": [
            ("screen", "Entire Screen"),
            ("window", "Active Window"),
        ],
        "default": "screen",
    },
    {
        "key": "include_cursor",
        "type": "bool",
        "title": "Include Mouse Pointer",
        "default": False,
    },
    {
        "key": "flash",
        "type": "bool",
        "title": "Screen Flash Effect",
        "default": True,
    },
]


def format_subtitle(params: dict) -> str:
    mode = "Active window" if params.get("target") == "window" else "Full screen"
    return f"Screenshot ({mode})"


def run(params: dict, context: str = "") -> bool:
    target = params.get("target", "screen")
    cursor = bool(params.get("include_cursor", False))
    flash = bool(params.get("flash", True))

    pic_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or str(Path.home() / "Pictures")
    out_dir = Path(pic_dir) / "Screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = str(out_dir / f"Screenshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png")

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    if target == "window":
        bus.call_sync(
            "org.gnome.Shell.Screenshot",
            "/org/gnome/Shell/Screenshot",
            "org.gnome.Shell.Screenshot",
            "ScreenshotWindow",
            GLib.Variant("(bbbs)", (True, cursor, flash, filename)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    else:
        bus.call_sync(
            "org.gnome.Shell.Screenshot",
            "/org/gnome/Shell/Screenshot",
            "org.gnome.Shell.Screenshot",
            "Screenshot",
            GLib.Variant("(bbs)", (cursor, flash, filename)),
            None,
            Gio.DBusCallFlags.NONE,
            -1,
            None,
        )
    return True