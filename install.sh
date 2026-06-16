#!/bin/bash
set -e

APPDIR="$(cd "$(dirname "$0")" && pwd)"
ICON_FILE="$APPDIR/assets/icon.svg"
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(eval echo "~$REAL_USER")

echo "=== Installing JetdreamTerminal ==="

# Install system dependencies if missing
echo "Checking system dependencies..."
APT_PKGS=()
for pkg in libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
           libxcb-keysyms1 libxcb-render-util0 libxcb-shape0 \
           libxkbcommon-x11-0 sshpass tigervnc-viewer; do
    if ! dpkg -s "$pkg" &>/dev/null; then
        APT_PKGS+=("$pkg")
    fi
done

# Detect freerdp version (freerdp2-x11 on 22.04, freerdp3-x11 on 24.04+)
if dpkg -s freerdp3-x11 &>/dev/null 2>&1; then
    :  # already installed
elif dpkg -s freerdp2-x11 &>/dev/null 2>&1; then
    :  # already installed
else
    if apt-cache show freerdp3-x11 &>/dev/null 2>&1; then
        APT_PKGS+=(freerdp3-x11)
    elif apt-cache show freerdp2-x11 &>/dev/null 2>&1; then
        APT_PKGS+=(freerdp2-x11)
    fi
fi

if [ ${#APT_PKGS[@]} -gt 0 ]; then
    echo "Installing: ${APT_PKGS[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${APT_PKGS[@]}"
    echo "✓ System dependencies installed"
else
    echo "✓ All system dependencies present"
fi

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
