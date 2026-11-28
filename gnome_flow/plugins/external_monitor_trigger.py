from gi.repository import Gio

MODE = "trigger"
CATEGORY = "display"
CATEGORY_TITLE = "Display"
CATEGORY_ICON = "preferences-desktop-display-symbolic"
TYPE = "external_monitor_changed"
LABEL = "External Monitor"
DESCRIPTION = "Triggers when an external display is connected or disconnected."

SCHEMA = [
    {
        "key": "event",
        "type": "choice",
        "title": "Trigger When External Monitor Is",
        "options": [
            ("connected", "Connected"),
            ("disconnected", "Disconnected"),
            ("any", "Connected or Disconnected"),
        ],
        "default": "connected",
    },
    {
        "key": "filter",
        "type": "entry",
        "title": "Monitor Name / Connector Filter (optional)",
        "default": "",
    },
]


def format_subtitle(params: dict) -> str:
    labels = {
        "connected": "External monitor connected",
        "disconnected": "External monitor disconnected",
        "any": "External monitor changed",
    }
    base = labels.get(params.get("event", "connected"), "External monitor changed")
    flt = (params.get("filter") or "").strip()
    return f"{base} ({flt})" if flt else base


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    wanted = trigger.params.get("event", "connected")
    name_filter = (trigger.params.get("filter") or "").strip().lower()

    state = {"prev_names": None}

    def _matches_filter(names: list[str]) -> bool:
        if not name_filter:
            return True
        return any(name_filter in n.lower() for n in names)

    def on_signal(_conn, _sender, _path, _iface, _signal, params):
        _total, _ext_count, ext_names = params.unpack()
        ext_list = list(ext_names)

        prev = state["prev_names"]
        state["prev_names"] = ext_list

        # Első eseménynél ha nincs előzmény, darabszám alapján döntünk
        if prev is None:
            added = ext_list
            removed = []
        else:
            prev_set = set(prev)
            curr_set = set(ext_list)
            added = [n for n in ext_list if n not in prev_set]
            removed = [n for n in prev if n not in curr_set]

        if wanted in ("connected", "any") and added and _matches_filter(added):
            fire_callback(context=", ".join(added))
        elif wanted in ("disconnected", "any") and removed and _matches_filter(removed):
            fire_callback(context=", ".join(removed))

    sub_id = bus.signal_subscribe(
        None,
        "org.gnome.Flow.ShellBridge",
        "MonitorsChanged",
        "/org/gnome/Flow/ShellBridge",
        None,
        Gio.DBusSignalFlags.NONE,
        on_signal,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch