import os
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

from ..model import Block, load_flows
from ..plugins import get_plugins_by_mode

CATEGORY_META = {
    "keyboard": ("Keyboard Shortcut", "input-keyboard-symbolic"),
    "schedule": ("Schedule & Time", "alarm-symbolic"),
    "dbus": ("Hardware & D-Bus", "drive-removable-media-symbolic"),
    "file": ("Files & Folders", "folder-open-symbolic"),
    "flow": ("Other Flows", "media-playlist-repeat-symbolic"),
    "app": ("Applications", "application-x-executable-symbolic"),
    "system": ("System & Notify", "preferences-system-symbolic"),
    "time": ("Wait / Delay", "alarm-symbolic"),
    "network": ("Network & Connectivity", "network-wireless-symbolic"),
    "display": ("Display & Appearance", "preferences-desktop-display-symbolic"),
    "audio": ("Audio & Media", "audio-speakers-symbolic"),
    "text": ("Text & Data", "insert-text-symbolic"),
    "clipboard": ("Clipboard", "edit-paste-symbolic"),
    "idle": ("User Idle", "preferences-desktop-screensaver-symbolic"),
    "power": ("Power", "battery-symbolic"),
    "web": ("Web & HTTP", "web-browser-symbolic"),
    "prompt": ("Interaction & Prompts", "dialog-question-symbolic"),
}


def _get_installed_process_options() -> list[tuple[str, str]]:
    seen: set[str] = set()
    items: list[tuple[str, str]] = [("", "— Custom Process Name Below —")]
    apps = [a for a in Gio.AppInfo.get_all() if a.should_show()]
    apps.sort(key=lambda a: (a.get_name() or "").lower())

    for app in apps:
        exe = app.get_executable()
        if not exe:
            continue
        proc_name = os.path.basename(exe).strip()
        if not proc_name or proc_name in ("env", "sh", "bash", "python3", "flatpak"):
            continue
        if proc_name.lower() in seen:
            continue
        seen.add(proc_name.lower())
        title = app.get_name() or proc_name
        items.append((proc_name, f"{title} ({proc_name})"))
    return items


