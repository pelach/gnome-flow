import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Gdk, GLib

from ..model import Block, load_flows
from ..plugins import get_plugins_by_mode


class BlockPickerDialog(Adw.Window):
    """Kétpaneles választóablak: bal oldalon kategóriák, jobb oldalon a konkrét beállítások."""

    def __init__(self, mode: str, on_selected, edit_block: Block | None = None):
        """
        mode: 'trigger' (HA), 'action' (AKKOR), vagy 'condition' (Érvényességi kör feltétel)
        on_selected: callback függvény, ami megkapja az elkészült Block objektumot
        edit_block: ha meg van adva, előtölti a meglévő blokk adatait szerkesztéshez
        """
        super().__init__()
        self.mode = mode
        self.on_selected = on_selected
        self.edit_block = edit_block
        self._category_pages: dict[str, Gtk.Widget] = {}

        if edit_block:
            titles = {
                "trigger": "Edit Trigger",
                "action": "Edit Action",
                "condition": "Edit Condition",
            }
        else:
            titles = {
                "trigger": "Add Trigger (When)",
                "action": "Add Action (Then)",
                "condition": "Add Condition (Valid When)",
            }
        self.set_title(titles.get(mode, "Configure Block"))
        self.set_default_size(760, 560)
        self.set_modal(True)

        # Fő elrendezés: fejléc + kétoszlopos osztott nézet
        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        split.set_position(210)
        split.set_shrink_start_child(False)
        split.set_shrink_end_child(False)

        # Bal oldali kategórialista
        self.cat_list = Gtk.ListBox()
        self.cat_list.add_css_class("navigation-sidebar")
        self.cat_list.connect("row-selected", self._on_category_selected)

        left_scroll = Gtk.ScrolledWindow(vexpand=True)
        left_scroll.set_child(self.cat_list)
        split.set_start_child(left_scroll)

        # Jobb oldali tartalomváltó (Stack)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        right_scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        right_scroll.set_child(self.stack)
        split.set_end_child(right_scroll)

        toolbar_view.set_content(split)
        self.set_content(toolbar_view)

        self._populate_categories()

    def _add_category(self, key: str, title: str, icon_name: str, widget: Gtk.Widget):
        """Hozzáad egy kategóriát a bal sávhoz és a hozzá tartozó oldalt a jobb oldalra."""
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_start(12)
        box.set_margin_end(12)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        lbl = Gtk.Label(label=title, xalign=0)
        box.append(icon)
        box.append(lbl)
        row.set_child(box)
        row.cat_key = key

        self.cat_list.append(row)
        self.stack.add_named(widget, key)
        self._category_pages[key] = widget

    def _on_category_selected(self, listbox, row):
        if row:
            self.stack.set_visible_child_name(row.cat_key)

    def _populate_categories(self):
        """Módtól ('trigger', 'action', 'condition') függően építi fel a kategóriákat."""
        if self.mode == "trigger":
            self._add_category("keyboard", "Keyboard Shortcut", "input-keyboard-symbolic", self._build_keyboard_trigger())
            self._add_category("schedule", "Schedule & Time", "alarm-symbolic", self._build_schedule_trigger())
            self._add_category("dbus", "Hardware & D-Bus", "drive-removable-media-symbolic", self._build_dbus_trigger())
            self._add_category("file", "Files & Folders", "folder-symbolic", self._build_file_trigger())
            self._add_category("flow", "Other Flows", "media-playlist-repeat-symbolic", self._build_flow_trigger())

        elif self.mode == "action":
            self._add_category("app", "Applications", "application-x-executable-symbolic", self._build_app_action())
            self._add_category("file", "Files & Folders", "folder-open-symbolic", self._build_file_action())
            self._add_category("system", "System & Notify", "preferences-system-symbolic", self._build_system_action())
            self._add_category("time", "Wait / Delay", "alarm-symbolic", self._build_delay_action())
            self._add_category("flow", "Other Flows", "media-playlist-repeat-symbolic", self._build_flow_action())

        elif self.mode == "condition":
            self._add_category("app", "Application State", "application-x-executable-symbolic", self._build_app_condition())
            self._add_category("file", "File / Folder Exists", "folder-symbolic", self._build_file_condition())
            self._add_category("system", "System State", "preferences-system-symbolic", self._build_system_condition())
            self._add_category("flow", "Flow State", "media-playlist-repeat-symbolic", self._build_flow_condition())

        # Dinamikus plug-inek regisztrálása a megfelelő kategóriába (vagy új kategóriába)
        for plugin in get_plugins_by_mode(self.mode):
            self._mount_plugin(plugin)

        # Szerkesztésnél a blokk saját kategóriáját jelöljük ki, különben az elsőt
        target_row = None
        if self.edit_block:
            idx = 0
            while True:
                r = self.cat_list.get_row_at_index(idx)
                if not r:
                    break
                if r.cat_key == self.edit_block.category:
                    target_row = r
                    break
                idx += 1

        if not target_row:
            target_row = self.cat_list.get_row_at_index(0)
        if target_row:
            self.cat_list.select_row(target_row)

    def _mount_plugin(self, plugin):
        """A plug-in SCHEMA leírásából automatikusan felépíti a Libadwaita űrlapot."""
        cat_key = getattr(plugin, "CATEGORY", "plugins")
        cat_title = getattr(plugin, "CATEGORY_TITLE", "Plugins")
        cat_icon = getattr(plugin, "CATEGORY_ICON", "application-x-addon-symbolic")

        block_type = getattr(plugin, "TYPE")
        label = getattr(plugin, "LABEL", block_type)
        desc = getattr(plugin, "DESCRIPTION", "")
        schema = getattr(plugin, "SCHEMA", [])

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
                row = Adw.SpinRow.new_with_range(
                    float(field.get("min", 0)),
                    float(field.get("max", 999999)),
                    float(field.get("step", 1)),
                )
                row.set_title(ftitle)
                row.set_value(float(current_val if current_val is not None else 0))
                group.add(row)
                readers[key] = lambda r=row: int(r.get_value())

            elif ftype == "float":
                row = Adw.SpinRow.new_with_range(
                    float(field.get("min", 0.0)),
                    float(field.get("max", 999999.0)),
                    float(field.get("step", 0.5)),
                )
                row.set_title(ftitle)
                row.set_value(float(current_val if current_val is not None else 0.0))
                group.add(row)
                readers[key] = lambda r=row: float(r.get_value())

            elif ftype == "bool":
                row = Adw.SwitchRow(title=ftitle, active=bool(current_val))
                group.add(row)
                readers[key] = lambda r=row: bool(r.get_active())

            elif ftype == "choice":
                options = field.get("options", [])  # [(val, label), ...]
                opt_keys = [o[0] for o in options]
                opt_labels = [o[1] for o in options]
                row = Adw.ComboRow(title=ftitle)
                row.set_model(Gtk.StringList.new(opt_labels))
                if current_val in opt_keys:
                    row.set_selected(opt_keys.index(current_val))
                group.add(row)
                readers[key] = lambda r=row, keys=opt_keys: keys[r.get_selected()] if keys else ""

        btn_text = "Save Changes" if ep else f"Add {label}"
        add_btn = Gtk.Button(label=btn_text, margin_top=12)
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")

        def on_submit(_):
            params = {k: fn() for k, fn in readers.items()}
            if hasattr(plugin, "format_subtitle"):
                subtitle = str(plugin.format_subtitle(params))
            else:
                subtitle = ", ".join(f"{k}={v}" for k, v in params.items())
            self._finish(Block(
                category=cat_key,
                type=block_type,
                label=label,
                subtitle=subtitle,
                params=params,
            ))

        add_btn.connect("clicked", on_submit)
        group.add(add_btn)

        # Ha a kategória már létezik (Adw.PreferencesPage), hozzáfűzzük új szekcióként
        target_widget = self._category_pages.get(cat_key)
        if isinstance(target_widget, Adw.PreferencesPage):
            target_widget.add(group)
        else:
            page = Adw.PreferencesPage()
            page.add(group)
            self._add_category(cat_key, cat_title, cat_icon, page)

    def _edit_params(self, block_type: str) -> dict | None:
        if self.edit_block and self.edit_block.type == block_type:
            return self.edit_block.params
        return None

    def _finish(self, block: Block):
        self.on_selected(block)
        self.close()

    def _wrap_page(self, title: str, subtitle: str = "") -> tuple[Adw.PreferencesPage, Adw.PreferencesGroup]:
        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup(title=title, description=subtitle)
        page.add(group)
        return page, group

    # --- TRIGGER PANELEK (HA ÁG) ---

    def _build_keyboard_trigger(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Global Keyboard Shortcut",
            "Select modifiers and press a key to trigger this flow anywhere on the desktop.",
        )

        ep = self._edit_params("shortcut")

        ctrl_row = Adw.SwitchRow(title="Control (Ctrl)")
        alt_row = Adw.SwitchRow(title="Alt")
        super_row = Adw.SwitchRow(title="Super (Windows / Meta)")
        shift_row = Adw.SwitchRow(title="Shift")
        group.add(ctrl_row)
        group.add(alt_row)
        group.add(super_row)
        group.add(shift_row)

        key_entry = Adw.EntryRow(title="Key Name (e.g. F1, F12, k, Return)")
        key_entry.set_text("F1")
        group.add(key_entry)

        if ep:
            accel = ep.get("accel", "F1")
            ctrl_row.set_active("<Control>" in accel)
            alt_row.set_active("<Alt>" in accel)
            super_row.set_active("<Super>" in accel)
            shift_row.set_active("<Shift>" in accel)
            key_entry.set_text(accel.split(">")[-1] or "F1")

        capture_btn = Gtk.Button(label="Press Key to Capture...", margin_top=12)
        capture_btn.add_css_class("pill")

        key_ctrl = Gtk.EventControllerKey()
        def on_key_pressed(ctrl, keyval, keycode, state):
            key_name = Gdk.keyval_name(keyval)
            if key_name and key_name not in ("Control_L", "Control_R", "Alt_L", "Alt_R", "Super_L", "Super_R", "Shift_L", "Shift_R"):
                key_entry.set_text(key_name)
                ctrl_row.set_active(bool(state & Gdk.ModifierType.CONTROL_MASK))
                alt_row.set_active(bool(state & Gdk.ModifierType.ALT_MASK))
                super_row.set_active(bool(state & Gdk.ModifierType.SUPER_MASK))
                shift_row.set_active(bool(state & Gdk.ModifierType.SHIFT_MASK))
                capture_btn.set_label(f"Captured: {key_name}")
            return True

        key_ctrl.connect("key-pressed", on_key_pressed)
        capture_btn.add_controller(key_ctrl)
        group.add(capture_btn)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Shortcut Trigger",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")

        def on_add(_):
            mods = ""
            human_mods = []
            if ctrl_row.get_active():
                mods += "<Control>"
                human_mods.append("Ctrl")
            if alt_row.get_active():
                mods += "<Alt>"
                human_mods.append("Alt")
            if super_row.get_active():
                mods += "<Super>"
                human_mods.append("Super")
            if shift_row.get_active():
                mods += "<Shift>"
                human_mods.append("Shift")

            raw_key = key_entry.get_text().strip() or "F1"
            accel = f"{mods}{raw_key}"
            human = "+".join(human_mods + [raw_key])
            self._finish(Block(
                category="keyboard",
                type="shortcut",
                label="Shortcut Pressed",
                subtitle=human,
                params={"accel": accel},
            ))

        add_btn.connect("clicked", on_add)
        group.add(add_btn)
        return page

    def _build_schedule_trigger(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Schedule &amp; Time",
            "Automatically trigger this flow at a specific time on selected days.",
        )

        ep = self._edit_params("time")
        init_h, init_m = 7, 0
        init_days = [0, 1, 2, 3, 4]
        if ep:
            try:
                init_h, init_m = map(int, ep.get("time", "07:00").split(":"))
            except ValueError:
                pass
            init_days = ep.get("days", [0, 1, 2, 3, 4])

        time_row = Adw.ActionRow(title="Trigger Time")
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)

        hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        hour_spin.set_wrap(True)
        hour_spin.set_value(init_h)
        hour_spin.set_width_chars(2)
        hour_spin.connect("output", lambda s: (s.set_text(f"{int(s.get_value()):02d}"), True)[1])

        colon = Gtk.Label(label=":")

        min_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
        min_spin.set_wrap(True)
        min_spin.set_value(init_m)
        min_spin.set_width_chars(2)
        min_spin.connect("output", lambda s: (s.set_text(f"{int(s.get_value()):02d}"), True)[1])

        time_box.append(hour_spin)
        time_box.append(colon)
        time_box.append(min_spin)
        time_row.add_suffix(time_box)
        group.add(time_row)

        days_row = Adw.ActionRow(title="Repeat Days")
        days_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0, valign=Gtk.Align.CENTER)
        days_box.add_css_class("linked")
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        day_buttons = []

        for idx, name in enumerate(day_names):
            btn = Gtk.ToggleButton(label=name, active=(idx in init_days))
            days_box.append(btn)
            day_buttons.append((idx, name, btn))

        days_row.add_suffix(days_box)
        group.add(days_row)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Schedule Trigger",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")

        def _on_add(_):
            h = int(hour_spin.get_value())
            m = int(min_spin.get_value())
            time_str = f"{h:02d}:{m:02d}"
            selected_days = [idx for idx, _, b in day_buttons if b.get_active()]
            if not selected_days:
                return

            if selected_days == [0, 1, 2, 3, 4]:
                days_label = "Weekdays"
            elif selected_days == [5, 6]:
                days_label = "Weekends"
            elif len(selected_days) == 7:
                days_label = "Every day"
            else:
                days_label = ", ".join(day_names[i] for i in selected_days)

            self._finish(Block(
                category="schedule",
                type="time",
                label="Scheduled Time",
                subtitle=f"{days_label} at {time_str}",
                params={"time": time_str, "days": selected_days},
            ))

        add_btn.connect("clicked", _on_add)
        group.add(add_btn)
        return page

    def _build_dbus_trigger(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Hardware &amp; D-Bus Events",
            "Triggered automatically by system D-Bus signals. Passes mount path as {context}.",
        )

        ep = self._edit_params("drive_mounted")
        filter_entry = Adw.EntryRow(title="Optional Path / Label Filter (leave empty for any)")
        if ep:
            filter_entry.set_text(ep.get("filter", ""))
        group.add(filter_entry)

        drive_row = Adw.ActionRow(
            title="Storage Drive Mounted (UDisks2)",
            subtitle="Fires when a USB drive, SD card, or external disk is mounted",
        )
        drive_row.set_activatable(True)
        drive_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        drive_row.connect("activated", lambda _: self._finish(Block(
            category="dbus",
            type="drive_mounted",
            label="Drive Mounted",
            subtitle=filter_entry.get_text().strip() or "Any removable drive",
            params={"filter": filter_entry.get_text().strip()},
        )))
        group.add(drive_row)
        return page

    def _build_file_trigger(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Folder &amp; File Watcher (GIO)",
            "Watches a directory for newly created or modified files. Passes file path as {context}.",
        )

        ep = self._edit_params("dir_changed")
        path_entry = Adw.EntryRow(title="Folder Path")
        if ep and ep.get("path"):
            path_entry.set_text(ep["path"])
        else:
            path_entry.set_text(str(Gio.File.new_for_path("~").get_path()))
        group.add(path_entry)

        browse_btn = Gtk.Button(label="Choose Folder...", margin_top=8)
        def on_browse(_):
            dialog = Gtk.FileDialog(title="Select Folder to Watch")
            dialog.select_folder(self, None, lambda d, res: self._on_folder_chosen(d, res, path_entry))
        browse_btn.connect("clicked", on_browse)
        group.add(browse_btn)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Folder Watcher",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda _: self._finish(Block(
            category="file",
            type="dir_changed",
            label="Folder Changed",
            subtitle=path_entry.get_text().strip(),
            params={"path": path_entry.get_text().strip()},
        )))
        group.add(add_btn)
        return page

    def _on_folder_chosen(self, dialog, result, entry_row):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                entry_row.set_text(folder.get_path())
        except Exception:
            pass

    def _build_flow_trigger(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Chained Flow Trigger",
            "Run this flow immediately after another flow finishes.",
        )
        flows = load_flows()
        if not flows:
            group.add(Adw.ActionRow(title="No other flows available yet"))
            return page

        for f in flows:
            row = Adw.ActionRow(title=f.name, subtitle=f"CLI: flow {f.slug}")
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda _, target=f: self._finish(Block(
                category="flow",
                type="flow_finished",
                label="After Flow Finishes",
                subtitle=target.name,
                params={"flow_id": target.id},
            )))
            group.add(row)
        return page

    # --- ACTION PANELEK (AKKOR ÁG) ---

    def _build_app_action(self) -> Gtk.Widget:
        """Betölti a rendszeren telepített összes alkalmazást ikonnal és keresőmezővel."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(16)
        box.set_margin_end(16)

        search = Gtk.SearchEntry(placeholder_text="Search installed applications...")
        box.append(search)

        listbox = Gtk.ListBox()
        listbox.add_css_class("boxed-list")

        ep = self._edit_params("open_app")
        selected_id = ep.get("desktop_id") if ep else None

        apps = [a for a in Gio.AppInfo.get_all() if a.should_show()]
        apps.sort(key=lambda a: (a.get_name() or "").lower())

        selected_row = None
        for app in apps:
            row = Adw.ActionRow(
                title=app.get_name() or "Unknown",
                subtitle=app.get_id() or "",
            )
            gicon = app.get_icon()
            if gicon:
                img = Gtk.Image.new_from_gicon(gicon)
                img.set_pixel_size(24)
                row.add_prefix(img)
            if selected_id and app.get_id() == selected_id:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
                selected_row = row
            row.set_activatable(True)
            row.connect("activated", lambda _, a=app: self._finish(Block(
                category="app",
                type="open_app",
                label=f"Open {a.get_name()}",
                subtitle=a.get_id() or "",
                params={"desktop_id": a.get_id()},
            )))
            listbox.append(row)

        if selected_row:
            listbox.select_row(selected_row)

        def filter_func(row):
            q = search.get_text().strip().lower()
            if not q:
                return True
            return q in row.get_title().lower() or q in (row.get_subtitle() or "").lower()

        listbox.set_filter_func(filter_func)
        search.connect("search-changed", lambda _: listbox.invalidate_filter())

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(listbox)
        box.append(scroll)
        return box

    def _build_file_action(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Open Folder, File, or URL",
            "Use {context} to open the path passed by the trigger (e.g. mounted drive or new file).",
        )
        ep = self._edit_params("open_path")
        path_entry = Adw.EntryRow(title="Path or URL (or {context})")
        path_entry.set_text(ep.get("path", "{context}") if ep else "{context}")
        group.add(path_entry)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Open Path / URL Action",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda _: self._finish(Block(
            category="file",
            type="open_path",
            label="Open Path / URL",
            subtitle=path_entry.get_text().strip(),
            params={"path": path_entry.get_text().strip()},
        )))
        group.add(add_btn)
        return page

    def _build_system_action(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Notifications &amp; Commands",
            "Supports {context} placeholder in text and command arguments.",
        )

        ep_notif = self._edit_params("notify")
        ep_cmd = self._edit_params("command")

        # 1. Értesítés blokk
        title_entry = Adw.EntryRow(title="Notification Title")
        title_entry.set_text(ep_notif.get("title", "GNOME Flow") if ep_notif else "GNOME Flow")
        body_entry = Adw.EntryRow(title="Notification Body")
        body_entry.set_text(ep_notif.get("body", "Triggered: {context}") if ep_notif else "Triggered: {context}")
        group.add(title_entry)
        group.add(body_entry)

        notif_btn = Gtk.Button(
            label="Save Notification Changes" if ep_notif else "Add Desktop Notification",
            margin_top=8,
            margin_bottom=16,
        )
        notif_btn.add_css_class("suggested-action")
        notif_btn.add_css_class("pill")
        notif_btn.connect("clicked", lambda _: self._finish(Block(
            category="system",
            type="notify",
            label="Send Notification",
            subtitle=f"{title_entry.get_text()}: {body_entry.get_text()}",
            params={"title": title_entry.get_text(), "body": body_entry.get_text()},
        )))
        group.add(notif_btn)

        # 2. Egyéni parancs blokk
        cmd_entry = Adw.EntryRow(title="Shell Command (optional fallback)")
        if ep_cmd:
            cmd_entry.set_text(ep_cmd.get("command", ""))
        group.add(cmd_entry)

        cmd_btn = Gtk.Button(
            label="Save Command Changes" if ep_cmd else "Add Run Command Action",
            margin_top=8,
        )
        if ep_cmd:
            cmd_btn.add_css_class("suggested-action")
        cmd_btn.add_css_class("pill")
        cmd_btn.connect("clicked", lambda _: self._finish(Block(
            category="system",
            type="command",
            label="Run Command",
            subtitle=cmd_entry.get_text().strip(),
            params={"command": cmd_entry.get_text().strip()},
        )))
        group.add(cmd_btn)
        return page

    def _build_delay_action(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Wait / Delay",
            "Pause execution before running the next action in the chain.",
        )
        ep = self._edit_params("delay")
        spin = Adw.SpinRow.new_with_range(0.5, 300.0, 0.5)
        spin.set_title("Seconds to Wait")
        spin.set_value(float(ep.get("seconds", 2.0)) if ep else 2.0)
        group.add(spin)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Delay Action",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda _: self._finish(Block(
            category="time",
            type="delay",
            label="Wait",
            subtitle=f"{spin.get_value():.1f} seconds",
            params={"seconds": spin.get_value()},
        )))
        group.add(add_btn)
        return page

    def _build_flow_action(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Control Another Flow",
            "Enable, disable, toggle, or immediately execute another saved flow.",
        )
        flows = load_flows()
        if not flows:
            group.add(Adw.ActionRow(title="No other flows available yet"))
            return page

        ep = self._edit_params("toggle_flow")
        mode_row = Adw.ComboRow(title="Operation")
        mode_model = Gtk.StringList.new(["Enable Flow", "Disable Flow", "Toggle Flow", "Run Flow Now"])
        mode_keys = ["enable", "disable", "toggle", "run"]
        mode_labels = ["Enable", "Disable", "Toggle", "Run"]
        mode_row.set_model(mode_model)
        if ep and ep.get("state") in mode_keys:
            mode_row.set_selected(mode_keys.index(ep["state"]))
        group.add(mode_row)

        for f in flows:
            row = Adw.ActionRow(title=f.name, subtitle=f"CLI: flow {f.slug}")
            if ep and ep.get("flow_id") == f.id:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda _, target=f: self._finish(Block(
                category="flow",
                type="toggle_flow",
                label=f"{mode_labels[mode_row.get_selected()]} Flow",
                subtitle=target.name,
                params={"flow_id": target.id, "state": mode_keys[mode_row.get_selected()]},
            )))
            group.add(row)
        return page

    # --- CONDITION PANELEK (ÉRVÉNYESSÉGI KÖR) ---

    def _build_app_condition(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Application State Condition",
            "Allow execution only when a specific process is currently running.",
        )
        ep = self._edit_params("app_running")
        proc_entry = Adw.EntryRow(title="Process Name (e.g. code, chromium, amberol)")
        if ep:
            proc_entry.set_text(ep.get("process", ""))
        group.add(proc_entry)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Running App Condition",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda _: self._finish(Block(
            category="app",
            type="app_running",
            label="App is Running",
            subtitle=proc_entry.get_text().strip(),
            params={"process": proc_entry.get_text().strip()},
        )))
        group.add(add_btn)
        return page

    def _build_file_condition(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "File or Folder Exists",
            "Allow execution only if a given path exists on disk.",
        )
        ep = self._edit_params("file_exists")
        path_entry = Adw.EntryRow(title="File or Folder Path")
        if ep:
            path_entry.set_text(ep.get("path", ""))
        group.add(path_entry)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Path Exists Condition",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda _: self._finish(Block(
            category="file",
            type="file_exists",
            label="Path Exists",
            subtitle=path_entry.get_text().strip(),
            params={"path": path_entry.get_text().strip()},
        )))
        group.add(add_btn)
        return page

    def _build_system_condition(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Desktop Appearance Condition",
            "Check current GNOME color scheme.",
        )
        ep = self._edit_params("dark_mode")
        dark_row = Adw.SwitchRow(
            title="Require Dark Mode Active",
            active=bool(ep.get("dark", True)) if ep else True,
        )
        group.add(dark_row)

        add_btn = Gtk.Button(
            label="Save Changes" if ep else "Add Theme Condition",
            margin_top=16,
        )
        add_btn.add_css_class("suggested-action")
        add_btn.add_css_class("pill")
        add_btn.connect("clicked", lambda _: self._finish(Block(
            category="system",
            type="dark_mode",
            label="Desktop Theme",
            subtitle="Dark Mode" if dark_row.get_active() else "Light Mode",
            params={"dark": dark_row.get_active()},
        )))
        group.add(add_btn)
        return page

    def _build_flow_condition(self) -> Gtk.Widget:
        page, group = self._wrap_page(
            "Another Flow State",
            "Valid only while the selected flow is enabled.",
        )
        ep = self._edit_params("flow_enabled")
        for f in load_flows():
            row = Adw.ActionRow(title=f.name)
            if ep and ep.get("flow_id") == f.id:
                row.add_suffix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            row.set_activatable(True)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", lambda _, target=f: self._finish(Block(
                category="flow",
                type="flow_enabled",
                label="Flow is Enabled",
                subtitle=target.name,
                params={"flow_id": target.id},
            )))
            group.add(row)
        return page