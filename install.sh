#!/bin/bash
set -e

APPDIR="/home/jetdream/HHD-Dream/JetdreamTerminal"
DESKTOP_FILE="$APPDIR/assets/jetdreamterminal.desktop"
ICON_FILE="$APPDIR/assets/icon.svg"

echo "=== Installing JetdreamTerminal ==="

# Make launch script executable
chmod +x "$APPDIR/launch.sh"

# Install .desktop file
mkdir -p ~/.local/share/applications
cp "$DESKTOP_FILE" ~/.local/share/applications/
echo "✓ Desktop entry installed"

# Install icon
mkdir -p ~/.local/share/icons/hicolor/scalable/apps
cp "$ICON_FILE" ~/.local/share/icons/hicolor/scalable/apps/jetdreamterminal.svg
gtk-update-icon-cache ~/.local/share/icons/hicolor/ 2>/dev/null || true
echo "✓ Icon installed"

# Create symlink for easy launch
sudo ln -sf "$APPDIR/launch.sh" /usr/local/bin/jetdreamterminal 2>/dev/null || \
    ln -sf "$APPDIR/launch.sh" ~/bin/jetdreamterminal 2>/dev/null || \
    echo "⚠ Could not create symlink (create ~/bin/ manually if needed)"

# Create desktop shortcut
cp "$DESKTOP_FILE" ~/Desktop/jetdreamterminal.desktop 2>/dev/null && \
    chmod +x ~/Desktop/jetdreamterminal.desktop && \
    echo "✓ Desktop shortcut created" || echo "⚠ No Desktop folder"

echo ""
echo "=== Done! ==="
echo "Launch from: Applications menu → JetdreamTerminal"
echo "Or run: jetdreamterminal"
echo "Or run: $APPDIR/launch.sh"
