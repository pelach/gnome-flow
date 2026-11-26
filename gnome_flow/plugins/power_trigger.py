from gi.repository import Gio, GLib

MODE = "trigger"
CATEGORY = "power"
CATEGORY_TITLE = "Power"
CATEGORY_ICON = "battery-good-symbolic"
TYPE = "battery_event"
LABEL = "Battery & Power"
DESCRIPTION = "Triggers on charger plug/unplug or when battery drops below / rises above a percentage."

SCHEMA = [
    {
        "key": "event",
        "type": "choice",
        "title": "Power Event",
        "options": [
            ("below", "Battery Drops Below (%)"),
            ("above", "Battery Rises Above (%)"),
            ("charging", "Charger Connected (Charging)"),
            ("discharging", "Charger Disconnected (On Battery)"),
        ],
        "default": "below",
    },
    {
        "key": "threshold",
        "type": "int",
        "title": "Battery Percentage Threshold",
        "min": 5,
        "max": 100,
        "step": 5,
        "default": 20,
    },
]


def format_subtitle(params: dict) -> str:
    ev = params.get("event", "below")
    pct = int(params.get("threshold", 20))
    if ev == "below":
        return f"Battery below {pct}%"
    if ev == "above":
        return f"Battery above {pct}%"
    if ev == "charging":
        return "Charger connected"
    return "Switched to battery power"


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    dev_path = "/org/freedesktop/UPower/devices/DisplayDevice"

    event = trigger.params.get("event", "below")
    threshold = int(trigger.params.get("threshold", 20))

    # Állapotkövetés, hogy csak átlépéskor/változáskor süssön el, ne minden 1%-os lépésnél
    state_cache = {"triggered": False, "last_state": None}

    def on_props_changed(_conn, _sender, _path, _iface, _signal, params, _data):
        iface_name, changed, _invalidated = params.unpack()
        if iface_name != "org.freedesktop.UPower.Device":
            return

        if "State" in changed and event in ("charging", "discharging"):
            # UPower State: 1 = Charging, 2 = Discharging, 4 = Fully charged
            st = changed["State"]
            if st != state_cache["last_state"]:
                state_cache["last_state"] = st
                if event == "charging" and st == 1:
                    fire_callback(context="charging")
                elif event == "discharging" and st == 2:
                    fire_callback(context="discharging")

        if "Percentage" in changed and event in ("below", "above"):
            pct = float(changed["Percentage"])
            if event == "below":
                cond = pct <= threshold
            else:
                cond = pct >= threshold

            if cond and not state_cache["triggered"]:
                state_cache["triggered"] = True
                fire_callback(context=f"{int(pct)}%")
            elif not cond:
                state_cache["triggered"] = False

    sub_id = bus.signal_subscribe(
        "org.freedesktop.UPower",
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        dev_path,
        None,
        Gio.DBusSignalFlags.NONE,
        on_props_changed,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch