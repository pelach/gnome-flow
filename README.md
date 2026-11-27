# GNOME Flow

**Visual IF-THEN desktop automation for GNOME & Libadwaita.**

GNOME Flow lets you build event-driven automation rules (*When → Then*) with conditional validity gates (*Valid When*) for your GNOME desktop using a native GTK4 / Libadwaita interface, a lightweight background `systemd` user daemon, and a CLI tool (`flow`).

---

## Features

- **Visual Rule Editor (GTK4 / Libadwaita):** Create, reorder, test, and toggle automation rules with `AND` / `OR` trigger logic, time/day schedules, and conditional validity gates (*Valid When*).
- **Modular Plugin Architecture:** Every trigger, action, and condition is a self-contained drop-in Python module under `gnome_flow/plugins/` with declarative UI `SCHEMA` definitions.
- **Pipeline Data Flow (`{context}`):** Pass dynamic values between steps — e.g., a mounted drive path, copied URL, focused window title, HTTP response, downloaded file path, or user prompt input — into subsequent actions.
- **Background Daemon (`systemd --user`):** Listens to D-Bus, GIO, UDisks2, Mutter IdleMonitor, and GSettings events with minimal memory footprint (~15 MB).
- **Native Wayland Shell Bridge:** Includes a lightweight companion GNOME Shell extension (`gnome-flow-bridge@pelach.github.com`) exposing Wayland clipboard changes, active window focus events, and window tiling/management over session D-Bus.
- **CLI Control:** Trigger rules manually from scripts, terminal aliases, or custom shortcuts (`flow <rule-name>`).

---

## Built-in Triggers, Actions & Conditions

| Category | Triggers (*When*) | Actions (*Then*) | Conditions (*Valid When*) |
| :--- | :--- | :--- | :--- |
| **Applications** | Application opened / closed, Window focused | Launch installed desktop app (`.desktop` search), Tile / focus / move / close window | Application / process is running |
| **Keyboard Shortcut** | Global keyboard shortcut capture (`Ctrl` / `Alt` / `Super` / `Shift` + key) | — | — |
| **Schedule & Time** | Specific time & days schedule, Repeat interval, Session / daemon startup | — | Time window & active days restriction |
| **Wait / Delay** | — | Pause execution for a configurable delay between actions | — |
| **Files & Folders** | Directory watcher (added, modified, removed via GIO) | Open file/folder/URL, Move, copy, rename, trash, or delete files/folders | File or folder exists on disk |
| **Web & HTTP** | — | HTTP `GET`/`POST` webhook request, Download file directly to folder | — |
| **Text & Data** | — | Set text/template, Regex extract, Find & replace, Split & pick item, Trim/case, Save to file | — |
| **Interaction & Prompts** | — | Native Libadwaita text input box or option selection menu | — |
| **Clipboard** | Text copied on Wayland (with optional Regex filter) | Strip tracking params (`utm_*`, `fbclid`, etc.) from URLs, Clear clipboard | — |
| **Display & Appearance** | Color scheme changed, Wallpaper changed | Switch Light/Dark theme, Toggle Night Light, Set wallpaper, Take screenshot | Desktop Dark/Light mode active |
| **Audio & Media** | Wired headphones plugged / unplugged | Set volume / mute (`wpctl`), Switch audio output sink, Media playback control, Play alert sound | — |
| **Network & Connectivity** | Airplane mode, Bluetooth device connect/disconnect, Wi-Fi connect/disconnect | Toggle Bluetooth power / connect device, Toggle Wi-Fi / connect network | — |
| **System & Notify** | — | Send desktop notification, Run shell command, Toggle Do Not Disturb, Switch power profile, Lock screen / Suspend / Log out | — |
| **Hardware & D-Bus** | Storage drive mounted (`UDisks2`) | — | — |
| **Power** | AC charging / Battery discharging | — | — |
| **User Idle** | Session inactivity timeout (`Mutter.IdleMonitor`) | — | — |
| **Other Flows** | Chained after another flow finishes | Run, enable, disable, or toggle another flow | Another flow is enabled |

---

## Context Pipeline Example

Actions can pass data forward via `{context}`:

1. **When:** `Scheduled Time` (Weekdays at `07:00`)
2. **Then 1 (`Web & HTTP`):** `GET` RSS feed URL → passes XML response as `{context}`
3. **Then 2 (`Text & Data`):** `Split & Pick` `<item>` `#1` → `Regex Extract` episode `.mp3` URL → passes URL as `{context}`
4. **Then 3 (`Web & HTTP`):** `Download to Folder` (`~/Podcasts`) using `{context}` → passes saved file path as `{context}`
5. **Then 4 (`System & Notify`):** `Send Notification` → *"Downloaded: `{context}`"*

---

## Requirements

- **OS / Desktop:** Linux with GNOME 48+ (Wayland or X11)
- **System Packages:**
  - `python3` with PyGObject (`python3-gi`), GTK 4 (`gir1.2-gtk-4.0`), and Libadwaita (`gir1.2-adw-1`)
  - `pipewire` / `wireplumber` (`wpctl`) for audio control
  - `bluez` (`bluetoothctl`) and `network-manager` (`nmcli`) for connectivity actions
  - `wl-clipboard` (`wl-copy`, `wl-paste`) for clipboard write/clear actions

On Debian / Ubuntu:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 wireplumber bluez network-manager wl-clipboard
```

---

## Installation

1. Clone the repository:

```bash
git clone [https://github.com/pelach/gnome-flow.git](https://github.com/pelach/gnome-flow.git)
cd gnome-flow
```

2. Run the installer:

```bash
./install.sh
```

*(For development, `./install.sh --dev` symlinks the repository directory instead of copying files.)*

3. **Activate Wayland Shell Bridge (first install only):**
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

Create a `.py` file inside `gnome_flow/plugins/` defining:
- `MODE`: `"trigger"`, `"action"`, or `"condition"`
- `CATEGORY`, `TYPE`, `LABEL`, `DESCRIPTION`, and `SCHEMA`
- Entry point function:
  - `start_watch(trigger, fire_callback)` returning a cleanup callable (for triggers)
  - `run(params, context="")` returning `bool` or `{"context": ...}` (for actions)
  - `check(params)` returning `bool` (for conditions)

Restart the daemon (`systemctl --user restart gnome-flow-daemon.service`) to load new plugins automatically.

---

## Credits

Developed by [@pelach](https://github.com/pelach) with AI assistance from **Google Gemini**.

---

## License

See [LICENSE](LICENSE) for details.