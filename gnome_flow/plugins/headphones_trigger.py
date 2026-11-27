import subprocess
from gi.repository import Gio, GLib

MODE = "trigger"
CATEGORY = "audio"
CATEGORY_TITLE = "Audio"
CATEGORY_ICON = "audio-headphones-symbolic"
TYPE = "headphones_event"
LABEL = "Wired Headphones"
DESCRIPTION = "Triggers when wired headphones are plugged in or unplugged."

SCHEMA = [
    {
        "key": "state",
        "type": "choice",
        "title": "Headphones Event",
        "options": [
            ("plugged", "Plugged In"),
            ("unplugged", "Unplugged"),
            ("any", "Any Change"),
        ],
        "default": "plugged",
    },
]


def format_subtitle(params: dict) -> str:
    st = params.get("state", "plugged")
    labels = {"plugged": "Plugged in", "unplugged": "Unplugged", "any": "Any change"}
    return f"Headphones: {labels.get(st, st)}"


def _are_headphones_plugged() -> bool | None:
    try:
        out = subprocess.check_output(["pactl", "list", "sinks"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            low = line.lower()
            if "headphones" in low and "availability:" in low:
                return "not available" not in low
    except Exception:
        pass
    return None


def start_watch(trigger, fire_callback):
    wanted = trigger.params.get("state", "plugged")
    last_state = {"plugged": _are_headphones_plugged()}
    proc = None
    cancellable = Gio.Cancellable()

    def _read_line(stream):
        def _on_line(src, res):
            try:
                line, _ = src.read_line_finish_utf8(res)
                if line is None:
                    return
                if "on sink" in line or "on card" in line:
                    cur = _are_headphones_plugged()
                    if cur is not None and cur != last_state["plugged"]:
                        last_state["plugged"] = cur
                        if wanted == "any" or (wanted == "plugged" and cur) or (wanted == "unplugged" and not cur):
                            fire_callback(context="plugged" if cur else "unplugged")
                if not cancellable.is_cancelled():
                    src.read_line_async(GLib.PRIORITY_DEFAULT, cancellable, _on_line)
            except Exception:
                pass

        stream.read_line_async(GLib.PRIORITY_DEFAULT, cancellable, _on_line)

    try:
        proc = Gio.Subprocess.new(
            ["pactl", "subscribe"],
            Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE,
        )
        stdout = proc.get_stdout_pipe()
        if stdout:
            data_stream = Gio.DataInputStream.new(stdout)
            _read_line(data_stream)
    except Exception as e:
        print(f"[GNOME Flow] headphones_trigger error: {e}")

    def stop_watch():
        cancellable.cancel()
        if proc:
            try:
                proc.force_exit()
            except Exception:
                pass

    return stop_watch