from gi.repository import Gio, GLib

MODE = "trigger"
CATEGORY = "network"
CATEGORY_TITLE = "Network"
CATEGORY_ICON = "network-wireless-signal-excellent-symbolic"
TYPE = "wifi_event"
LABEL = "Wi-Fi Connection"
DESCRIPTION = "Triggers when connecting to or disconnecting from Wi-Fi (any or specific network)."

SCHEMA = [
    {
        "key": "event",
        "type": "choice",
        "title": "Wi-Fi Event",
        "options": [
            ("connected", "Connected to Wi-Fi"),
            ("disconnected", "Disconnected from Wi-Fi"),
        ],
        "default": "connected",
    },
    {
        "key": "ssid",
        "type": "str",
        "title": "Network Name / SSID (leave empty for any)",
        "default": "",
    },
]


def _get_active_wifi_ssids(bus: Gio.DBusConnection) -> set[str]:
    """Közvetlen D-Bus lekérdezés alfolyamat (nmcli) indítása nélkül."""
    ssids = set()
    try:
        nm_proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS,
            None,
            "org.freedesktop.NetworkManager",
            "/org/freedesktop/NetworkManager",
            "org.freedesktop.NetworkManager",
            None,
        )
        active_conns = nm_proxy.get_cached_property("ActiveConnections")
        if not active_conns:
            return ssids

        for path in active_conns.unpack():
            ac_proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS,
                None,
                "org.freedesktop.NetworkManager",
                path,
                "org.freedesktop.NetworkManager.Connection.Active",
                None,
            )
            ctype = ac_proxy.get_cached_property("Type")
            cstate = ac_proxy.get_cached_property("State")
            cid = ac_proxy.get_cached_property("Id")
            # State == 2 jelenti az aktív (Activated) kapcsolatot
            if (
                ctype and ctype.unpack() == "802-11-wireless"
                and cstate and cstate.unpack() == 2
                and cid
            ):
                ssids.add(cid.unpack())
    except Exception:
        pass
    return ssids


def format_subtitle(params: dict) -> str:
    ev = params.get("event", "connected")
    ssid = params.get("ssid", "").strip()
    target = f"'{ssid}'" if ssid else "any network"
    return f"{'Connected to' if ev == 'connected' else 'Disconnected from'} {target}"


def start_watch(trigger, fire_callback):
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    event = trigger.params.get("event", "connected")
    target_ssid = trigger.params.get("ssid", "").strip()

    state = {
        "last_ssids": _get_active_wifi_ssids(bus),
        "debounce_id": 0,
    }

    def _evaluate_change():
        state["debounce_id"] = 0
        current_ssids = _get_active_wifi_ssids(bus)
        added = current_ssids - state["last_ssids"]
        removed = state["last_ssids"] - current_ssids
        state["last_ssids"] = current_ssids

        if event == "connected" and added:
            for ssid in added:
                if not target_ssid or ssid == target_ssid:
                    fire_callback(context=ssid)
                    break

        elif event == "disconnected" and removed:
            for ssid in removed:
                if not target_ssid or ssid == target_ssid:
                    fire_callback(context=ssid)
                    break

        return False  # Egyszeri lefutás

    def on_nm_props(_conn, _sender, _path, _iface, _signal, params, _data):
        iface_name, changed, _invalidated = params.unpack()
        if iface_name != "org.freedesktop.NetworkManager":
            return
        if "ActiveConnections" not in changed and "State" not in changed:
            return

        # 800 ms debounce: megvárjuk, míg a lecsatlakozás/felcsatlakozás lezajlik
        if state["debounce_id"]:
            GLib.source_remove(state["debounce_id"])
        state["debounce_id"] = GLib.timeout_add(800, _evaluate_change)

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
        if state["debounce_id"]:
            try:
                GLib.source_remove(state["debounce_id"])
            except Exception:
                pass
        try:
            bus.signal_unsubscribe(sub_id)
        except Exception:
            pass

    return stop_watch