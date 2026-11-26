import shutil
import subprocess

MODE = "action"
CATEGORY = "audio"
CATEGORY_TITLE = "Audio"
CATEGORY_ICON = "audio-volume-high-symbolic"
TYPE = "set_volume"
LABEL = "System Volume"
DESCRIPTION = "Set master output volume percentage or toggle mute."

SCHEMA = [
    {
        "key": "mode",
        "type": "choice",
        "title": "Action",
        "options": [
            ("set", "Set Volume Level (%)"),
            ("mute_toggle", "Toggle Mute"),
            ("mute", "Mute Audio"),
            ("unmute", "Unmute Audio"),
        ],
        "default": "set",
    },
    {
        "key": "level",
        "type": "int",
        "title": "Volume Percentage (for Set Level)",
        "min": 0,
        "max": 100,
        "step": 5,
        "default": 50,
    },
]


def format_subtitle(params: dict) -> str:
    mode = params.get("mode", "set")
    if mode == "set":
        return f"Set volume to {int(params.get('level', 50))}%"
    labels = {
        "mute_toggle": "Toggle Mute",
        "mute": "Mute",
        "unmute": "Unmute",
    }
    return labels.get(mode, "Set Volume")


def run(params: dict, context: str = "") -> bool:
    mode = params.get("mode", "set")
    level = max(0, min(100, int(params.get("level", 50))))

    if shutil.which("wpctl"):
        sink = "@DEFAULT_AUDIO_SINK@"
        if mode == "set":
            subprocess.run(["wpctl", "set-volume", sink, f"{level}%"], check=False)
        elif mode == "mute_toggle":
            subprocess.run(["wpctl", "set-mute", sink, "toggle"], check=False)
        elif mode == "mute":
            subprocess.run(["wpctl", "set-mute", sink, "1"], check=False)
        elif mode == "unmute":
            subprocess.run(["wpctl", "set-mute", sink, "0"], check=False)
        return True

    if shutil.which("pactl"):
        sink = "@DEFAULT_SINK@"
        if mode == "set":
            subprocess.run(["pactl", "set-sink-volume", sink, f"{level}%"], check=False)
        elif mode == "mute_toggle":
            subprocess.run(["pactl", "set-sink-mute", sink, "toggle"], check=False)
        elif mode == "mute":
            subprocess.run(["pactl", "set-sink-mute", sink, "1"], check=False)
        elif mode == "unmute":
            subprocess.run(["pactl", "set-sink-mute", sink, "0"], check=False)
        return True

    return False