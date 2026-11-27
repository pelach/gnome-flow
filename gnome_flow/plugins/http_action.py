import os
import urllib.parse
import urllib.request
from pathlib import Path

MODE = "action"
CATEGORY = "web"
CATEGORY_TITLE = "Network & Connectivity"
CATEGORY_ICON = "network-wireless-symbolic"
TYPE = "http_request"
LABEL = "HTTP / Webhook / Download"
DESCRIPTION = "Send a GET/POST request or download a file to a folder (passes response or saved file path as {context})."

SCHEMA = [
    {
        "key": "method",
        "type": "choice",
        "title": "HTTP Method",
        "options": [
            ("GET", "GET"),
            ("POST", "POST"),
        ],
        "default": "GET",
    },
    {
        "key": "url",
        "type": "entry",
        "title": "Target URL (supports {context})",
        "default": "https://",
    },
    {
        "key": "save_folder",
        "type": "entry",
        "title": "Download to Folder (optional, e.g. ~/Podcasts — empty = return text)",
        "default": "",
    },
    {
        "key": "body",
        "type": "entry",
        "title": "JSON / Text Body for POST (optional)",
        "default": "",
    },
    {
        "key": "pass_response",
        "type": "bool",
        "title": "Pass Response / File Path as {context}",
        "default": True,
    },
]


def format_subtitle(params: dict) -> str:
    method = params.get("method", "GET")
    url = params.get("url", "").strip() or "(no URL)"
    folder = params.get("save_folder", "").strip()
    if folder:
        return f"Download {url} → {folder}"
    return f"{method} {url}"


def _filename_from_response(url: str, resp) -> str:
    cd = resp.headers.get("Content-Disposition", "")
    if "filename=" in cd:
        fname = cd.split("filename=")[-1].strip().strip('"').strip("'")
        if fname:
            return os.path.basename(fname)
    path = urllib.parse.urlparse(resp.geturl() or url).path
    name = os.path.basename(urllib.parse.unquote(path))
    return name or "downloaded_file"


def run(params: dict, context: str = "") -> dict | bool:
    method = params.get("method", "GET").upper()
    url = params.get("url", "").strip()
    save_folder = params.get("save_folder", "").strip()
    body = params.get("body", "")
    pass_resp = bool(params.get("pass_response", True))

    if not url or url == "https://":
        return False

    try:
        data = body.encode("utf-8") if (method == "POST" and body) else None
        headers = {"User-Agent": "GNOME-Flow/1.0"}
        if data and body.lstrip().startswith(("{", "[")):
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            if save_folder:
                dest_dir = Path(os.path.expanduser(save_folder))
                dest_dir.mkdir(parents=True, exist_ok=True)
                fname = _filename_from_response(url, resp)
                target = dest_dir / fname

                # Ütközés esetén sorszámozás (ep42_1.mp3)
                if target.exists():
                    stem, suffix = target.stem, target.suffix
                    idx = 1
                    while (dest_dir / f"{stem}_{idx}{suffix}").exists():
                        idx += 1
                    target = dest_dir / f"{stem}_{idx}{suffix}"

                with open(target, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)

                saved_path = str(target)
                return {"context": saved_path} if pass_resp else True

            resp_text = resp.read().decode("utf-8", errors="replace").strip()
            return {"context": resp_text} if pass_resp else True

    except Exception as e:
        print(f"[GNOME Flow] HTTP request/download failed: {e}")
        return False