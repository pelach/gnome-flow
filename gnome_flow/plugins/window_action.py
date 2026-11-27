from gi.repository import Gio, GLib

MODE = "action"
CATEGORY = "display"
CATEGORY_TITLE = "Display"
CATEGORY_ICON = "preferences-desktop-display-symbolic"
TYPE = "window_layout"
LABEL = "Window Layout & Focus"
DESCRIPTION = "Tile, maximize, focus, or move windows via GNOME Flow Shell Bridge."

SCHEMA = [
    {
        "key": "app_filter",
        "type": "entry",
        "title": "App / Window Filter (empty = active window, e.g. code, chrome)",
        "default": "",
    },
    {
        "key": "layout",
        "type": "choice",
        "title": "Window Action / Position",
        "options": [
            ("left", "Left Half (50%)"),
            ("right", "Right Half (50%)"),
            ("top", "Top Half"),
            ("bottom", "Bottom Half"),
            ("top-left", "Top-Left Quarter"),
            ("top-right", "Top-Right Quarter"),
            ("bottom-left", "Bottom-Left Quarter"),
            ("bottom-right", "Bottom-Right Quarter"),
            ("center", "Centered (70% × 80%)"),
            ("maximize", "Maximize"),
            ("unmaximize", "Unmaximize / Restore"),
            ("focus", "Bring to Front / Focus"),
            ("ws-next", "Move to Next Workspace"),
            ("ws-prev", "Move to Previous Workspace"),
            ("minimize", "Minimize"),
            ("close", "Close Window"),
        ],
        "default": "left",
    },
]

_LAYOUT_LABELS = {
    "left": "Left Half",
    "right": "Right Half",
    "top": "Top Half",
    "bottom": "Bottom Half",
    "top-left": "Top-Left Quarter",
    "top-right": "Top-Right Quarter",
    "bottom-left": "Bottom-Left Quarter",
    "bottom-right": "Bottom-Right Quarter",
    "center": "Centered",
    "maximize": "Maximize",
    "unmaximize": "Unmaximize",
    "focus": "Focus",
    "ws-next": "Next Workspace",
    "ws-prev": "Previous Workspace",
    "minimize": "Minimize",
    "close": "Close",
}


def format_subtitle(params: dict) -> str:
    flt = params.get("app_filter", "").strip()
    target = f"'{flt}'" if flt else "Active window"
    layout = params.get("layout", "left")
    return f"{target} → {_LAYOUT_LABELS.get(layout, layout)}"


def run(params: dict, context: str = "") -> bool:
    app_filter = params.get("app_filter", "").strip()
    layout = params.get("layout", "left")

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        res = bus.call_sync(
            "org.gnome.Shell",
            "/org/gnome/Flow/ShellBridge",
            "org.gnome.Flow.ShellBridge",
            "ManageWindow",
            GLib.Variant("(ss)", (app_filter, layout)),
            GLib.VariantType("(b)"),
            Gio.DBusCallFlags.NONE,
            2000,
            None,
        )
        ok = bool(res.unpack()[0])
        if not ok:
            print(f"[GNOME Flow] Window '{app_filter or 'active'}' not found for '{layout}'.")
        return ok
    except Exception as e:
        print(f"[GNOME Flow] Window Layout D-Bus error: {e}")
        return False