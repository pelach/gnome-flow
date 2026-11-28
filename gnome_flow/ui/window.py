import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from ..model import Flow, Block, load_flows, save_flows
from ..engine import FlowEngine
from ..daemon import BUS_NAME, OBJECT_PATH
from .picker import BlockPickerDialog
from .scope import ValidityScopeDialog

import threading

def notify_daemon_reload():
    """Szól a háttérben futó daemonnak D-Bus-on, hogy töltse újra a szabályokat."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None, BUS_NAME, OBJECT_PATH, BUS_NAME, None
        )
        if proxy.get_name_owner():
            proxy.call_sync("Reload", None, Gio.DBusCallFlags.NONE, -1, None)
    except Exception:
        pass


class FlowEditorPage(Adw.NavigationPage):
    """Egyetlen automatizmus szerkesztő nézete (When / Then / Validity Scope)."""

    def __init__(self, flow: Flow, is_new: bool, on_save_callback, on_delete_callback):
        super().__init__(title=flow.name if not is_new else "New Automation")
        self.flow = flow
        self.is_new = is_new
        self.on_save_callback = on_save_callback
        self.on_delete_callback = on_delete_callback

        self.trigger_rows = []
        self.action_rows = []

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        if not is_new:
            del_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete Flow")
            del_btn.add_css_class("destructive-action")
            del_btn.connect("clicked", lambda _: self.on_delete_callback(self.flow))
            header.pack_end(del_btn)

        toolbar.add_top_bar(header)

        page = Adw.PreferencesPage()

        # 0. Név és CLI azonosító
        info_group = Adw.PreferencesGroup()
        self.name_entry = Adw.EntryRow(title="Automation Name")
        self.name_entry.set_text(flow.name)
        self.name_entry.connect("changed", self._on_name_changed)
        info_group.add(self.name_entry)

        self.slug_row = Adw.ActionRow(
            title="CLI Command",
            subtitle=f"flow {Flow.make_slug(flow.name)}",
        )
        info_group.add(self.slug_row)
        page.add(info_group)

        # 1. WHEN (HA ág)
        self.when_group = Adw.PreferencesGroup(title="When")
        add_trig_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Trigger")
        add_trig_btn.add_css_class("flat")
        add_trig_btn.connect("clicked", self._open_trigger_picker)
        self.when_group.set_header_suffix(add_trig_btn)

        self.trig_mode_row = Adw.ComboRow(title="Trigger Logic")
        self.trig_mode_row.set_model(Gtk.StringList.new(["Any condition is met (OR)", "All conditions are met (AND)"]))
        self.trig_mode_row.set_selected(1 if flow.trigger_mode == "all" else 0)
        self.when_group.add(self.trig_mode_row)
        page.add(self.when_group)

        # 2. THEN (AKKOR ág)
        self.then_group = Adw.PreferencesGroup(title="Then")
        add_act_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Action")
        add_act_btn.add_css_class("flat")
        add_act_btn.connect("clicked", self._open_action_picker)
        self.then_group.set_header_suffix(add_act_btn)
        page.add(self.then_group)

        # 3. VALIDITY SCOPE (Érvényességi kör)
        scope_group = Adw.PreferencesGroup()
        self.scope_row = Adw.ActionRow(title="Validity Scope")
        self.scope_row.set_activatable(True)
        self.scope_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        self.scope_row.connect("activated", self._open_scope_dialog)
        scope_group.add(self.scope_row)
        page.add(scope_group)

        # 4. Mentés gomb alul
        save_group = Adw.PreferencesGroup()
        self.save_btn = Gtk.Button(label="Save Automation")
        self.save_btn.add_css_class("suggested-action")
        self.save_btn.connect("clicked", self._on_save)
        save_group.add(self.save_btn)
        page.add(save_group)

        toolbar.set_content(page)
        self.set_child(toolbar)

        self._refresh_triggers()
        self._refresh_actions()
        self._update_scope_summary()
        self._validate_name()

    def _on_name_changed(self, entry):
        name = entry.get_text().strip() or "New Flow"
        self.set_title(name)
        self.slug_row.set_subtitle(f"flow {Flow.make_slug(name)}")

    def _update_scope_summary(self):
        s = self.flow.scope
        parts = []
        if s.time_enabled:
            parts.append(f"{s.start_time}–{s.end_time}")
        else:
            parts.append("All Day")
        if s.conditions:
            parts.append(f"{len(s.conditions)} condition(s)")
        self.scope_row.set_subtitle(" · ".join(parts))

    def _refresh_triggers(self):
        for r in self.trigger_rows:
            self.when_group.remove(r)
        self.trigger_rows.clear()

        for idx, trig in enumerate(self.flow.triggers):
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(trig.label, -1),
                subtitle=GLib.markup_escape_text(trig.subtitle, -1),
            )
            row.set_activatable(True)
            row.connect("activated", lambda _, i=idx: self._edit_trigger(i))
            del_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            del_btn.add_css_class("flat")
            del_btn.connect("clicked", lambda _, i=idx: self._remove_trigger(i))
            row.add_suffix(del_btn)
            self.when_group.add(row)
            self.trigger_rows.append(row)

    def _remove_trigger(self, idx: int):
        self.flow.triggers.pop(idx)
        self._refresh_triggers()

    def _refresh_actions(self):
        for row in self.action_rows:
            self.then_group.remove(row)
        self.action_rows.clear()

        total = len(self.flow.actions)
        for idx, act in enumerate(self.flow.actions):
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(f"{idx + 1}. {act.label}", -1),
                subtitle=GLib.markup_escape_text(act.subtitle, -1),
            )
            row.set_activatable(True)
            row.connect("activated", lambda _, i=idx: self._edit_action(i))

            btn_box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=2,
                valign=Gtk.Align.CENTER,
            )

            if idx > 0:
                up_btn = Gtk.Button(
                    icon_name="go-up-symbolic",
                    tooltip_text="Move up",
                )
                up_btn.add_css_class("flat")
                up_btn.connect("clicked", self._move_action, idx, -1)
                btn_box.append(up_btn)

            if idx < total - 1:
                down_btn = Gtk.Button(
                    icon_name="go-down-symbolic",
                    tooltip_text="Move down",
                )
                down_btn.add_css_class("flat")
                down_btn.connect("clicked", self._move_action, idx, 1)
                btn_box.append(down_btn)

            del_btn = Gtk.Button(
                icon_name="user-trash-symbolic",
                tooltip_text="Remove action",
            )
            del_btn.add_css_class("flat")
            del_btn.connect("clicked", self._remove_action, idx)
            btn_box.append(del_btn)

            row.add_suffix(btn_box)
            self.then_group.add(row)
            self.action_rows.append(row)

    def _remove_action(self, idx: int):
        self.flow.actions.pop(idx)
        self._refresh_actions()

    def _move_action(self, _btn, idx: int, delta: int):
        new_idx = idx + delta
        if 0 <= new_idx < len(self.flow.actions):
            actions = self.flow.actions
            actions[idx], actions[new_idx] = actions[new_idx], actions[idx]
            self._refresh_actions()

    def _open_trigger_picker(self, _):
        dlg = BlockPickerDialog("trigger", on_selected=self._on_trigger_added)
        dlg.set_transient_for(self.get_root())
        dlg.present()

    def _on_trigger_added(self, block: Block):
        self.flow.triggers.append(block)
        self._refresh_triggers()

    def _open_action_picker(self, _):
        dlg = BlockPickerDialog("action", on_selected=self._on_action_added)
        dlg.set_transient_for(self.get_root())
        dlg.present()

    def _on_action_added(self, block: Block):
        self.flow.actions.append(block)
        self._refresh_actions()

    def _open_scope_dialog(self, _):
        ValidityScopeDialog(self.flow.scope, on_saved=lambda _: self._update_scope_summary()).present(self)

    def _on_save(self, _):
        if not self._validate_name():
            return
        name = self.name_entry.get_text().strip()
        self.flow.name = name
        self.flow.slug = Flow.make_slug(name)
        self.flow.trigger_mode = "all" if self.trig_mode_row.get_selected() == 1 else "any"
        self.on_save_callback(self.flow, self.is_new)

    def _edit_trigger(self, idx: int):
        def on_updated(updated: Block):
            self.flow.triggers[idx] = updated
            self._refresh_triggers()

        dlg = BlockPickerDialog("trigger", on_selected=on_updated, edit_block=self.flow.triggers[idx])
        dlg.set_transient_for(self.get_root())
        dlg.present()

    def _edit_action(self, idx: int):
        def on_updated(updated: Block):
            self.flow.actions[idx] = updated
            self._refresh_actions()

        dlg = BlockPickerDialog("action", on_selected=on_updated, edit_block=self.flow.actions[idx])
        dlg.set_transient_for(self.get_root())
        dlg.present()

    def _validate_name(self) -> bool:
        raw_name = self.name_entry.get_text().strip()
        if not raw_name:
            self.name_entry.add_css_class("error")
            self.slug_row.set_subtitle("Name cannot be empty")
            self.save_btn.set_sensitive(False)
            return False

        candidate_slug = Flow.make_slug(raw_name)
        conflict = any(
            f.slug == candidate_slug and f.id != self.flow.id
            for f in load_flows()
        )
        if conflict:
            self.name_entry.add_css_class("error")
            self.slug_row.set_subtitle(f"flow {candidate_slug}  —  already in use!")
            self.save_btn.set_sensitive(False)
            return False

        self.name_entry.remove_css_class("error")
        self.slug_row.set_subtitle(f"flow {candidate_slug}")
        self.save_btn.set_sensitive(True)
        return True

    def _on_name_changed(self, entry):
        name = entry.get_text().strip() or "New Flow"
        self.set_title(name)
        self._validate_name()

class MainWindow(Adw.ApplicationWindow):
    """A GNOME Flow főablaka."""

    def __init__(self, app):
        super().__init__(application=app, title="GNOME Flow")
        self.set_default_size(640, 620)
        self.engine = FlowEngine(on_flows_changed=self._reload_list)

        self.nav = Adw.NavigationView()
        self.set_content(self.nav)

        # Főoldal felépítése
        self.home_page = Adw.NavigationPage(title="GNOME Flow")
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Create New Flow")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_create_flow)
        header.pack_end(add_btn)

        toolbar.add_top_bar(header)

        pref_page = Adw.PreferencesPage()
        self.list_group = Adw.PreferencesGroup(
            title="Automations",
            description="Click a flow to edit, press Play to run manually, or invoke via CLI: flow &lt;name&gt;",
        )
        pref_page.add(self.list_group)
        toolbar.set_content(pref_page)
        self.home_page.set_child(toolbar)

        self.nav.add(self.home_page)
        self.flow_rows = []
        self._reload_list()

    def _reload_list(self):
        for r in self.flow_rows:
            self.list_group.remove(r)
        self.flow_rows.clear()

        flows = load_flows()
        if not flows:
            empty = Adw.ActionRow(
                title="No automations yet",
                subtitle="Click the + button in the top right to build your first IF-THEN flow.",
            )
            self.list_group.add(empty)
            self.flow_rows.append(empty)
            return

        for f in flows:
            trig_summary = ", ".join(t.label for t in f.triggers) or "Manual / CLI only"
            act_summary = " → ".join(a.label for a in f.actions) or "No actions"
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(f.name, -1),
                subtitle=GLib.markup_escape_text(
                    f"When: {trig_summary}  |  Then: {act_summary}  (cli: flow {f.slug})", -1
                ),
            )
            row.set_activatable(True)
            row.connect("activated", lambda _, target=f: self._open_editor(target, is_new=False))

            # Azonnali futtatás (Play) gomb
            run_btn = Gtk.Button(icon_name="media-playback-start-symbolic", tooltip_text="Run Now", valign=Gtk.Align.CENTER)
            run_btn.add_css_class("flat")
            run_btn.connect("clicked", self._on_play_clicked, f)
            row.add_suffix(run_btn)

            # Aktív / Kikapcsolt kapcsoló
            sw = Gtk.Switch(active=f.enabled, valign=Gtk.Align.CENTER)
            sw.connect("state-set", lambda _, state, target=f: self._on_toggle_enabled(target, state))
            row.add_suffix(sw)

            self.list_group.add(row)
            self.flow_rows.append(row)

    def _on_play_clicked(self, _btn, target: Flow):
        def _fallback_local():
            threading.Thread(
                target=self.engine.execute_flow,
                args=(target,),
                kwargs={"force": True},
                daemon=True,
            ).start()

        def _on_dbus_done(bus, res):
            try:
                bus.call_finish(res)
            except Exception:
                _fallback_local()

        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            bus.call(
                "org.gnome.Flow.Daemon",
                "/org/gnome/Flow/Daemon",
                "org.gnome.Flow.Daemon",
                "RunFlow",
                GLib.Variant("(ss)", (target.slug, "")),
                GLib.VariantType("(b)"),
                Gio.DBusCallFlags.NONE,
                2000,
                None,
                _on_dbus_done,
            )
        except Exception:
            _fallback_local()

    def _on_toggle_enabled(self, flow: Flow, state: bool):
        flows = load_flows()
        for item in flows:
            if item.id == flow.id:
                item.enabled = state
        save_flows(flows)
        notify_daemon_reload()
        return False

    def _on_create_flow(self, _):
        existing = load_flows()
        unique_name = Flow.make_unique_name("New Flow", existing)
        new_flow = Flow(name=unique_name, slug=Flow.make_slug(unique_name))
        self._open_editor(new_flow, is_new=True)

    def _open_editor(self, flow: Flow, is_new: bool):
        editor = FlowEditorPage(
            flow=flow,
            is_new=is_new,
            on_save_callback=self._on_save_flow,
            on_delete_callback=self._on_delete_flow,
        )
        self.nav.push(editor)

    def _on_save_flow(self, flow: Flow, is_new: bool):
        flows = load_flows()
        if is_new:
            flows.append(flow)
        else:
            flows = [flow if item.id == flow.id else item for item in flows]
        save_flows(flows)
        notify_daemon_reload()
        self.nav.pop()
        self._reload_list()

    def _on_delete_flow(self, flow: Flow):
        flows = [item for item in load_flows() if item.id != flow.id]
        save_flows(flows)
        notify_daemon_reload()
        self.nav.pop()
        self._reload_list()


class GnomeFlowApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.gnome.Flow")

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(self)
        win.present()


def run_gui():
    app = GnomeFlowApp()
    app.run(None)