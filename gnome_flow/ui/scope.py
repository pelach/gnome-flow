import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ..model import ValidityScope, Block
from .picker import BlockPickerDialog


def make_time_picker(initial_hhmm: str) -> tuple[Gtk.Box, Gtk.SpinButton, Gtk.SpinButton]:
    """Natív Libadwaita stílusú óra:perc választó két körbeforduló (wrap) SpinButton-nal."""
    try:
        h, m = map(int, initial_hhmm.split(":"))
    except ValueError:
        h, m = 8, 0

    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    box.set_valign(Gtk.Align.CENTER)

    hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
    hour_spin.set_wrap(True)
    hour_spin.set_value(h)
    hour_spin.set_width_chars(2)
    # Kétjegyű formázás (pl. 08)
    hour_spin.connect("output", lambda s: (s.set_text(f"{int(s.get_value()):02d}"), True)[1])

    colon = Gtk.Label(label=":")
    colon.add_css_class("title-4")

    min_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
    min_spin.set_wrap(True)
    min_spin.set_value(m)
    min_spin.set_width_chars(2)
    min_spin.connect("output", lambda s: (s.set_text(f"{int(s.get_value()):02d}"), True)[1])

    box.append(hour_spin)
    box.append(colon)
    box.append(min_spin)
    return box, hour_spin, min_spin


class ValidityScopeDialog(Adw.Dialog):
    """Érvényességi kör dialógus (Hatékony időszak + Feltétel-kapuk)."""

    def __init__(self, scope: ValidityScope, on_saved):
        super().__init__()
        self.scope = scope
        self.on_saved = on_saved

        self.set_title("Validity Scope")
        self.set_content_width(540)
        self.set_content_height(560)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()

        done_btn = Gtk.Button(label="Done")
        done_btn.add_css_class("suggested-action")
        done_btn.connect("clicked", self._on_done)
        header.pack_end(done_btn)
        toolbar.add_top_bar(header)

        page = Adw.PreferencesPage()

        # 1. Szekció: Hatékony időszak (Effective Period)
        time_group = Adw.PreferencesGroup(
            title="Effective Period",
            description="Restrict when this automation is allowed to run. Does not trigger execution by itself.",
        )

        self.time_switch = Adw.SwitchRow(
            title="Enable Time &amp; Day Restriction",
            active=scope.time_enabled,
        )
        time_group.add(self.time_switch)

        # Kezdő időpont sor
        start_row = Adw.ActionRow(title="Start Time")
        start_box, self.sh_spin, self.sm_spin = make_time_picker(scope.start_time)
        start_row.add_suffix(start_box)
        time_group.add(start_row)

        # Befejező időpont sor
        end_row = Adw.ActionRow(title="End Time")
        end_box, self.eh_spin, self.em_spin = make_time_picker(scope.end_time)
        end_row.add_suffix(end_box)
        time_group.add(end_row)

        # Hét napjai (összefűzött ToggleButton sáv)
        days_row = Adw.ActionRow(title="Active Days")
        days_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        days_box.add_css_class("linked")
        days_box.set_valign(Gtk.Align.CENTER)

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.day_buttons = []
        for idx, dname in enumerate(day_names):
            btn = Gtk.ToggleButton(label=dname)
            btn.set_active(idx in scope.days)
            days_box.append(btn)
            self.day_buttons.append(btn)

        days_row.add_suffix(days_box)
        time_group.add(days_row)
        page.add(time_group)

        # 2. Szekció: Érvényes mikor (Valid When)
        self.cond_group = Adw.PreferencesGroup(
            title="Valid When",
            description="Additional system state conditions required before actions execute.",
        )

        add_cond_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Condition")
        add_cond_btn.add_css_class("flat")
        add_cond_btn.connect("clicked", self._on_add_condition)
        self.cond_group.set_header_suffix(add_cond_btn)

        self.mode_row = Adw.ComboRow(title="Condition Logic")
        self.mode_row.set_model(Gtk.StringList.new(["Any condition is met (OR)", "All conditions are met (AND)"]))
        self.mode_row.set_selected(1 if scope.condition_mode == "all" else 0)
        self.cond_group.add(self.mode_row)

        self.cond_rows = []
        page.add(self.cond_group)

        toolbar.set_content(page)
        self.set_child(toolbar)
        self._refresh_conditions()

    def _refresh_conditions(self):
        for r in self.cond_rows:
            self.cond_group.remove(r)
        self.cond_rows.clear()

        for idx, cond in enumerate(self.scope.conditions):
            row = Adw.ActionRow(
                title=GLib.markup_escape_text(cond.label, -1),
                subtitle=GLib.markup_escape_text(cond.subtitle, -1),
            )
            row.set_activatable(True)
            row.connect("activated", lambda _, i=idx: self._edit_condition(i))
            del_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
            del_btn.add_css_class("flat")
            del_btn.connect("clicked", lambda _, i=idx: self._remove_condition(i))
            row.add_suffix(del_btn)
            self.cond_group.add(row)
            self.cond_rows.append(row)

    def _remove_condition(self, idx: int):
        self.scope.conditions.pop(idx)
        self._refresh_conditions()

    def _on_add_condition(self, _):
        picker = BlockPickerDialog("condition", on_selected=self._on_condition_picked)
        picker.present(self)

    def _on_condition_picked(self, block: Block):
        self.scope.conditions.append(block)
        self._refresh_conditions()

    def _on_done(self, _):
        self.scope.time_enabled = self.time_switch.get_active()
        self.scope.start_time = f"{int(self.sh_spin.get_value()):02d}:{int(self.sm_spin.get_value()):02d}"
        self.scope.end_time = f"{int(self.eh_spin.get_value()):02d}:{int(self.em_spin.get_value()):02d}"
        self.scope.days = [i for i, b in enumerate(self.day_buttons) if b.get_active()]
        self.scope.condition_mode = "all" if self.mode_row.get_selected() == 1 else "any"
        self.on_saved(self.scope)
        self.close()

    def _edit_condition(self, idx: int):
        def on_updated(updated: Block):
            self.scope.conditions[idx] = updated
            self._refresh_conditions()

        BlockPickerDialog("condition", on_selected=on_updated, edit_block=self.scope.conditions[idx]).present(self)