import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import Shell from 'gi://Shell';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BRIDGE_IFACE = `
<node>
  <interface name="org.gnome.Flow.ShellBridge">
    <method name="ManageWindow">
      <arg type="s" name="app_filter" direction="in"/>
      <arg type="s" name="action" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>
    <signal name="ClipboardChanged">
      <arg type="s" name="text"/>
    </signal>
    <signal name="FocusChanged">
        <arg type="s" name="wm_class"/>
        <arg type="s" name="title"/>
    </signal>
  </interface>
</node>
`;

export default class GnomeFlowBridgeExtension extends Extension {
    enable() {
        this._selection = global.display.get_selection();
        this._clipboard = St.Clipboard.get_default();
        this._lastText = '';

        // 1. Vágólap-figyelés
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

        this._focusSignalId = global.display.connect('notify::focus-window', () => {
            const win = global.display.get_focus_window();
            if (!win)
                return;
            const wmClass = win.get_wm_class() || '';
            const title = win.get_title() || '';
            Gio.DBus.session.emit_signal(
                null,
                '/org/gnome/Flow/ShellBridge',
                'org.gnome.Flow.ShellBridge',
                'FocusChanged',
                new GLib.Variant('(ss)', [wmClass, title])
            );
        });

        // 2. D-Bus metódusok regisztrálása (ablakkezeléshez)
        this._dbusImpl = Gio.DBusExportedObject.wrapJSObject(BRIDGE_IFACE, this);
        this._dbusImpl.export(Gio.DBus.session, '/org/gnome/Flow/ShellBridge');
    }

    disable() {
        if (this._dbusImpl) {
            this._dbusImpl.unexport();
            this._dbusImpl = null;
        }
        if (this._selection && this._ownerChangedId) {
            this._selection.disconnect(this._ownerChangedId);
            this._ownerChangedId = null;
        }
        if (this._focusSignalId) {
            global.display.disconnect(this._focusSignalId);
            this._focusSignalId = 0;
        }
        this._selection = null;
        this._clipboard = null;
    }

    ManageWindow(appFilter, action) {
        try {
            const win = this._findTargetWindow(appFilter);
            if (!win)
                return false;

            const now = global.get_current_time();

            if (action === 'close') {
                win.delete(now);
                return true;
            }
            if (action === 'minimize') {
                win.minimize();
                return true;
            }

            // Előtérbe hozzuk és feloldjuk a minimalizálást
            if (win.minimized)
                win.unminimize();
            win.activate(now);

            if (action === 'focus')
                return true;

            if (action === 'ws-next' || action === 'ws-prev') {
                const wm = global.workspace_manager;
                const curIdx = win.get_workspace()?.index() ?? wm.get_active_workspace_index();
                const targetIdx = action === 'ws-next'
                    ? Math.min(curIdx + 1, wm.get_n_workspaces() - 1)
                    : Math.max(curIdx - 1, 0);
                const targetWs = wm.get_workspace_by_index(targetIdx);
                if (targetWs) {
                    win.change_workspace(targetWs);
                    targetWs.activate(now);
                }
                return true;
            }

            if (action === 'maximize') {
                win.maximize(Meta.MaximizeFlags.BOTH);
                return true;
            }

            if (action === 'unmaximize') {
                win.unmaximize(Meta.MaximizeFlags.BOTH);
                return true;
            }

            // Pozicionálás / csempézés előtt feloldjuk a maximalizálást
            if (win.get_maximized() !== 0)
                win.unmaximize(Meta.MaximizeFlags.BOTH);

            const monitor = win.get_monitor();
            const workArea = win.get_work_area_for_monitor(monitor);

            let x = workArea.x;
            let y = workArea.y;
            let w = workArea.width;
            let h = workArea.height;

            switch (action) {
            case 'left':
                w = Math.floor(workArea.width / 2);
                break;
            case 'right':
                w = Math.floor(workArea.width / 2);
                x = workArea.x + w;
                break;
            case 'top':
                h = Math.floor(workArea.height / 2);
                break;
            case 'bottom':
                h = Math.floor(workArea.height / 2);
                y = workArea.y + h;
                break;
            case 'top-left':
                w = Math.floor(workArea.width / 2);
                h = Math.floor(workArea.height / 2);
                break;
            case 'top-right':
                w = Math.floor(workArea.width / 2);
                h = Math.floor(workArea.height / 2);
                x = workArea.x + w;
                break;
            case 'bottom-left':
                w = Math.floor(workArea.width / 2);
                h = Math.floor(workArea.height / 2);
                y = workArea.y + h;
                break;
            case 'bottom-right':
                w = Math.floor(workArea.width / 2);
                h = Math.floor(workArea.height / 2);
                x = workArea.x + w;
                y = workArea.y + h;
                break;
            case 'center':
                w = Math.floor(workArea.width * 0.7);
                h = Math.floor(workArea.height * 0.8);
                x = workArea.x + Math.floor((workArea.width - w) / 2);
                y = workArea.y + Math.floor((workArea.height - h) / 2);
                break;
            default:
                return false;
            }

            win.move_resize_frame(true, x, y, w, h);
            return true;
        } catch (e) {
            logError(e, '[GNOME Flow Bridge] ManageWindow failed');
            return false;
        }
    }

    _findTargetWindow(appFilter) {
        const query = (appFilter || '').trim().toLowerCase();
        if (!query)
            return global.display.get_focus_window();

        const tracker = Shell.WindowTracker.get_default();
        // MRU (legutóbb fókuszált) sorrendben kérjük le az összes normál ablakot
        const actors = global.get_window_actors();
        const windows = actors
            .map(a => a.get_meta_window())
            .filter(w => w && w.get_window_type() === Meta.WindowType.NORMAL)
            .sort((a, b) => b.get_user_time() - a.get_user_time());

        for (const win of windows) {
            const wmClass = (win.get_wm_class() || '').toLowerCase();
            const wmInst = (win.get_wm_class_instance() || '').toLowerCase();
            const title = (win.get_title() || '').toLowerCase();
            const app = tracker.get_window_app(win);
            const appId = (app ? app.get_id() : '').toLowerCase();
            const appName = (app ? app.get_name() : '').toLowerCase();

            if (
                wmClass.includes(query) ||
                wmInst.includes(query) ||
                title.includes(query) ||
                appId.includes(query) ||
                appName.includes(query)
            )
                return win;
        }
        return null;
    }
}