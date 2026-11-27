import re
import subprocess

MODE = "action"
CATEGORY = "audio"
CATEGORY_TITLE = "Audio & Media"
CATEGORY_ICON = "audio-speakers-symbolic"
TYPE = "audio_output"
LABEL = "Audio Output Device"
DESCRIPTION = "Switch the default PipeWire audio output device or cycle through available outputs."


def _get_sinks() -> list[tuple[str, str, bool]]:
    """Visszaadja a PipeWire sinkek listáját: [(id, leírás, aktív_e), ...]"""
    try:
        out = subprocess.check_output(["wpctl", "status"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []

    sinks: list[tuple[str, str, bool]] = []
    in_audio = False
    in_sinks = False

    for raw_line in out.splitlines():
        line = raw_line.strip()
        if line == "Audio":
            in_audio = True
            continue
        if in_audio and line in ("Video", "Settings"):
            break
        if in_audio and "Sinks:" in line:
            in_sinks = True
            continue
        if in_sinks:
            if line.endswith(":") and not re.search(r"\d+\.", line):
                break
            m = re.search(r"(\*)?\s*(\d+)\.\s+(.+?)(?:\s+\[vol:.*\])?$", line)
            if m:
                is_default = bool(m.group(1))
                sink_id = m.group(2)
                desc = m.group(3).strip()
                sinks.append((sink_id, desc, is_default))

    return sinks


def _build_device_options() -> list[tuple[str, str]]:
    options = [("__cycle__", "Cycle to Next Output Device")]
    for _, desc, _ in _get_sinks():
        options.append((desc, desc))
    return options


SCHEMA = [
    {
        "key": "device",
        "type": "choice",
        "title": "Output Device",
        "options": _build_device_options(),
        "default": "__cycle__",
    },
]


def format_subtitle(params: dict) -> str:
    dev = params.get("device", "__cycle__")
    if dev == "__cycle__" or not dev:
        return "Cycle to next audio output"
    return f"Output: {dev}"


def run(params: dict, context: str = "") -> bool:
    target = params.get("device", "__cycle__")
    sinks = _get_sinks()

    if not sinks:
        print("[GNOME Flow] No PipeWire audio sinks found.")
        return False

    if target == "__cycle__" or not target:
        if len(sinks) == 1:
            return True
        cur_idx = next((i for i, s in enumerate(sinks) if s[2]), 0)
        next_sink = sinks[(cur_idx + 1) % len(sinks)]
        subprocess.run(["wpctl", "set-default", next_sink[0]], check=False)
        print(f"[GNOME Flow] Switched audio output to: {next_sink[1]}")
        return True

    target_low = target.lower()
    for sink_id, desc, _ in sinks:
        if desc.lower() == target_low or target_low in desc.lower():
            subprocess.run(["wpctl", "set-default", sink_id], check=False)
            print(f"[GNOME Flow] Switched audio output to: {desc}")
            return True

    print(f"[GNOME Flow] Audio output '{target}' not currently available.")
    return False