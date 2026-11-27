import subprocess

MODE = "action"
CATEGORY = "system"
TYPE = "set_power_profile"
LABEL = "Power Profile"
DESCRIPTION = "Switch or toggle GNOME power profile (Power Saver, Balanced, Performance)."

SCHEMA = [
    {
        "key": "profile",
        "type": "choice",
        "title": "Power Profile",
        "options": [
            ("toggle_saver", "Toggle Power Saver / Balanced"),
            ("power-saver", "Power Saver"),
            ("balanced", "Balanced"),
            ("performance", "Performance"),
        ],
        "default": "toggle_saver",
    },
]


def format_subtitle(params: dict) -> str:
    prof = params.get("profile", "toggle_saver")
    labels = {
        "toggle_saver": "Toggle Power Saver",
        "power-saver": "Set Power Saver",
        "balanced": "Set Balanced",
        "performance": "Set Performance",
    }
    return labels.get(prof, prof)


def run(params: dict, context: str = "") -> bool:
    prof = params.get("profile", "toggle_saver")
    if prof == "toggle_saver":
        try:
            cur = subprocess.check_output(["powerprofilesctl", "get"], text=True).strip()
            target = "balanced" if cur == "power-saver" else "power-saver"
        except Exception:
            target = "power-saver"
    else:
        target = prof

    subprocess.run(["powerprofilesctl", "set", target], check=False)
    return True