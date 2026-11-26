#!/usr/bin/env bash
set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/gnome-flow"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
SYSTEMD_DIR="$HOME/.config/systemd/user"

mkdir -p "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR" "$SYSTEMD_DIR"

# Régi /usr/local/bin/flow figyelmeztetés, ha maradt korábbi tesztből
if [ -f "/usr/local/bin/flow" ]; then
    echo "Megjegyzés: /usr/local/bin/flow létezik. Ha az előbbre van a PATH-ban, törölheted: sudo rm /usr/local/bin/flow"
fi

rm -rf "$APP_DIR"

if [ "$1" = "--dev" ]; then
    echo "Fejlesztői mód: szimbolikus link létrehozása ($REPO_DIR -> $APP_DIR)..."
    ln -s "$REPO_DIR" "$APP_DIR"
else
    echo "Alkalmazás fájlok másolása ide: $APP_DIR..."
    mkdir -p "$APP_DIR"
    cp "$REPO_DIR/flow.py" "$APP_DIR/"
    cp -r "$REPO_DIR/gnome_flow" "$APP_DIR/"
    find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
fi

# Futtatható parancs létrehozása (~/.local/bin/flow)
cat > "$BIN_DIR/flow" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DIR/flow.py" "\$@"
EOF
chmod +x "$BIN_DIR/flow"

# Ikon és .desktop fájl telepítése
cp "$REPO_DIR/data/org.gnome.Flow.svg" "$ICON_DIR/"
cp "$REPO_DIR/data/org.gnome.Flow.desktop" "$DESKTOP_DIR/"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# Systemd user service telepítése és indítása
cp "$REPO_DIR/data/gnome-flow-daemon.service" "$SYSTEMD_DIR/"
systemctl --user daemon-reload

# Ha korábban kézzel indított daemon futott, leállítjuk, hogy a systemd vegye át
pkill -f "flow.py --daemon" 2>/dev/null || true
sleep 0.5

systemctl --user enable --now gnome-flow-daemon.service

echo ""
echo "GNOME Flow sikeresen telepítve!"
echo " - Alkalmazásindító: keresd a 'GNOME Flow' ikont a menüben"
echo " - Háttérszolgáltatás állapota: systemctl --user status gnome-flow-daemon.service"