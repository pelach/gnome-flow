import subprocess

MODE = "action"
CATEGORY = "network"
TYPE = "set_bluetooth"
LABEL = "Bluetooth Control"
DESCRIPTION = "Turn Bluetooth adapter on/off, or connect/disconnect a paired device by MAC address."

SCHEMA = [
    {
        "key": "mode",
        "type": "choice",
        "title": "Bluetooth Action",
        "options": [
            ("toggle", "Toggle Bluetooth Power"),
            ("on", "Turn Bluetooth On"),
            ("off", "Turn Bluetooth Off"),
            ("connect", "Connect Device (by MAC)"),
            ("disconnect", "Disconnect Device (by MAC)"),
        ],
        "default": "toggle",
    },
    {
        "key": "mac",
        "type": "str",
        "title": "Device MAC Address (e.g. AA:BB:CC:11:22:33)",
        "default": "",
    },
]


def format_subtitle(params: dict) -> str:
    mode = params.get("mode", "toggle")
    mac = params.get("mac", "").strip()
    if mode in ("connect", "disconnect"):
        return f"{mode.capitalize()} {mac or '(no MAC)'}"
    labels = {
        "toggle": "Toggle Bluetooth",
        "on": "Turn Bluetooth On",
        "off": "Turn Bluetooth Off",
    }
    return labels.get(mode, "Toggle Bluetooth")


def run(params: dict, context: str = "") -> bool:
    mode = params.get("mode", "toggle")
    mac = params.get("mac", "").strip()

    if mode == "on":
        subprocess.run(["bluetoothctl", "power", "on"], check=False)
    elif mode == "off":
        subprocess.run(["bluetoothctl", "power", "off"], check=False)
    elif mode == "toggle":
        out = subprocess.check_output(["bluetoothctl", "show"], text=True)
        is_on = "Powered: yes" in out
        subprocess.run(["bluetoothctl", "power", "off" if is_on else "on"], check=False)
    elif mode == "connect" and mac:
        subprocess.run(["bluetoothctl", "connect", mac], check=False)
    elif mode == "disconnect" and mac:
        subprocess.run(["bluetoothctl", "disconnect", mac], check=False)
    return True