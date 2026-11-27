MODE = "action"
CATEGORY = "time"
TYPE = "delay"
LABEL = "Wait"
DESCRIPTION = "Pause execution before running the next action in the chain."

SCHEMA = [
    {"key": "seconds", "type": "float", "title": "Seconds to Wait", "min": 0.5, "max": 300.0, "step": 0.5, "default": 2.0},
]

def format_subtitle(params: dict) -> str:
    return f"{float(params.get('seconds', 2.0)):.1f} seconds"