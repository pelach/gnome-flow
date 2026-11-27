import json
import subprocess
import sys

MODE = "action"
CATEGORY = "prompt"
TYPE = "ask_input"
LABEL = "Ask for Input / Menu"
DESCRIPTION = "Show a native Libadwaita dialog for text input or option selection and pass the result as {context}."

SCHEMA = [
    {
        "key": "mode",
        "type": "choice",
        "title": "Prompt Mode",
        "options": [
            ("text", "Text Input Box"),
            ("menu", "Choose from Options List"),
        ],
        "default": "text",
    },
    {
        "key": "title",
        "type": "entry",
        "title": "Dialog Title / Question",
        "default": "Enter value:",
    },
    {
        "key": "default_or_options",
        "type": "entry",
        "title": "Default Text (or semicolon-separated options: Opt 1;Opt 2;Opt 3)",
        "default": "{context}",
    },
]

_DIALOG_RUNNER = r"""
import json, sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

cfg = json.loads(sys.argv[1])
result = {"cancelled": True, "value": ""}

class PromptApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.gnome.Flow.Prompt")

    def do_activate(self):
        win = Adw.Window(application=self, title=cfg.get("title") or "GNOME Flow")
        win.set_default_size(420, -1)
        win.set_resizable(False)

        tv = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_end_title_buttons(False)
        hb.set_show_start_title_buttons(False)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.quit())
        hb.pack_start(cancel_btn)

        ok_btn = Gtk.Button(label="Continue")
        ok_btn.add_css_class("suggested-action")
        hb.pack_end(ok_btn)
        tv.add_top_bar(hb)

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()

        mode = cfg.get("mode", "text")
        raw = cfg.get("default_or_options", "")

        if mode == "menu":
            opts = [o.strip() for o in raw.split(";") if o.strip()] or ["Option 1"]
            combo = Adw.ComboRow(title="Select Option")
            combo.set_model(Gtk.StringList.new(opts))
            group.add(combo)

            def submit(_=None):
                result["cancelled"] = False
                result["value"] = opts[combo.get_selected()]
                self.quit()
        else:
            entry = Adw.EntryRow(title="Value")
            entry.set_text(raw)
            group.add(entry)

            def submit(_=None):
                result["cancelled"] = False
                result["value"] = entry.get_text()
                self.quit()

            entry.connect("entry-activated", submit)

        ok_btn.connect("clicked", submit)

        key_ctrl = Gtk.EventControllerKey()
        def on_key(_c, keyval, _kc, _st):
            if keyval == Gdk.KEY_Escape:
                self.quit()
                return True
            return False
        key_ctrl.connect("key-pressed", on_key)
        win.add_controller(key_ctrl)

        page.add(group)
        tv.set_content(page)
        win.set_content(tv)
        win.present()

app = PromptApp()
app.run(None)
print(json.dumps(result))
"""


def format_subtitle(params: dict) -> str:
    mode = params.get("mode", "text")
    title = params.get("title", "Enter value:").strip()
    prefix = "Menu" if mode == "menu" else "Input"
    return f"{prefix}: '{title}'"


def run(params: dict, context: str = "") -> dict | bool:
    payload = json.dumps({
        "mode": params.get("mode", "text"),
        "title": params.get("title", "Enter value:"),
        "default_or_options": params.get("default_or_options", ""),
    })

    try:
        proc = subprocess.run(
            [sys.executable, "-c", _DIALOG_RUNNER, payload],
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = proc.stdout.strip().splitlines()
        if not out:
            return {"abort": True}
        data = json.loads(out[-1])
        if data.get("cancelled"):
            return {"abort": True}
        return {"context": data.get("value", "")}
    except Exception as e:
        print(f"[GNOME Flow] Prompt dialog error: {e}")
        return {"abort": True}