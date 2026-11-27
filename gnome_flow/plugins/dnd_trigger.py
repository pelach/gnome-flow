from gi.repository import Gio

MODE = "trigger"
CATEGORY = "system"
CATEGORY_TITLE = "System State"
CATEGORY_ICON = "preferences-system-symbolic"
TYPE = "dnd_changed"
LABEL = "Do Not Disturb"
DESCRIPTION = "Triggers when GNOME Do Not Disturb mode turns on or off."

SCHEMA = [
    {
        "key": "state",
        "type": "choice",
        "title": "Trigger When DND Turns",
        "options": [
            ("on", "Turned On (Silent)"),
            ("off", "Turned Off (Banners Shown)"),
            ("any", "Any Change"),
        ],
        "default": "on",
    },
]


def format_subtitle(params: dict) -> str:
    state = params.get("state", "on")
    labels = {"on": "Turned On", "off": "Turned Off", "any": "Any Change"}
    return f"Do Not Disturb: {labels.get(state, state)}"


def start_watch(trigger, fire_callback):
    settings = Gio.Settings.new("org.gnome.desktop.notifications")
    wanted = trigger.params.get("state", "on")

    def on_changed(_settings, _key):
        show_banners = settings.get_boolean("show-banners")
        is_dnd = not show_banners
        if wanted == "any" or (wanted == "on" and is_dnd) or (wanted == "off" and not is_dnd):
            fire_callback(context="dnd-on" if is_dnd else "dnd-off")

    sig_id = settings.connect("changed::show-banners", on_changed)

    def stop_watch():
        try:
            settings.disconnect(sig_id)
        except Exception:
            pass

    return stop_watch