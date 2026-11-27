from gi.repository import Gio, GLib

MODE = "action"
CATEGORY = "audio"
CATEGORY_TITLE = "Audio & Media"
CATEGORY_ICON = "audio-speakers-symbolic"
TYPE = "media_control"
LABEL = "Media Playback (MPRIS)"
DESCRIPTION = "Control active media players (Play/Pause, Next, Previous, Stop)."

SCHEMA = [
    {
        "key": "command",
        "type": "choice",
        "title": "Playback Command",
        "options": [
            ("PlayPause", "Play / Pause Toggle"),
            ("Play", "Play"),
            ("Pause", "Pause"),
            ("Next", "Next Track"),
            ("Previous", "Previous Track"),
            ("Stop", "Stop"),
        ],
        "default": "PlayPause",
    },
    {
        "key": "player_filter",
        "type": "entry",
        "title": "Player Filter (optional, e.g. amberol, chromium)",
        "default": "",
    },
]

_CMD_LABELS = {
    "PlayPause": "Play / Pause",
    "Play": "Play",
    "Pause": "Pause",
    "Next": "Next Track",
    "Previous": "Previous Track",
    "Stop": "Stop",
}


def format_subtitle(params: dict) -> str:
    cmd = params.get("command", "PlayPause")
    flt = params.get("player_filter", "").strip()
    label = _CMD_LABELS.get(cmd, cmd)
    return f"{label} ({flt})" if flt else label


def run(params: dict, context: str = "") -> bool:
    command = params.get("command", "PlayPause")
    flt = params.get("player_filter", "").strip().lower()

    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    res = bus.call_sync(
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "ListNames",
        None,
        GLib.VariantType("(as)"),
        Gio.DBusCallFlags.NONE,
        -1,
        None,
    )
    names = res.unpack()[0]
    players = [
        n for n in names
        if n.startswith("org.mpris.MediaPlayer2.") and (not flt or flt in n.lower())
    ]

    if not players:
        print(f"[GNOME Flow] No matching MPRIS media player found (filter='{flt}').")
        return False

    ok = False
    for dest in players:
        try:
            bus.call_sync(
                dest,
                "/org/mpris/MediaPlayer2",
                "org.mpris.MediaPlayer2.Player",
                command,
                None,
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
            ok = True
        except Exception as e:
            print(f"[GNOME Flow] MPRIS call failed for {dest}: {e}")

    return ok