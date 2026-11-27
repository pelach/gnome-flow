from gi.repository import Gio

MODE = "trigger"
CATEGORY = "app"
CATEGORY_TITLE = "Applications"
CATEGORY_ICON = "application-x-executable-symbolic"
TYPE = "window_focused"
LABEL = "Window Focused"
DESCRIPTION = "Triggers when a specific application window gains focus. Passes 'wm_class: title' as {context}."

SCHEMA = [
    {
        "key": "app_filter",
        "type": "app_picker",
        "title": "Window Class or Title Filter (e.g. code, mixxx, chrome)",
        "default": "",
    },
]


def format_subtitle(params: dict) -> str:
    flt = params.get("app_filter", "").strip()
    return f"Focus: {flt}" if flt else "Any window focused"


def start_watch(trigger, fire_callback):
    flt = trigger.params.get("app_filter", "").strip().lower()
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    last_key = ""

    def on_focus(_conn, _sender, _path, _iface, _signal, params, _data):
        nonlocal last_key
        wm_class, title = params.unpack()
        combined = f"{wm_class} {title}".lower()
        if flt and flt not in combined:
            last_key = ""
            return
        cur_key = f"{wm_class}:{title}"
        if cur_key != last_key:
            last_key = cur_key
            fire_callback(context=f"{wm_class}: {title}".strip(": "))

    sub_id = bus.signal_subscribe(
        None,
        "org.gnome.Flow.ShellBridge",
        "FocusChanged",
        "/org/gnome/Flow/ShellBridge",
        None,
        Gio.DBusSignalFlags.NONE,
        on_focus,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch