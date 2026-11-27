MODE = "trigger"
CATEGORY = "schedule"
TYPE = "time"
LABEL = "Scheduled Time"
DESCRIPTION = "Automatically trigger this flow at a specific time on selected days."

SCHEMA = [
    {"key": "schedule", "type": "schedule_picker", "title": "Schedule"},
]

def format_subtitle(params: dict) -> str:
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    days = params.get("days", [0, 1, 2, 3, 4])
    t = params.get("time", "07:00")
    if days == [0, 1, 2, 3, 4]:
        dl = "Weekdays"
    elif days == [5, 6]:
        dl = "Weekends"
    elif len(days) == 7:
        dl = "Every day"
    else:
        dl = ", ".join(day_names[i] for i in days if 0 <= i < 7)
    return f"{dl} at {t}"