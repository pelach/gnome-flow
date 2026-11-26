import subprocess

MODE = "action"
CATEGORY = "network"
CATEGORY_TITLE = "Network"
CATEGORY_ICON = "network-wireless-signal-excellent-symbolic"
TYPE = "set_wifi"
LABEL = "Wi-Fi Control"
DESCRIPTION = "Enable, disable, or toggle Wi-Fi radio, or connect to a saved network."

SCHEMA = [
    {
        "key": "mode",
        "type": "choice",
        "title": "Wi-Fi Action",
        "options": [
            ("toggle", "Toggle Wi-Fi On/Off"),
            ("on", "Turn Wi-Fi On"),
            ("off", "Turn Wi-Fi Off"),
            ("connect", "Connect to Specific SSID"),
        ],
        "default": "toggle",
    },
    {
        "key": "ssid",
        "type": "str",
        "title": "Network Name / SSID (for Connect)",
        "default": "",
    },
]


def format_subtitle(params: dict) -> str:
    mode = params.get("mode", "toggle")
    if mode == "connect":
        return f"Connect to '{params.get('ssid', '').strip()}'"
    labels = {
        "toggle": "Toggle Wi-Fi",
        "on": "Turn Wi-Fi On",
        "off": "Turn Wi-Fi Off",
    }
    return labels.get(mode, "Toggle Wi-Fi")


def run(params: dict, context: str = "") -> bool:
    mode = params.get("mode", "toggle")
    if mode == "on":
        subprocess.run(["nmcli", "radio", "wifi", "on"], check=False)
    elif mode == "off":
        subprocess.run(["nmcli", "radio", "wifi", "off"], check=False)
    elif mode == "toggle":
        out = subprocess.check_output(["nmcli", "radio", "wifi"], text=True).strip()
        next_state = "off" if out == "enabled" else "on"
        subprocess.run(["nmcli", "radio", "wifi", next_state], check=False)
    elif mode == "connect":
        ssid = params.get("ssid", "").strip()
        if ssid:
            subprocess.run(["nmcli", "device", "wifi", "connect", ssid], check=False)
    return True