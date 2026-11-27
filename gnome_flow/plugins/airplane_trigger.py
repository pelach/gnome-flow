from gi.repository import Gio

MODE = "trigger"
CATEGORY = "network"
TYPE = "airplane_mode"
LABEL = "Airplane Mode"
DESCRIPTION = "Triggers when Airplane Mode (wireless kill-switch) turns on or off."

SCHEMA = [
    {
        "key": "state",
        "type": "choice",
        "title": "Trigger When Airplane Mode Turns",
        "options": [
            ("on", "Turned On"),
            ("off", "Turned Off"),
            ("any", "Any Change"),
        ],
        "default": "on",
    },
]


def format_subtitle(params: dict) -> str:
    state = params.get("state", "on")
    labels = {"on": "Turned On", "off": "Turned Off", "any": "Any Change"}
    return f"Airplane Mode: {labels.get(state, state)}"


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    wanted = trigger.params.get("state", "on")

    def on_nm_props(_conn, _sender, _path, _iface, _signal, params, _data):
        iface_name, changed, _invalidated = params.unpack()
        if iface_name == "org.freedesktop.NetworkManager" and "WirelessEnabled" in changed:
            airplane_on = not bool(changed["WirelessEnabled"])
            if wanted == "any" or (wanted == "on" and airplane_on) or (wanted == "off" and not airplane_on):
                fire_callback(context="airplane-on" if airplane_on else "airplane-off")

    sub_id = bus.signal_subscribe(
        "org.freedesktop.NetworkManager",
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        "/org/freedesktop/NetworkManager",
        None,
        Gio.DBusSignalFlags.NONE,
        on_nm_props,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch