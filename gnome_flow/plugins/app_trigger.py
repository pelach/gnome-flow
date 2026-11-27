import os
from gi.repository import GLib

MODE = "trigger"
CATEGORY = "app"
CATEGORY_TITLE = "Applications"
CATEGORY_ICON = "application-x-executable-symbolic"
TYPE = "app_state"
LABEL = "Application Opened / Closed"
DESCRIPTION = "Triggers when a specific application starts or exits. Passes the process name as {context}."

SCHEMA = [
    {
        "key": "process",
        "type": "app_picker",
        "title": "Process / App Name (e.g. firefox, code, gimp)",
        "default": "",
    },
    {
        "key": "event",
        "type": "choice",
        "title": "Trigger When",
        "options": [
            ("opened", "Application Opened"),
            ("closed", "Application Closed"),
        ],
        "default": "opened",
    },
]


def format_subtitle(params: dict) -> str:
    proc = params.get("process", "").strip() or "(unset)"
    ev = params.get("event", "opened")
    return f"{proc} {ev}"


def _is_process_running(target: str) -> bool:
    if not target:
        return False
    low = target.lower()
    try:
        for entry in os.scandir("/proc"):
            if not entry.name.isdigit():
                continue
            try:
                with open(os.path.join(entry.path, "comm"), "r", encoding="utf-8", errors="ignore") as f:
                    if low in f.read().strip().lower():
                        return True
                with open(os.path.join(entry.path, "cmdline"), "rb") as f:
                    cmd = f.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore").lower()
                    if low in cmd:
                        return True
            except OSError:
                continue
    except Exception:
        pass
    return False


def start_watch(trigger, fire_callback):
    target = trigger.params.get("process", "").strip()
    event = trigger.params.get("event", "opened")
    was_running = _is_process_running(target)

    def _poll() -> bool:
        nonlocal was_running
        if not target:
            return True
        now_running = _is_process_running(target)
        if now_running and not was_running and event == "opened":
            fire_callback(context=target)
        elif not now_running and was_running and event == "closed":
            fire_callback(context=target)
        was_running = now_running
        return True

    timer_id = GLib.timeout_add_seconds(2, _poll)

    def stop_watch():
        try:
            GLib.source_remove(timer_id)
        except Exception:
            pass

    return stop_watch