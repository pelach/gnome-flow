import datetime
import subprocess
import time
import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib
from .model import Flow, Block, load_flows, save_flows
from .plugins import get_plugin


class FlowEngine:
    def __init__(self, on_flows_changed=None):
        self.on_flows_changed = on_flows_changed

    def check_scope(self, flow: Flow) -> bool:
        """Kiértékeli az Érvényességi kört (Hatékony időszak + Feltételek)."""
        scope = flow.scope
        now = datetime.datetime.now()

        # 1. Hatékony időszak ellenőrzése
        if scope.time_enabled:
            if now.weekday() not in scope.days:
                return False
            try:
                sh, sm = map(int, scope.start_time.split(":"))
                eh, em = map(int, scope.end_time.split(":"))
                start_t = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
                end_t = now.replace(hour=eh, minute=em, second=59, microsecond=0)
                if start_t <= end_t:
                    if not (start_t <= now <= end_t):
                        return False
                else:
                    # Éjszakába nyúló időszak (pl. 22:00 - 06:00)
                    if not (now >= start_t or now <= end_t):
                        return False
            except ValueError:
                pass

        # 2. Feltételek ellenőrzése (Bármilyen / Összes)
        if not scope.conditions:
            return True

        results = [self._eval_condition(c) for c in scope.conditions]
        if scope.condition_mode == "all":
            return all(results)
        return any(results)

    def _eval_condition(self, cond: Block) -> bool:
        ctype = cond.type
        p = cond.params

        if ctype == "app_running":
            proc_name = p.get("process", "")
            if not proc_name:
                return False
            res = subprocess.run(["pgrep", "-f", proc_name], capture_output=True)
            return res.returncode == 0

        if ctype == "file_exists":
            path = p.get("path", "")
            return bool(path) and Gio.File.new_for_path(path).query_exists(None)

        if ctype == "flow_enabled":
            target_id = p.get("flow_id", "")
            for f in load_flows():
                if f.id == target_id:
                    return f.enabled
            return False

        if ctype == "dark_mode":
            settings = Gio.Settings.new("org.gnome.desktop.interface")
            scheme = settings.get_string("color-scheme")
            want_dark = p.get("dark", True)
            return (scheme == "prefer-dark") == want_dark

        # Plug-in feltétel kiértékelése
        plugin = get_plugin(ctype)
        if plugin and hasattr(plugin, "check"):
            try:
                return bool(plugin.check(p))
            except Exception as e:
                print(f"[GNOME Flow] Condition plugin '{ctype}' error: {e}")
                return False

        return True

    def execute_flow(self, flow: Flow, context: str = "", force: bool = False) -> bool:
        """Lefuttatja az automatizmust. force=True esetén (pl. kézi indítás) is ellenőrzi a scope-ot, hacsak ki nincs kapcsolva."""
        if not flow.enabled and not force:
            return False

        if not self.check_scope(flow):
            print(f"[GNOME Flow] Skipped '{flow.name}' (validity scope not met).")
            return False

        print(f"[GNOME Flow] Running '{flow.name}' (context='{context}')")
        for action in flow.actions:
            self._run_action(action, context)

        # Láncolt szabályok értesítése ('flow_finished' trigger)
        self._trigger_chained_flows(flow.id, context)
        return True

    def _run_action(self, action: Block, context: str):
        atype = action.type
        p = action.params

        def sub(val: str) -> str:
            return val.replace("{context}", context) if isinstance(val, str) else val

        if atype == "open_app":
            desktop_id = p.get("desktop_id", "")
            if desktop_id:
                app_info = Gio.DesktopAppInfo.new(desktop_id)
                if app_info:
                    app_info.launch([], None)

        elif atype == "open_path":
            target = sub(p.get("path", "")) or context
            if target:
                uri = target if "://" in target else Gio.File.new_for_path(target).get_uri()
                Gio.AppInfo.launch_default_for_uri(uri, None)

        elif atype == "notify":
            title = sub(p.get("title", "GNOME Flow"))
            body = sub(p.get("body", ""))
            subprocess.Popen(["notify-send", "-a", "GNOME Flow", title, body])

        elif atype == "delay":
            sec = float(p.get("seconds", 1))
            time.sleep(sec)

        elif atype == "command":
            cmd = sub(p.get("command", ""))
            if cmd:
                subprocess.Popen(cmd, shell=True)

        elif atype == "toggle_flow":
            target_id = p.get("flow_id", "")
            mode = p.get("state", "enable")  # 'enable', 'disable', 'toggle', 'run'
            flows = load_flows()
            changed = False
            for f in flows:
                if f.id == target_id:
                    if mode == "run":
                        self.execute_flow(f, context=context, force=True)
                        return
                    elif mode == "enable":
                        f.enabled = True
                    elif mode == "disable":
                        f.enabled = False
                    elif mode == "toggle":
                        f.enabled = not f.enabled
                    changed = True
            if changed:
                save_flows(flows)
                if self.on_flows_changed:
                    self.on_flows_changed()

        else:
            # Plug-in művelet futtatása
            plugin = get_plugin(atype)
            if plugin and hasattr(plugin, "run"):
                try:
                    resolved_params = {k: sub(v) for k, v in p.items()}
                    plugin.run(resolved_params, context=context)
                except Exception as e:
                    print(f"[GNOME Flow] Action plugin '{atype}' error: {e}")

    def _trigger_chained_flows(self, finished_flow_id: str, context: str):
        for f in load_flows():
            if not f.enabled or f.id == finished_flow_id:
                continue
            for trig in f.triggers:
                if trig.type == "flow_finished" and trig.params.get("flow_id") == finished_flow_id:
                    self.execute_flow(f, context=context)