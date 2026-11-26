import re
from gi.repository import Gio

MODE = "trigger"
CATEGORY = "clipboard"
CATEGORY_TITLE = "Clipboard"
CATEGORY_ICON = "edit-paste-symbolic"
TYPE = "clipboard_changed"
LABEL = "Clipboard Text Copied"
DESCRIPTION = "Triggers immediately when text is copied to clipboard. Passes text as {context}."

SCHEMA = [
    {
        "key": "regex",
        "type": "str",
        "title": "Optional Regex Filter (leave empty for any text)",
        "default": "",
    }
]


def format_subtitle(params: dict) -> str:
    rx = params.get("regex", "").strip()
    return f"Matches: {rx}" if rx else "Any copied text"


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    pattern_str = trigger.params.get("regex", "").strip()
    compiled = re.compile(pattern_str) if pattern_str else None

    def on_clipboard_signal(_conn, _sender, _path, _iface, _signal, params, _data):
        (text,) = params.unpack()
        if not text:
            return
        if compiled and not compiled.search(text):
            return
        fire_callback(context=text)

    sub_id = bus.signal_subscribe(
        None,
        "org.gnome.Flow.ShellBridge",
        "ClipboardChanged",
        "/org/gnome/Flow/ShellBridge",
        None,
        Gio.DBusSignalFlags.NONE,
        on_clipboard_signal,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch