from gi.repository import Gio

MODE = "trigger"
CATEGORY = "display"
CATEGORY_TITLE = "Display & Appearance"
CATEGORY_ICON = "preferences-desktop-wallpaper-symbolic"
TYPE = "wallpaper_changed"
LABEL = "Wallpaper Changed"
DESCRIPTION = "Triggers when the desktop background changes. Passes the new wallpaper URI/path as {context}."

SCHEMA = [
    {
        "key": "scheme",
        "type": "choice",
        "title": "Watch Wallpaper For",
        "options": [
            ("any", "Light or Dark Wallpaper"),
            ("light", "Default / Light Wallpaper"),
            ("dark", "Dark Mode Wallpaper"),
        ],
        "default": "any",
    },
]


def format_subtitle(params: dict) -> str:
    sc = params.get("scheme", "any")
    labels = {"any": "Any theme", "light": "Light theme", "dark": "Dark theme"}
    return f"Wallpaper changed ({labels.get(sc, sc)})"


def start_watch(trigger, fire_callback):
    settings = Gio.Settings.new("org.gnome.desktop.background")
    scheme = trigger.params.get("scheme", "any")
    sig_ids = []

    def _emit(uri: str):
        path = uri.removeprefix("file://")
        fire_callback(context=path)

    if scheme in ("any", "light"):
        sig_ids.append(
            settings.connect("changed::picture-uri", lambda s, _k: _emit(s.get_string("picture-uri")))
        )
    if scheme in ("any", "dark"):
        sig_ids.append(
            settings.connect("changed::picture-uri-dark", lambda s, _k: _emit(s.get_string("picture-uri-dark")))
        )

    def stop_watch():
        for sid in sig_ids:
            try:
                settings.disconnect(sid)
            except Exception:
                pass

    return stop_watch