from gi.repository import Gio, GLib

MODE = "action"
CATEGORY = "display"
CATEGORY_TITLE = "Display"
CATEGORY_ICON = "preferences-desktop-display-symbolic"
TYPE = "display_control"
LABEL = "Display & Brightness"
DESCRIPTION = "Set screen brightness, keyboard backlight, or screen blank timeout."

SCHEMA = [
    {
        "key": "target",
        "type": "choice",
        "title": "Setting",
        "options": [
            ("screen_brightness", "Screen Brightness (%)"),
            ("kbd_brightness", "Keyboard Backlight (%)"),
            ("screen_timeout", "Screen Blank Timeout (seconds, 0 = Never)"),
        ],
        "default": "screen_brightness",
    },
    {
        "key": "value",
        "type": "int",
        "title": "Value (% or seconds)",
        "min": 0,
        "max": 3600,
        "step": 5,
        "default": 50,
    },
]


def format_subtitle(params: dict) -> str:
    target = params.get("target", "screen_brightness")
    val = int(params.get("value", 50))
    if target == "screen_brightness":
        return f"Screen brightness: {min(100, val)}%"
    if target == "kbd_brightness":
        return f"Keyboard backlight: {min(100, val)}%"
    return "Screen timeout: Never" if val == 0 else f"Screen timeout: {val}s"


def _set_gsd_brightness(iface: str, pct: int):
    pct = max(0, min(100, pct))
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    bus.call_sync(
        "org.gnome.SettingsDaemon.Power",
        "/org/gnome/SettingsDaemon/Power",
        "org.freedesktop.DBus.Properties",
        "Set",
        GLib.Variant("(ssv)", (iface, "Brightness", GLib.Variant("i", pct))),
        None,
        Gio.DBusCallFlags.NONE,
        -1,
        None,
    )


def run(params: dict, context: str = "") -> bool:
    target = params.get("target", "screen_brightness")
    val = int(params.get("value", 50))

    if target == "screen_brightness":
        _set_gsd_brightness("org.gnome.SettingsDaemon.Power.Screen", val)
    elif target == "kbd_brightness":
        _set_gsd_brightness("org.gnome.SettingsDaemon.Power.Keyboard", val)
    elif target == "screen_timeout":
        settings = Gio.Settings.new("org.gnome.desktop.session")
        settings.set_uint("idle-delay", max(0, val))
    return True