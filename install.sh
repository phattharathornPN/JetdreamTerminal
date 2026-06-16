#!/bin/bash
set -e

APPDIR="$(cd "$(dirname "$0")" && pwd)"
ICON_FILE="$APPDIR/assets/icon.svg"
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

echo "=== Installing JetdreamTerminal ==="

# Setup venv if missing
if [ ! -d "$APPDIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$APPDIR/.venv"
fi
source "$APPDIR/.venv/bin/activate"

# Install Python dependencies
echo "Installing Python packages..."
pip install -q -r "$APPDIR/requirements.txt"

# Make launch script executable
chmod +x "$APPDIR/launch.sh"

# Generate .desktop file with correct paths
mkdir -p "$REAL_HOME/.local/share/applications"
cat > "$REAL_HOME/.local/share/applications/jetdreamterminal.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=JetdreamTerminal
GenericName=Terminal Client
Comment=MobaXterm-like terminal for Linux (SSH, Telnet, SFTP, VPN, Serial, RDP)
Exec=$APPDIR/launch.sh
Icon=$ICON_FILE
Terminal=false
Categories=System;TerminalEmulator;
Keywords=terminal;ssh;sftp;telnet;vpn;serial;
StartupWMClass=JetdreamTerminal
EOF
echo "✓ Desktop entry installed"

# Install icon
mkdir -p "$REAL_HOME/.local/share/icons/hicolor/scalable/apps"
cp "$ICON_FILE" "$REAL_HOME/.local/share/icons/hicolor/scalable/apps/jetdreamterminal.svg"
gtk-update-icon-cache "$REAL_HOME/.local/share/icons/hicolor/" 2>/dev/null || true
echo "✓ Icon installed"

# Create symlink for easy launch
ln -sf "$APPDIR/launch.sh" "$REAL_HOME/bin/jetdreamterminal" 2>/dev/null || \
    echo "⚠ Could not create symlink (create ~/bin/ manually if needed)"
sudo ln -sf "$APPDIR/launch.sh" /usr/local/bin/jetdreamterminal 2>/dev/null || true

# Create desktop shortcut
mkdir -p "$REAL_HOME/Desktop"
cat > "$REAL_HOME/Desktop/jetdreamterminal.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=JetdreamTerminal
GenericName=Terminal Client
Comment=MobaXterm-like terminal for Linux (SSH, Telnet, SFTP, VPN, Serial, RDP)
Exec=$APPDIR/launch.sh
Icon=$ICON_FILE
Terminal=false
Categories=System;TerminalEmulator;
Keywords=terminal;ssh;sftp;telnet;vpn;serial;
StartupWMClass=JetdreamTerminal
EOF
chmod +x "$REAL_HOME/Desktop/jetdreamterminal.desktop" 2>/dev/null
gio set "$REAL_HOME/Desktop/jetdreamterminal.desktop" metadata::trusted true 2>/dev/null && \
    echo "✓ Desktop shortcut created" || echo "⚠ No Desktop folder"

echo ""
echo "=== Done! ==="
echo "Launch from: Applications menu → JetdreamTerminal"
echo "Or run: jetdreamterminal"
echo "Or run: $APPDIR/launch.sh"
