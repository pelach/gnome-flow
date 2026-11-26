import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class GnomeFlowBridgeExtension extends Extension {
    enable() {
        this._selection = global.display.get_selection();
        this._clipboard = St.Clipboard.get_default();
        this._lastText = '';

        this._ownerChangedId = this._selection.connect(
            'owner-changed',
            (_sel, selectionType) => {
                if (selectionType !== Meta.SelectionType.SELECTION_CLIPBOARD)
                    return;

                this._clipboard.get_text(St.ClipboardType.CLIPBOARD, (_cb, text) => {
                    if (!text)
                        return;
                    const trimmed = text.trim();
                    if (!trimmed || trimmed === this._lastText)
                        return;
                    this._lastText = trimmed;

                    Gio.DBus.session.emit_signal(
                        null,
                        '/org/gnome/Flow/ShellBridge',
                        'org.gnome.Flow.ShellBridge',
                        'ClipboardChanged',
                        new GLib.Variant('(s)', [trimmed])
                    );
                });
            }
        );
    }

    disable() {
        if (this._selection && this._ownerChangedId) {
            this._selection.disconnect(this._ownerChangedId);
            this._ownerChangedId = null;
        }
        this._selection = null;
        this._clipboard = null;
    }
}