import shutil
import subprocess
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

MODE = "action"
CATEGORY = "clipboard"
CATEGORY_TITLE = "Clipboard"
CATEGORY_ICON = "edit-paste-symbolic"
TYPE = "clipboard_action"
LABEL = "Clipboard Action"
DESCRIPTION = "Clear clipboard or strip tracking parameters (utm_*, fbclid, etc.) from copied URLs."

SCHEMA = [
    {
        "key": "mode",
        "type": "choice",
        "title": "Action",
        "options": [
            ("clean_url", "Strip Tracking Params from URL"),
            ("clear", "Clear Clipboard"),
        ],
        "default": "clean_url",
    }
]

TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "ref", "si")


def format_subtitle(params: dict) -> str:
    return "Clean URL tracking params" if params.get("mode", "clean_url") == "clean_url" else "Clear clipboard"


def _strip_tracking(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return url
    clean_query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if not any(k.lower().startswith(p) for p in TRACKING_PREFIXES)
    ]
    return urlunparse(parsed._replace(query=urlencode(clean_query)))


def run(params: dict, context: str = "") -> bool:
    if not shutil.which("wl-copy"):
        return False

    mode = params.get("mode", "clean_url")
    if mode == "clear":
        subprocess.run(["wl-copy", "--clear"], check=False)
        return True

    if mode == "clean_url":
        raw = context
        if not raw and shutil.which("wl-paste"):
            res = subprocess.run(["wl-paste", "--no-newline"], capture_output=True, text=True, check=False)
            raw = res.stdout
        cleaned = _strip_tracking(raw)
        if cleaned and cleaned != raw:
            subprocess.run(["wl-copy"], input=cleaned, text=True, check=False)
        return True

    return False