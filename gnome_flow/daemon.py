import json
import time
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from .model import Flow, load_flows, save_flows
from .engine import FlowEngine

from datetime import datetime

BUS_NAME = "org.gnome.Flow.Daemon"
OBJECT_PATH = "/org/gnome/Flow/Daemon"

# D-Bus interfész definíciója (ezen keresztül kommunikál a CLI és a GUI a daemonnal)
DBUS_XML = """
<node>
  <interface name="org.gnome.Flow.Daemon">
    <method name="RunFlow">
      <arg type="s" name="name_or_slug" direction="in"/>
      <arg type="s" name="context" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <method name="ToggleFlow">
      <arg type="s" name="name_or_slug" direction="in"/>
      <arg type="b" name="new_state" direction="out"/>
    </method>
    <method name="ListFlows">
      <arg type="s" name="json_list" direction="out"/>
    </method>
    <method name="Reload"/>
  </interface>
</node>
"""


class FlowDaemon:
    def __init__(self):
        self.loop = GLib.MainLoop()
        # A motor újratölti a figyelőket, ha egy akció ki/bekapcsolt egy másik szabályt
        self.engine = FlowEngine(on_flows_changed=self.reload_watchers)
        self.flows = []
        self.dir_monitors = []          # Aktív Gio.FileMonitor példányok tárolója (hogy ne szedje össze a GC)
        self.trigger_timestamps = {}    # 'all' (ÉS) módú triggerek időbélyegei: {(flow_id, trigger_id): timestamp}
        # időzítő
        self._last_schedule_key = ""
        self._schedule_next_minute_check()
        # Rendszerbusz csatlakozás az UDisks2 meghajtó-figyeléshez
        self.system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self._setup_udisks_watcher()

    def start(self):
        """Elindítja a D-Bus szolgáltatást és betölti a figyelőket."""
        Gio.bus_own_name(
            Gio.BusType.SESSION,
            BUS_NAME,
            Gio.BusNameOwnerFlags.NONE,
            self._on_bus_acquired,
            None,
            None,
        )
        self.reload_watchers()
        print("[GNOME Flow Daemon] Started and listening...")
        try:
            self.loop.run()
        except KeyboardInterrupt:
            print("\n[GNOME Flow Daemon] Shutting down.")

    def _on_bus_acquired(self, connection, name):
        """Regisztrálja a D-Bus metódusokat a session buszon."""
        node_info = Gio.DBusNodeInfo.new_for_xml(DBUS_XML)
        connection.register_object(
            OBJECT_PATH,
            node_info.interfaces[0],
            self._handle_method_call,
            None,
            None,
        )

    def _handle_method_call(self, connection, sender, object_path, interface_name, method_name, parameters, invocation):
        """Kezeli a CLI-ből vagy GUI-ból érkező D-Bus hívásokat."""
        if method_name == "RunFlow":
            target, context = parameters.unpack()
            ok = self.run_by_name(target, context)
            invocation.return_value(GLib.Variant("(b)", (ok,)))

        elif method_name == "ToggleFlow":
            target, = parameters.unpack()
            state = self.toggle_by_name(target)
            invocation.return_value(GLib.Variant("(b)", (state,)))

        elif method_name == "ListFlows":
            flows = load_flows()
            summary = [{"id": f.id, "name": f.name, "slug": f.slug, "enabled": f.enabled} for f in flows]
            invocation.return_value(GLib.Variant("(s)", (json.dumps(summary),)))

        elif method_name == "Reload":
            self.reload_watchers()
            invocation.return_value(None)

    def reload_watchers(self):
        """Újratölti a szabályokat, a mappafigyelőket és a GNOME gyorsbillentyűket."""
        self.flows = load_flows()
        self.dir_monitors.clear()

        custom_shortcuts = []

        for flow in self.flows:
            if not flow.enabled:
                continue

            for trig in flow.triggers:
                # 1. Mappaváltozás figyelő (GIO FileMonitor)
                if trig.type == "dir_changed":
                    path = trig.params.get("path", "")
                    if path:
                        gfile = Gio.File.new_for_path(path)
                        if gfile.query_exists(None):
                            monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
                            # Zárvány (closure) a pontos flow és trigger azonosítók átadásához
                            monitor.connect("changed", self._on_dir_changed, flow.id, trig.id)
                            self.dir_monitors.append(monitor)

                # 2. Globális gyorsbillentyű összegyűjtése
                elif trig.type == "shortcut":
                    accel = trig.params.get("accel", "")  # pl. '<Control><Alt>k' vagy 'F1'
                    if accel:
                        custom_shortcuts.append((flow.slug, flow.name, accel))

        self._sync_gnome_shortcuts(custom_shortcuts)

    def _sync_gnome_shortcuts(self, shortcuts):
        """Beregisztálja a gyorsbillentyűket a GNOME gyári egyéni gyorsbillentyűi közé."""
        base_schema = "org.gnome.settings-daemon.plugins.media-keys"
        item_schema = f"{base_schema}.custom-keybinding"
        settings = Gio.Settings.new(base_schema)

        existing_paths = list(settings.get_strv("custom-keybindings"))
        # Megtartjuk a nem gnome-flow által kezelt saját gyorsbillentyűket
        kept_paths = [p for p in existing_paths if "/gnome-flow-" not in p]

        new_paths = list(kept_paths)
        for slug, name, accel in shortcuts:
            path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/gnome-flow-{slug}/"
            item_settings = Gio.Settings.new_with_path(item_schema, path)
            item_settings.set_string("name", f"GNOME Flow: {name}")
            item_settings.set_string("command", f"flow {slug}")
            item_settings.set_string("binding", accel)
            if path not in new_paths:
                new_paths.append(path)

        if new_paths != existing_paths:
            settings.set_strv("custom-keybindings", new_paths)
        Gio.Settings.sync()

    def _setup_udisks_watcher(self):
        """Feliratkozik az UDisks2 D-Bus jelére meghajtók csatlakoztatásához."""
        self.system_bus.signal_subscribe(
            "org.freedesktop.UDisks2",
            "org.freedesktop.DBus.ObjectManager",
            "InterfacesAdded",
            "/org/freedesktop/UDisks2",
            None,
            Gio.DBusSignalFlags.NONE,
            self._on_udisks_interfaces_added,
            None,
        )

    def _on_udisks_interfaces_added(self, connection, sender, path, interface, signal_name, parameters, user_data):
        """Akkor fut le, amikor új eszköz vagy fájlrendszer csatlakozik."""
        obj_path, interfaces = parameters.unpack()
        if "org.freedesktop.UDisks2.Filesystem" in interfaces:
            # Kis késleltetés (1 mp), hogy a GNOME/Nautilus biztosan felcsatolja a kötetet
            GLib.timeout_add_seconds(1, self._check_mounted_drive, obj_path)

    def _check_mounted_drive(self, obj_path):
        """Lekérdezi a csatolási útvonalat (MountPoints) az UDisks2-től."""
        try:
            proxy = Gio.DBusProxy.new_sync(
                self.system_bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.UDisks2",
                obj_path,
                "org.freedesktop.UDisks2.Filesystem",
                None,
            )
            mount_points = proxy.get_cached_property("MountPoints")
            if mount_points:
                paths = mount_points.unpack()
                if paths:
                    # A MountPoints bájt-tömbként (ay) érkezik, null-terminátorral a végén
                    raw_bytes = bytes(paths[0]).rstrip(b"\x00")
                    mount_path = raw_bytes.decode("utf-8", errors="ignore")
                    if mount_path:
                        self._fire_trigger_type("drive_mounted", context=mount_path)
        except Exception as e:
            print(f"[GNOME Flow Daemon] UDisks2 read error: {e}")
        return False  # Ne ismétlődjön a timeout

    def _on_dir_changed(self, monitor, file, other_file, event_type, flow_id, trigger_id):
        """Akkor fut le, ha egy figyelt mappában új fájl jön létre vagy módosul."""
        if event_type in (Gio.FileMonitorEvent.CREATED, Gio.FileMonitorEvent.CHANGES_DONE_HINT):
            filepath = file.get_path() or ""
            self._fire_specific_trigger(flow_id, trigger_id, context=filepath)

    def _fire_trigger_type(self, trigger_type: str, context: str = ""):
        """Elsüt minden olyan triggert, amelyik az adott típusra vár (pl. drive_mounted)."""
        for flow in self.flows:
            if not flow.enabled:
                continue
            for trig in flow.triggers:
                if trig.type == trigger_type:
                    # Ha meg van adva név/útvonal szűrő a triggerben, ellenőrizzük
                    filter_str = trig.params.get("filter", "")
                    if filter_str and filter_str not in context:
                        continue
                    self._fire_specific_trigger(flow.id, trig.id, context)

    def _fire_specific_trigger(self, flow_id: str, trigger_id: str, context: str = ""):
        """Kiértékeli a HA ág logikáját ('any' = Bármelyik vs 'all' = Minden feltétel)."""
        flow = next((f for f in self.flows if f.id == flow_id), None)
        if not flow or not flow.enabled:
            return

        if flow.trigger_mode == "any":
            self.engine.execute_flow(flow, context=context)
        else:
            # 'all' mód: minden triggernek be kell futnia egy 10 másodperces időablakon belül
            now = time.time()
            self.trigger_timestamps[(flow.id, trigger_id)] = now
            all_met = all(
                (now - self.trigger_timestamps.get((flow.id, t.id), 0)) <= 10.0
                for t in flow.triggers
            )
            if all_met:
                # Kinullázzuk, hogy ne süljön el duplán
                for t in flow.triggers:
                    self.trigger_timestamps.pop((flow.id, t.id), None)
                self.engine.execute_flow(flow, context=context)

    def run_by_name(self, name_or_slug: str, context: str = "") -> bool:
        """Név vagy slug alapján elindít egy automatizmust (CLI vagy gyorsbillentyű hívja)."""
        target_slug = Flow.make_slug(name_or_slug)
        for flow in load_flows():
            if flow.slug == target_slug or flow.name.lower() == name_or_slug.lower() or flow.id == name_or_slug:
                return self.engine.execute_flow(flow, context=context, force=True)
        print(f"[GNOME Flow] Flow not found: '{name_or_slug}'")
        return False

    def toggle_by_name(self, name_or_slug: str) -> bool:
        """Ki- vagy bekapcsol egy automatizmust név alapján."""
        target_slug = Flow.make_slug(name_or_slug)
        flows = load_flows()
        for flow in flows:
            if flow.slug == target_slug or flow.name.lower() == name_or_slug.lower():
                flow.enabled = not flow.enabled
                save_flows(flows)
                self.reload_watchers()
                return flow.enabled
        return False
    
    def _schedule_next_minute_check(self):
        delay = max(1, 60 - datetime.now().second)
        GLib.timeout_add_seconds(delay, self._check_schedules)

    def _check_schedules(self) -> bool:
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_day = now.weekday()  # 0 = Hétfő ... 6 = Vasárnap
        minute_key = now.strftime("%Y-%m-%d %H:%M")

        if minute_key == self._last_schedule_key:
            return True

        for flow in self.flows:
            if not flow.enabled:
                continue
            for trig in flow.triggers:
                if trig.category == "schedule" and trig.type == "time":
                    if (
                        trig.params.get("time") == current_time
                        and current_day in trig.params.get("days", [])
                    ):
                        self._last_schedule_key = minute_key
                        self.engine.execute_flow(flow, context=current_time)
                        break

        return True