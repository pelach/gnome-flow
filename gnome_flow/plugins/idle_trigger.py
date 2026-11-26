from gi.repository import Gio, GLib

MODE = "trigger"
CATEGORY = "user_idle"
CATEGORY_TITLE = "User Idle"
CATEGORY_ICON = "preferences-desktop-screensaver-symbolic"
TYPE = "user_idle"
LABEL = "User Idle"
DESCRIPTION = "Triggers after the keyboard and mouse have been inactive for the given seconds."

SCHEMA = [
    {
        "key": "seconds",
        "type": "int",
        "title": "Idle Timeout (seconds)",
        "min": 5,
        "max": 86400,
        "default": 300,
    }
]


def format_subtitle(params: dict) -> str:
    sec = int(params.get("seconds", 300))
    return f"After {sec} seconds of inactivity"


def start_watch(trigger, fire_callback):
    """Feliratkozik a GNOME Mutter IdleMonitor D-Bus jelére, és visszaad egy leállító függvényt."""
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    proxy = Gio.DBusProxy.new_sync(
        bus,
        Gio.DBusProxyFlags.NONE,
        None,
        "org.gnome.Mutter.IdleMonitor",
        "/org/gnome/Mutter/IdleMonitor/Core",
        "org.gnome.Mutter.IdleMonitor",
        None,
    )

    timeout_ms = int(trigger.params.get("seconds", 300)) * 1000
    res = proxy.call_sync(
        "AddIdleWatch",
        GLib.Variant("(t)", (timeout_ms,)),
        Gio.DBusCallFlags.NONE,
        -1,
        None,
    )
    watch_id = res.unpack()[0]

    def on_watch_fired(_conn, _sender, _path, _iface, _signal, params, _data):
        fired_id, = params.unpack()
        if fired_id == watch_id:
            fire_callback(context=f"idle:{timeout_ms // 1000}s")

    sub_id = bus.signal_subscribe(
        "org.gnome.Mutter.IdleMonitor",
        "org.gnome.Mutter.IdleMonitor",
        "WatchFired",
        "/org/gnome/Mutter/IdleMonitor/Core",
        None,
        Gio.DBusSignalFlags.NONE,
        on_watch_fired,
        None,
    )

    def stop_watch():
        try:
            bus.signal_unsubscribe(sub_id)
            proxy.call_sync(
                "RemoveWatch",
                GLib.Variant("(u)", (watch_id,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
        except Exception:
            pass

    return stop_watch