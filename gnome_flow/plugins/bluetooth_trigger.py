from gi.repository import Gio

MODE = "trigger"
CATEGORY = "network"
TYPE = "bluetooth_event"
LABEL = "Bluetooth Device"
DESCRIPTION = "Triggers when a Bluetooth device connects or disconnects. Passes device name/MAC as {context}."

SCHEMA = [
    {
        "key": "event",
        "type": "choice",
        "title": "Bluetooth Event",
        "options": [
            ("connected", "Device Connected"),
            ("disconnected", "Device Disconnected"),
        ],
        "default": "connected",
    },
    {
        "key": "filter",
        "type": "str",
        "title": "Device Name or MAC Filter (optional)",
        "default": "",
    },
]


def format_subtitle(params: dict) -> str:
    ev = params.get("event", "connected")
    flt = params.get("filter", "").strip()
    target = f"'{flt}'" if flt else "any device"
    return f"Bluetooth {ev}: {target}"


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    event = trigger.params.get("event", "connected")
    dev_filter = trigger.params.get("filter", "").strip().lower()

    def _get_device_label(obj_path: str) -> tuple[str, str]:
        try:
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                obj_path,
                "org.bluez.Device1",
                None,
            )
            alias = proxy.get_cached_property("Alias")
            addr = proxy.get_cached_property("Address")
            name = alias.unpack() if alias else ""
            mac = addr.unpack() if addr else ""
            return name, mac
        except Exception:
            return "", ""

    def on_bluez_props(_conn, _sender, obj_path, _iface, _signal, params, _data):
        iface_name, changed, _invalidated = params.unpack()
        if iface_name != "org.bluez.Device1" or "Connected" not in changed:
            return

        is_connected = bool(changed["Connected"])
        if (event == "connected" and not is_connected) or (event == "disconnected" and is_connected):
            return

        name, mac = _get_device_label(obj_path)
        haystack = f"{name} {mac} {obj_path}".lower()
        if dev_filter and dev_filter not in haystack:
            return

        fire_callback(context=name or mac or obj_path)

    sub_id = bus.signal_subscribe(
        "org.bluez",
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        None,
        None,
        Gio.DBusSignalFlags.NONE,
        on_bluez_props,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch