from gi.repository import Gio

MODE = "trigger"
CATEGORY = "power"
CATEGORY_TITLE = "Power"
CATEGORY_ICON = "battery-good-symbolic"
TYPE = "power_profile_changed"
LABEL = "Power Profile / Saver"
DESCRIPTION = "Triggers when the system power profile changes. Passes active profile as {context}."

SCHEMA = [
    {
        "key": "profile",
        "type": "choice",
        "title": "Target Power Profile",
        "options": [
            ("power-saver", "Power Saver Activated"),
            ("balanced", "Balanced Activated"),
            ("performance", "Performance Activated"),
            ("any", "Any Profile Change"),
        ],
        "default": "power-saver",
    },
]


def format_subtitle(params: dict) -> str:
    prof = params.get("profile", "power-saver")
    labels = {
        "power-saver": "Power Saver mode",
        "balanced": "Balanced mode",
        "performance": "Performance mode",
        "any": "Any profile change",
    }
    return f"Power profile: {labels.get(prof, prof)}"


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    target = trigger.params.get("profile", "power-saver")

    def on_profile_props(_conn, _sender, _path, _iface, _signal, params, _data):
        iface_name, changed, _invalidated = params.unpack()
        if iface_name in ("org.freedesktop.UPower.PowerProfiles", "net.hadess.PowerProfiles") and "ActiveProfile" in changed:
            active = str(changed["ActiveProfile"])
            if target == "any" or active == target:
                fire_callback(context=active)

    sub_id = bus.signal_subscribe(
        None,
        "org.freedesktop.DBus.Properties",
        "PropertiesChanged",
        "/org/freedesktop/UPower/PowerProfiles",
        None,
        Gio.DBusSignalFlags.NONE,
        on_profile_props,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch