from gi.repository import GLib

MODE = "trigger"
CATEGORY = "schedule"
TYPE = "interval_timer"
LABEL = "Repeat Interval"
DESCRIPTION = "Triggers repeatedly every N minutes while this automation is enabled."

SCHEMA = [
    {
        "key": "minutes",
        "type": "int",
        "title": "Interval (minutes)",
        "min": 1,
        "max": 1440,
        "default": 30,
    }
]


def format_subtitle(params: dict) -> str:
    mins = int(params.get("minutes", 30))
    return f"Every {mins} minute{'s' if mins != 1 else ''}"


def start_watch(trigger, fire_callback):
    mins = max(1, int(trigger.params.get("minutes", 30)))

    def on_tick():
        fire_callback(context=f"interval:{mins}m")
        return True  # Fut tovább a következő ciklusig

    source_id = GLib.timeout_add_seconds(mins * 60, on_tick)

    def stop_watch():
        try:
            GLib.source_remove(source_id)
        except Exception:
            pass

    return stop_watch