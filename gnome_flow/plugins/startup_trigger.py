from gi.repository import GLib

MODE = "trigger"
CATEGORY = "schedule"
TYPE = "startup"
LABEL = "Session / Daemon Startup"
DESCRIPTION = "Triggers once when the GNOME session or GNOME Flow daemon starts."

SCHEMA = [
    {
        "key": "delay",
        "type": "int",
        "title": "Delay After Startup (seconds)",
        "min": 0,
        "max": 300,
        "step": 1,
        "default": 3,
    },
]


def format_subtitle(params: dict) -> str:
    sec = int(params.get("delay", 3))
    return f"On startup (after {sec}s)" if sec > 0 else "Immediately on startup"


def start_watch(trigger, fire_callback):
    delay = max(0, int(trigger.params.get("delay", 3)))
    cancelled = False

    def _on_fire():
        if not cancelled:
            fire_callback(context="startup")
        return False

    timer_id = GLib.timeout_add_seconds(delay, _on_fire)

    def stop_watch():
        nonlocal cancelled
        cancelled = True
        try:
            GLib.source_remove(timer_id)
        except Exception:
            pass

    return stop_watch