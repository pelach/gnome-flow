#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

# Hozzáadjuk a projekt gyökerét a modulkeresési útvonalhoz (így telepítés nélkül is fut)
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from gnome_flow.daemon import FlowDaemon, BUS_NAME, OBJECT_PATH
from gnome_flow.engine import FlowEngine
from gnome_flow.model import Flow, load_flows


def get_daemon_proxy():
    """Megpróbál csatlakozni a háttérben futó daemonhoz D-Bus-on keresztül."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            BUS_NAME,
            OBJECT_PATH,
            BUS_NAME,
            None,
        )
        # Ellenőrizzük, él-e a szolgáltatás tulajdonosa
        if proxy.get_name_owner():
            return proxy
    except Exception:
        pass
    return None


def ensure_daemon_running():
    """Ha még nem fut a háttérszolgáltatás, elindítja a háttérben."""
    if not get_daemon_proxy():
        script_path = str(Path(__file__).resolve())
        subprocess.Popen(
            [sys.executable, script_path, "--daemon"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


def main():
    parser = argparse.ArgumentParser(
        prog="flow",
        description="GNOME Flow - Visual event-driven desktop automation",
    )
    parser.add_argument(
        "flow_name",
        nargs="?",
        help="Name or slug of the flow to run (e.g. 'flow dandelion')",
    )
    parser.add_argument(
        "-c", "--context",
        default="",
        help="Optional context string passed to {context} placeholder",
    )
    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="List all configured flows",
    )
    parser.add_argument(
        "-t", "--toggle",
        metavar="NAME",
        help="Enable or disable a flow by name",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run the background event listener service",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload daemon watchers",
    )

    args = parser.parse_args()

    # 1. Háttérszolgáltatás indítása
    if args.daemon:
        daemon = FlowDaemon()
        daemon.start()
        return

    # 2. Konfiguráció újratöltése a daemonban
    if args.reload:
        proxy = get_daemon_proxy()
        if proxy:
            proxy.call_sync("Reload", None, Gio.DBusCallFlags.NONE, -1, None)
            print("Daemon reloaded.")
        else:
            ensure_daemon_running()
            print("Daemon started.")
        return

    # 3. Automatizmusok listázása CLI-ben
    if args.list:
        flows = load_flows()
        if not flows:
            print("No flows configured yet.")
            return
        for f in flows:
            status = "ON " if f.enabled else "OFF"
            print(f"[{status}] {f.name}  (cli: flow {f.slug})")
        return

    # 4. Automatizmus ki/bekapcsolása név alapján
    if args.toggle:
        proxy = get_daemon_proxy()
        if proxy:
            res = proxy.call_sync("ToggleFlow", GLib.Variant("(s)", (args.toggle,)), Gio.DBusCallFlags.NONE, -1, None)
            state = res.unpack()[0]
            print(f"'{args.toggle}' is now {'ENABLED' if state else 'DISABLED'}.")
        else:
            print("Daemon is not running. Start GUI or 'flow --daemon' first.")
        return

    # 5. Konkrét automatizmus futtatása név alapján (pl. 'flow dandelion')
    if args.flow_name:
        proxy = get_daemon_proxy()
        if proxy:
            res = proxy.call_sync(
                "RunFlow",
                GLib.Variant("(ss)", (args.flow_name, args.context)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            ok = res.unpack()[0]
            sys.exit(0 if ok else 1)
        else:
            # Ha nem fut a daemon, közvetlenül is le tudjuk futtatni egyszeri alkalommal
            engine = FlowEngine()
            target_slug = Flow.make_slug(args.flow_name)
            for f in load_flows():
                if f.slug == target_slug or f.name.lower() == args.flow_name.lower():
                    ok = engine.execute_flow(f, context=args.context, force=True)
                    sys.exit(0 if ok else 1)
            print(f"Flow not found: '{args.flow_name}'")
            sys.exit(1)

    # 6. Paraméter nélkül: elindítja a daemont (ha még nem fut) és megnyitja a Libadwaita GUI-t
    ensure_daemon_running()
    from gnome_flow.ui.window import run_gui
    run_gui()


if __name__ == "__main__":
    main()