class BlockPickerDialog(Adw.Window):
    """Kétpaneles választóablak: bal oldalon kategóriák, jobb oldalon a plugin űrlapok."""

    def __init__(self, mode: str, on_selected, edit_block: Block | None = None):
        super().__init__()
        self.mode = mode
        self.on_selected = on_selected
        self.edit_block = edit_block
        self._category_pages: dict[str, Gtk.Widget] = {}

        titles = (
            {"trigger": "Edit Trigger", "action": "Edit Action", "condition": "Edit Condition"}
            if edit_block
            else {"trigger": "Add Trigger (When)", "action": "Add Action (Then)", "condition": "Add Condition (Valid When)"}
        )
        self.set_title(titles.get(mode, "Configure Block"))
        self.set_default_size(760, 560)
        self.set_modal(True)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(Adw.HeaderBar())

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        split.set_position(220)
        split.set_shrink_start_child(False)
        split.set_shrink_end_child(False)

        self.cat_list = Gtk.ListBox()
        self.cat_list.add_css_class("navigation-sidebar")
        self.cat_list.connect("row-selected", self._on_category_selected)

        left_scroll = Gtk.ScrolledWindow(vexpand=True)
        left_scroll.set_child(self.cat_list)
        split.set_start_child(left_scroll)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        right_scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        right_scroll.set_child(self.stack)
        split.set_end_child(right_scroll)

        toolbar_view.set_content(split)
        self.set_content(toolbar_view)

        self._populate_categories()

    def _add_category(self, key: str, title: str, icon_name: str, widget: Gtk.Widget):
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=10, margin_bottom=10, margin_start=12, margin_end=12)
        box.append(Gtk.Image.new_from_icon_name(icon_name))
        box.append(Gtk.Label(label=title, xalign=0))
        row.set_child(box)
        row.cat_key = key

        self.cat_list.append(row)
        self.stack.add_named(widget, key)
        self._category_pages[key] = widget

    def _on_category_selected(self, _listbox, row):
        if row:
            self.stack.set_visible_child_name(row.cat_key)

    def _populate_categories(self):
        # 1. Speciális dinamikus listák (telepített appok és mentett flow-k)
        if self.mode == "trigger":
            self._add_category("flow", *CATEGORY_META["flow"], self._build_flow_trigger())
        elif self.mode == "action":
            self._add_category("app", *CATEGORY_META["app"], self._build_app_action())
            self._add_category("flow", *CATEGORY_META["flow"], self._build_flow_action())
        elif self.mode == "condition":
            self._add_category("flow", *CATEGORY_META["flow"], self._build_flow_condition())

        # 2. Összes plugin automatikus betöltése SCHEMA alapján
        for plugin in get_plugins_by_mode(self.mode):
            self._mount_plugin(plugin)

        # Szerkesztésnél a meglévő kategória kiválasztása
        target_row = None
        if self.edit_block:
            idx = 0
            while (r := self.cat_list.get_row_at_index(idx)) is not None:
                if r.cat_key == self.edit_block.category:
                    target_row = r
                    break
                idx += 1

        if not target_row:
            target_row = self.cat_list.get_row_at_index(0)
        if target_row:
            self.cat_list.select_row(target_row)

    def _mount_plugin(self, plugin):
        block_type = getattr(plugin, "TYPE")
        label = getattr(plugin, "LABEL", block_type)
        desc = getattr(plugin, "DESCRIPTION", "")
        schema = getattr(plugin, "SCHEMA", [])

        cat_key = getattr(plugin, "CATEGORY", block_type)
        default_title, default_icon = CATEGORY_META.get(
            cat_key,
            (getattr(plugin, "CATEGORY_TITLE", label), getattr(plugin, "CATEGORY_ICON", "preferences-system-symbolic")),
        )

        ep = self._edit_params(block_type)
        group = Adw.PreferencesGroup(
            title=GLib.markup_escape_text(label, -1),
            description=GLib.markup_escape_text(desc, -1),
        )

        readers = {}
        for field in schema:
            key = field["key"]
            ftype = field.get("type", "entry")
            ftitle = GLib.markup_escape_text(field.get("title", key), -1)
            default_val = field.get("default")
            current_val = ep.get(key, default_val) if ep else default_val

            if ftype == "entry":
                row = Adw.EntryRow(title=ftitle)
                row.set_text(str(current_val or ""))
                group.add(row)
                readers[key] = lambda r=row: r.get_text().strip()

            elif ftype == "int":
                row = Adw.SpinRow.new_with_range(float(field.get("min", 0)), float(field.get("max", 999999)), float(field.get("step", 1)))
                row.set_title(ftitle)
                row.set_value(float(current_val if current_val is not None else 0))
                group.add(row)
                readers[key] = lambda r=row: int(r.get_value())

            elif ftype == "float":
                row = Adw.SpinRow.new_with_range(float(field.get("min", 0.0)), float(field.get("max", 999999.0)), float(field.get("step", 0.5)))
                row.set_title(ftitle)
                row.set_value(float(current_val if current_val is not None else 0.0))
                group.add(row)
                readers[key] = lambda r=row: float(r.get_value())

            elif ftype == "bool":
                row = Adw.SwitchRow(title=ftitle, active=bool(current_val))
                group.add(row)
                readers[key] = lambda r=row: bool(r.get_active())

            elif ftype == "choice":
                options = list(field.get("options", []))
                if current_val and current_val not in [o[0] for o in options]:
                    options.append((current_val, f"{current_val} (offline)"))
                opt_keys = [o[0] for o in options]
                opt_labels = [o[1] for o in options]
                row = Adw.ComboRow(title=ftitle)
                row.set_model(Gtk.StringList.new(opt_labels))
                if current_val in opt_keys:
                    row.set_selected(opt_keys.index(current_val))
                group.add(row)
                readers[key] = lambda r=row, keys=opt_keys: keys[r.get_selected()] if keys else ""

            elif ftype == "app_picker":
                app_opts = _get_installed_process_options()
                opt_keys, opt_labels = [o[0] for o in app_opts], [o[1] for o in app_opts]
                combo = Adw.ComboRow(title="Choose Installed Application")
                combo.set_model(Gtk.StringList.new(opt_labels))
                group.add(combo)

                entry = Adw.EntryRow(title=ftitle)
                entry.set_text(str(current_val or ""))
                if current_val and str(current_val) in opt_keys:
                    combo.set_selected(opt_keys.index(str(current_val)))
                group.add(entry)
                combo.connect("notify::selected", lambda c, _ps, e=entry, keys=opt_keys: e.set_text(keys[c.get_selected()]) if keys[c.get_selected()] else None)
                readers[key] = lambda r=entry: r.get_text().strip()

            elif ftype == "path_picker":
                entry = Adw.EntryRow(title=ftitle)
                entry.set_text(str(current_val or ""))
                group.add(entry)

                browse_row = Adw.ActionRow(title="Browse from Disk...")
                btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
                allow_file = field.get("allow_file", True)
                allow_folder = field.get("allow_folder", True)

                if allow_file:
                    fbtn = Gtk.Button(label="Select File...")
                    fbtn.connect("clicked", lambda _, e=entry: Gtk.FileDialog(title="Select File").open(self, None, lambda d, res: self._apply_picked_path(d, res, e, False)))
                    btn_box.append(fbtn)
                if allow_folder:
                    dbtn = Gtk.Button(label="Select Folder...")
                    dbtn.connect("clicked", lambda _, e=entry: Gtk.FileDialog(title="Select Folder").select_folder(self, None, lambda d, res: self._apply_picked_path(d, res, e, True)))
                    btn_box.append(dbtn)

                browse_row.add_suffix(btn_box)
                group.add(browse_row)
                readers[key] = lambda r=entry: r.get_text().strip()

            elif ftype == "shortcut_capture":
                ctrl_r = Adw.SwitchRow(title="Control (Ctrl)", active="<Control>" in str(current_val or ""))
                alt_r = Adw.SwitchRow(title="Alt", active="<Alt>" in str(current_val or ""))
                sup_r = Adw.SwitchRow(title="Super (Windows / Meta)", active="<Super>" in str(current_val or ""))
                shf_r = Adw.SwitchRow(title="Shift", active="<Shift>" in str(current_val or ""))
                for r in (ctrl_r, alt_r, sup_r, shf_r):
                    group.add(r)

                key_e = Adw.EntryRow(title="Key Name (e.g. F1, F12, k, Return)")
                key_e.set_text((str(current_val or "F1").split(">")[-1]) or "F1")
                group.add(key_e)

                cap_btn = Gtk.Button(label="Press Key to Capture...", margin_top=8)
                kctrl = Gtk.EventControllerKey()
                def _on_cap(_c, kval, _kc, st, ke=key_e, cr=ctrl_r, ar=alt_r, sr=sup_r, shr=shf_r, btn=cap_btn):
                    kname = Gdk.keyval_name(kval)
                    if kname and kname not in ("Control_L", "Control_R", "Alt_L", "Alt_R", "Super_L", "Super_R", "Shift_L", "Shift_R"):
                        ke.set_text(kname)
                        cr.set_active(bool(st & Gdk.ModifierType.CONTROL_MASK))
                        ar.set_active(bool(st & Gdk.ModifierType.ALT_MASK))
                        sr.set_active(bool(st & Gdk.ModifierType.SUPER_MASK))
                        shr.set_active(bool(st & Gdk.ModifierType.SHIFT_MASK))
                        btn.set_label(f"Captured: {kname}")
                    return True
                kctrl.connect("key-pressed", _on_cap)
                cap_btn.add_controller(kctrl)
                group.add(cap_btn)

                def _read_accel(cr=ctrl_r, ar=alt_r, sr=sup_r, shr=shf_r, ke=key_e):
                    mods = ("<Control>" if cr.get_active() else "") + ("<Alt>" if ar.get_active() else "") + ("<Super>" if sr.get_active() else "") + ("<Shift>" if shr.get_active() else "")
                    return f"{mods}{ke.get_text().strip() or 'F1'}"
                readers[key] = _read_accel

            elif ftype == "schedule_picker":
                init_time = ep.get("time", "07:00") if ep else "07:00"
                init_days = ep.get("days", [0, 1, 2, 3, 4]) if ep else [0, 1, 2, 3, 4]
                try:
                    ih, im = map(int, init_time.split(":"))
                except ValueError:
                    ih, im = 7, 0

                trow = Adw.ActionRow(title="Trigger Time")
                tbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
                hspin = Gtk.SpinButton.new_with_range(0, 23, 1)
                hspin.set_wrap(True)
                hspin.set_value(ih)
                hspin.set_width_chars(2)
                hspin.connect("output", lambda s: (s.set_text(f"{int(s.get_value()):02d}"), True)[1])

                mspin = Gtk.SpinButton.new_with_range(0, 59, 1)
                mspin.set_wrap(True)
                mspin.set_value(im)
                mspin.set_width_chars(2)
                mspin.connect("output", lambda s: (s.set_text(f"{int(s.get_value()):02d}"), True)[1])

                tbox.append(hspin)
                tbox.append(Gtk.Label(label=":"))
                tbox.append(mspin)
                trow.add_suffix(tbox)
                group.add(trow)

                drow = Adw.ActionRow(title="Repeat Days")
                dbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0, valign=Gtk.Align.CENTER)
                dbox.add_css_class("linked")
                day_btns = []
                for idx, dname in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                    b = Gtk.ToggleButton(label=dname, active=(idx in init_days))
                    dbox.append(b)
                    day_btns.append((idx, b))
                drow.add_suffix(dbox)
                group.add(drow)

                readers["time"] = lambda hs=hspin, ms=mspin: f"{int(hs.get_value()):02d}:{int(ms.get_value()):02d}"
                readers["days"] = lambda btns=day_btns: [i for i, b in btns if b.get_active()] or [0]

            elif ftype == "folder_watch":
                default_dir = (ep.get("path") if (ep and ep.get("path")) else str(Gio.File.new_for_path("~").get_path()))
                saved_ev = ep.get("events", ["added"]) if ep else ["added"]

                frow = Adw.ActionRow(title=Gio.File.new_for_path(default_dir).get_basename() or default_dir, subtitle=default_dir)
                frow._selected_path = default_dir
                cbtn = Gtk.Button(label="Change Folder...", valign=Gtk.Align.CENTER)
                cbtn.connect("clicked", lambda _, r=frow: Gtk.FileDialog(title="Select Folder to Watch").select_folder(self, None, lambda d, res: self._on_folder_chosen(d, res, r)))
                frow.add_suffix(cbtn)
                group.add(frow)

                chks = {}
                for ev_key, ev_title in [("added", "When Item Added"), ("modified", "When Item Modified"), ("removed", "When Item Removed")]:
                    sr = Adw.SwitchRow(title=ev_title, active=(ev_key in saved_ev))
                    group.add(sr)
                    chks[ev_key] = sr

                readers["path"] = lambda r=frow: r._selected_path
                readers["events"] = lambda c=chks: [k for k, sw in c.items() if sw.get_active()] or ["added"]

        add_btn = Gtk.Button(label="Save Changes" if ep else f"Add {label}", margin_top=12)
        add_btn.add_css_class("suggested-action")

        def on_submit(_):
            params = {k: fn() for k, fn in readers.items()}
            subtitle = str(plugin.format_subtitle(params)) if hasattr(plugin, "format_subtitle") else ", ".join(f"{k}={v}" for k, v in params.items())
            self._finish(Block(category=cat_key, type=block_type, label=label, subtitle=subtitle, params=params))

        add_btn.connect("clicked", on_submit)
        group.add(add_btn)

        target_widget = self._category_pages.get(cat_key)
        if isinstance(target_widget, Adw.PreferencesPage):
            target_widget.add(group)
        else:
            page = Adw.PreferencesPage()
            page.add(group)
            self._add_category(cat_key, default_title, default_icon, page)

    def _apply_picked_path(self, dialog, result, entry: Adw.EntryRow, is_folder: bool):
        try:
            gfile = dialog.select_folder_finish(result) if is_folder else dialog.open_finish(result)
            if gfile and gfile.get_path():
                entry.set_text(gfile.get_path())
        except Exception:
            pass

    def _on_folder_chosen(self, dialog, result, folder_row):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                folder_row._selected_path = path
                folder_row.set_title(folder.get_basename() or path)
                folder_row.set_subtitle(path)
        except Exception:
            pass

    def _edit_params(self, block_type: str) -> dict | None:
        return self.edit_block.params if (self.edit_block and self.edit_block.type == block_type) else None

    def _finish(self, block: Block):
        self.on_selected(block)
        self.close()

    def _wrap_page(self, title: str, subtitle: str = "") -> tuple[Adw.PreferencesPage, Adw.PreferencesGroup]:
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=title, description=subtitle)
        page.add(group)
        return page, group

    # --- SPECIÁLIS LISTÁZÓ PANELEK ---

    def _build_flow_trigger(self) -> Gtk.Widget:
        page, group = self._wrap_page("Chained Flow Trigger", "Run this flow immediately after another flow finishes.")
        flows = load_flows()
        if not flows:
            group.add(Adw.ActionRow(title="No other flows available yet"))
            return page
        for f in flows:
            row = Adw.ActionRow(title=f.name, subtitle=f"CLI: flow {f.slug}")
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda _, target=f: self._finish(Block(category="flow", type="flow_finished", label="After Flow Finishes", subtitle=target.name, params={"flow_id": target.id})))
            group.add(row)
        return page

    def _build_app_action(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12, margin_bottom=12, margin_start=16, margin_end=16)
        search = Gtk.SearchEntry(placeholder_text="Search installed applications...")
        box.append(search)

        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")
        ep = self._edit_params("open_app")
        selected_id = ep.get("desktop_id") if ep else None

        apps = sorted([a for a in Gio.AppInfo.get_all() if a.should_show()], key=lambda a: (a.get_name() or "").lower())
        for app in apps:
            row = Adw.ActionRow(title=app.get_name() or "Unknown", subtitle=app.get_id() or "")
            if gicon := app.get_icon():
                img = Gtk.Image.new_from_gicon(gicon)
                img.set_pixel_size(24)
                row.add_prefix(img)
            if selected_id and app.get_id() == selected_id:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            row.set_activatable(True)
            row.connect("activated", lambda _, a=app: self._finish(Block(category="app", type="open_app", label=f"Open {a.get_name()}", subtitle=a.get_id() or "", params={"desktop_id": a.get_id()})))
            listbox.append(row)

        listbox.set_filter_func(lambda r: (q := search.get_text().strip().lower()) == "" or q in r.get_title().lower() or q in (r.get_subtitle() or "").lower())
        search.connect("search-changed", lambda _: listbox.invalidate_filter())

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(listbox)
        box.append(scroll)
        return box

    def _build_flow_action(self) -> Gtk.Widget:
        page, group = self._wrap_page("Control Another Flow", "Enable, disable, toggle, or execute another saved flow (optionally filtered by {context}).")
        ep = self._edit_params("toggle_flow")
        mode_row = Adw.ComboRow(title="Operation")
        mode_row.set_model(Gtk.StringList.new(["Run Flow Now", "Enable Flow", "Disable Flow", "Toggle Flow"]))
        mode_keys, mode_labels = ["run", "enable", "disable", "toggle"], ["Run", "Enable", "Disable", "Toggle"]
        if ep and ep.get("state") in mode_keys:
            mode_row.set_selected(mode_keys.index(ep["state"]))
        group.add(mode_row)

        cond_entry = Adw.EntryRow(title="Only If {context} Equals (optional, e.g. Munka)")
        if ep:
            cond_entry.set_text(ep.get("match_context", ""))
        group.add(cond_entry)

        def _sub(name: str, m: str) -> str:
            return f"{name} (if {{context}} == '{m}')" if m else name

        dyn_row = Adw.ActionRow(title="Flow Matching {context} Name", subtitle="Runs the flow whose name or slug matches {context}")
        dyn_row.set_activatable(True)
        dyn_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        dyn_row.connect("activated", lambda _: self._finish(Block(
            category="flow", type="toggle_flow", label=f"{mode_labels[mode_row.get_selected()]} Flow ({{context}})",
            subtitle=_sub("{context}", cond_entry.get_text().strip()),
            params={"flow_id": "{context}", "state": mode_keys[mode_row.get_selected()], "match_context": cond_entry.get_text().strip()},
        )))
        group.add(dyn_row)

        for f in load_flows():
            row = Adw.ActionRow(title=f.name, subtitle=f"CLI: flow {f.slug}")
            if ep and ep.get("flow_id") == f.id:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda _, target=f: self._finish(Block(
                category="flow", type="toggle_flow", label=f"{mode_labels[mode_row.get_selected()]} Flow",
                subtitle=_sub(target.name, cond_entry.get_text().strip()),
                params={"flow_id": target.id, "state": mode_keys[mode_row.get_selected()], "match_context": cond_entry.get_text().strip()},
            )))
            group.add(row)
        return page

    def _build_flow_condition(self) -> Gtk.Widget:
        page, group = self._wrap_page("Another Flow State", "Valid only while the selected flow is enabled.")
        ep = self._edit_params("flow_enabled")
        for f in load_flows():
            row = Adw.ActionRow(title=f.name)
            if ep and ep.get("flow_id") == f.id:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda _, target=f: self._finish(Block(category="flow", type="flow_enabled", label="Flow is Enabled", subtitle=target.name, params={"flow_id": target.id})))
            group.add(row)
        return page