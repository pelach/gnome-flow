import os
import shutil
import subprocess

MODE = "action"
CATEGORY = "audio"
CATEGORY_TITLE = "Audio & Media"
CATEGORY_ICON = "audio-speakers-symbolic"
TYPE = "play_sound"
LABEL = "Play Sound / Ping"
DESCRIPTION = "Play a system alert sound or a custom audio file (.wav, .mp3, .ogg) when a flow runs."

SCHEMA = [
    {
        "key": "preset",
        "type": "choice",
        "title": "Sound Preset",
        "options": [
            ("complete", "Task Complete (Ping)"),
            ("bell", "System Bell"),
            ("message-new-instant", "Message Chime"),
            ("dialog-information", "Info Pop"),
            ("dialog-warning", "Warning Alert"),
            ("camera-shutter", "Camera Shutter"),
            ("custom", "Custom Audio File (path below)"),
        ],
        "default": "complete",
    },
    {
        "key": "file_path",
        "type": "entry",
        "title": "Custom Audio File Path (optional, e.g. ~/Music/ding.mp3)",
        "default": "",
    },
]

_PRESET_LABELS = {
    "complete": "Task Complete (Ping)",
    "bell": "System Bell",
    "message-new-instant": "Message Chime",
    "dialog-information": "Info Pop",
    "dialog-warning": "Warning Alert",
    "camera-shutter": "Camera Shutter",
    "custom": "Custom File",
}


def format_subtitle(params: dict) -> str:
    preset = params.get("preset", "complete")
    fpath = params.get("file_path", "").strip()
    if preset == "custom" or fpath:
        name = os.path.basename(fpath) if fpath else "(no file)"
        return f"Play: {name}"
    return f"Sound: {_PRESET_LABELS.get(preset, preset)}"


def _play_file(path: str) -> bool:
    expanded = os.path.expanduser(path)
    if not os.path.isfile(expanded):
        print(f"[GNOME Flow] Sound file not found: {expanded}")
        return False

    # PipeWire pw-play kezeli a wav/ogg/flac/mp3 formátumokat (libsndfile-on keresztül)
    if shutil.which("pw-play"):
        subprocess.Popen(["pw-play", expanded], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    if shutil.which("ffplay"):
        subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", expanded],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    if shutil.which("paplay"):
        subprocess.Popen(["paplay", expanded], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False


def run(params: dict, context: str = "") -> bool:
    preset = params.get("preset", "complete")
    fpath = params.get("file_path", "").strip()

    if preset == "custom" or fpath:
        return _play_file(fpath)

    if shutil.which("canberra-gtk-play"):
        subprocess.Popen(
            ["canberra-gtk-play", "-i", preset, "-d", "GNOME Flow"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    # Tartalék hangfájl, ha a canberra-gtk-play nem lenne telepítve
    fallback = f"/usr/share/sounds/freedesktop/stereo/{preset}.oga"
    return _play_file(fallback)