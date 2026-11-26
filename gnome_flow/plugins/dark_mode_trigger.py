from gi.repository import Gio

MODE = "trigger"
CATEGORY = "display"
CATEGORY_TITLE = "Display"
CATEGORY_ICON = "preferences-desktop-display-symbolic"
TYPE = "color_scheme_changed"
LABEL = "Color Scheme Changed"
DESCRIPTION = "Triggers when GNOME switches between Light and Dark mode."

SCHEMA = [
    {
        "key": "target",
        "type": "choice",
        "title": "Trigger When Switched To",
        "options": [
            ("any", "Any Change (Light or Dark)"),
            ("prefer-dark", "Dark Mode"),
            ("default", "Light Mode"),
        ],
        "default": "any",
    }
]


def format_subtitle(params: dict) -> str:
    labels = {
        "any": "Switched Light / Dark",
        "prefer-dark": "Switched to Dark Mode",
        "default": "Switched to Light Mode",
    }
    return labels.get(params.get("target", "any"), "Theme changed")


def start_watch(trigger, fire_callback):
    settings = Gio.Settings.new("org.gnome.desktop.interface")
    target = trigger.params.get("target", "any")
    state = {"last": settings.get_string("color-scheme")}

    def on_changed(s, key):
        current = s.get_string(key)
        if current == state["last"]:
            return
        state["last"] = current
        if target == "any" or current == target:
            fire_callback(context=current)

    handler_id = settings.connect("changed::color-scheme", on_changed)

    def stop_watch():
        try:
            settings.disconnect(handler_id)
        except Exception:
            pass

    return stop_watch