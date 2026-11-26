# GNOME Flow

**Visual IF-THEN desktop automation for GNOME & Libadwaita.**

GNOME Flow lets you build event-driven automation rules (*When → Then*) for your GNOME desktop using a clean GTK4 / Libadwaita interface, a lightweight background `systemd` user daemon, and a CLI tool (`flow`).

---

## Features

- **Visual Rule Editor (GTK4 / Libadwaita):** Create, toggle, test, and manage automation rules with `AND` / `OR` trigger logic and validity time scopes.
- **Rich Built-in Triggers & Actions:** Combine global hotkeys, schedules, filesystem watchers, hardware/D-Bus events, flow chaining, delays, and desktop controls out of the box.
- **Modular Plugin Architecture:** Extend functionality with drop-in Python triggers and actions under `gnome_flow/plugins/`.
- **Background Daemon (`systemd --user`):** Listens to D-Bus, GIO, GSettings, and system events with minimal memory footprint (~15 MB).
- **Native Wayland Clipboard Support:** Includes a lightweight companion GNOME Shell extension (`gnome-flow-bridge@pelach.github.com`) that exposes Wayland clipboard changes over session D-Bus without polling or focus restrictions.
- **CLI Control:** Trigger rules manually from scripts, terminal aliases, or custom shortcuts (`flow <rule-name>`).

---

## Built-in Triggers & Actions

| Category | Triggers (*When*) | Actions (*Then*) |
| :--- | :--- | :--- |
| **Keyboard Shortcut** | Global keyboard shortcut capture (Ctrl / Alt / Super / Shift + key) | — |
| **Schedule & Time** | Specific time / schedule, Interval timer | — |
| **Wait / Delay** | — | Pause execution for a configurable delay between actions |
| **Files & Folders** | File or directory created, modified, or deleted (GIO monitor) | Create, copy, move, delete files/folders |
| **Applications** | — | Launch any installed desktop application (`.desktop` search) |
| **System & Notify** | — | Run shell command, Send desktop notification |
| **Other Flows** | Triggered by another flow | Chain / execute another automation flow |
| **Hardware & D-Bus** | Custom D-Bus signal or hardware event | — |
| **Bluetooth** | Bluetooth device connected / disconnected | Connect / disconnect Bluetooth device |
| **Power** | AC charging / Battery discharging | — |
| **Display** | Color scheme changed (Light / Dark) | Toggle Dark/Light theme, Toggle Night Light, Set wallpaper, Toggle Do Not Disturb |
| **Audio** | — | Set volume level, Toggle mute (PipeWire / `wpctl`) |
| **Clipboard** | Text copied on Wayland (with optional Regex filter) | Strip tracking params (`utm_*`, `fbclid`, etc.) from URLs, Clear clipboard |
| **User Idle** | Session idle timeout | — |

---

## Requirements

- **OS / Desktop:** Linux with GNOME 48+ (Wayland or X11)
- **System Packages:**
  - `python3` with PyGObject (`python3-gi`), GTK 4 (`gir1.2-gtk-4.0`), and Libadwaita (`gir1.2-adw-1`)
  - `pipewire` / `wireplumber` (`wpctl`) for audio volume actions
  - `bluez` (`bluetoothctl`) for Bluetooth actions

On Debian / Ubuntu:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 wireplumber bluez
```

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/pelach/gnome-flow.git
cd gnome-flow
```

2. Run the installer:

```bash
./install.sh
```

*(For development, `./install.sh --dev` symlinks the repository directory instead of copying files.)*

3. **Activate Wayland Clipboard Bridge (first install only):**
Log out and log back in once so GNOME Shell registers `gnome-flow-bridge@pelach.github.com`, then ensure it is enabled:

```bash
gnome-extensions enable gnome-flow-bridge@pelach.github.com
```

### Uninstall

```bash
./install.sh uninstall
```

*(Your saved rules in `~/.config/gnome-flow` are preserved.)*

---

## Usage

- **GUI:** Open **GNOME Flow** from your application grid or run `flow` in a terminal.
- **Run a rule via CLI / Shortcut:**

```bash
flow <rule-name>
```

- **Check background daemon status:**

```bash
systemctl --user status gnome-flow-daemon.service
```

---

## Writing Custom Plugins

Create a `.py` file inside `gnome_flow/plugins/` defining `MODE = "trigger"` (with `start_watch(trigger, fire_callback)`) or `MODE = "action"` (with `run(params, context="")`), along with `CATEGORY`, `TYPE`, `LABEL`, and `SCHEMA`. Restart the daemon (`systemctl --user restart gnome-flow-daemon.service`) to load it automatically.

---

## Credits

Developed by [@pelach](https://github.com/pelach) with AI assistance from **Google Gemini**.


---

## License

See [LICENSE](LICENSE) for details.
