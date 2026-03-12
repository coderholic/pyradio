#!/bin/bash
set -euo pipefail

APP_NAME="PyRadio"
PNG_ICON="pyradio-1024.png"

APP_DIR="${APP_NAME}.app"
CONTENTS_DIR="${APP_DIR}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

ICONSET_DIR="${APP_NAME}.iconset"
ICNS_FILE="${APP_NAME}.icns"
ARCHIVE_FILE="${APP_NAME}_mac_app.tar.gz"

echo "---------------------------------------"
echo "Building PyRadio macOS launcher bundle"
echo "---------------------------------------"

if [[ ! -f "$PNG_ICON" ]]; then
    echo "Error: $PNG_ICON not found"
    echo "Expected a 1024x1024 PNG file"
    exit 1
fi

echo
echo "Cleaning previous build..."
rm -rf "$APP_DIR" "$ICONSET_DIR" "$ICNS_FILE" "$ARCHIVE_FILE"

echo
echo "Creating iconset..."
mkdir -p "$ICONSET_DIR"

sips -z 16 16     "$PNG_ICON" --out "$ICONSET_DIR/icon_16x16.png" > /dev/null
sips -z 32 32     "$PNG_ICON" --out "$ICONSET_DIR/icon_16x16@2x.png" > /dev/null
sips -z 32 32     "$PNG_ICON" --out "$ICONSET_DIR/icon_32x32.png" > /dev/null
sips -z 64 64     "$PNG_ICON" --out "$ICONSET_DIR/icon_32x32@2x.png" > /dev/null
sips -z 128 128   "$PNG_ICON" --out "$ICONSET_DIR/icon_128x128.png" > /dev/null
sips -z 256 256   "$PNG_ICON" --out "$ICONSET_DIR/icon_128x128@2x.png" > /dev/null
sips -z 256 256   "$PNG_ICON" --out "$ICONSET_DIR/icon_256x256.png" > /dev/null
sips -z 512 512   "$PNG_ICON" --out "$ICONSET_DIR/icon_256x256@2x.png" > /dev/null
sips -z 512 512   "$PNG_ICON" --out "$ICONSET_DIR/icon_512x512.png" > /dev/null
cp "$PNG_ICON" "$ICONSET_DIR/icon_512x512@2x.png"

echo
echo "Building icns..."
iconutil -c icns "$ICONSET_DIR" -o "$ICNS_FILE"
rm -rf "$ICONSET_DIR"

echo
echo "Creating app bundle..."
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR"

cp "$ICNS_FILE" "$RESOURCES_DIR/PyRadio.icns"

echo
echo "Writing Info.plist..."
cat > "$CONTENTS_DIR/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>PyRadio</string>

    <key>CFBundleDisplayName</key>
    <string>PyRadio</string>

    <key>CFBundleIdentifier</key>
    <string>org.pyradio.pyradio</string>

    <key>CFBundleVersion</key>
    <string>1.0</string>

    <key>CFBundleShortVersionString</key>
    <string>1.0</string>

    <key>CFBundleExecutable</key>
    <string>PyRadio</string>

    <key>CFBundlePackageType</key>
    <string>APPL</string>

    <key>CFBundleIconFile</key>
    <string>PyRadio.icns</string>

    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>

    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

echo
echo "Creating launcher..."
cat > "$MACOS_DIR/PyRadio" <<'EOF'
#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMMAND_FILE="$APP_DIR/Resources/PyRadio.command"

if [[ ! -f "$COMMAND_FILE" ]]; then
    echo "PyRadio.command not found: $COMMAND_FILE" >&2
    exit 1
fi

exec /usr/bin/open -a Terminal "$COMMAND_FILE"
EOF

echo
echo "Creating command file..."
cat > "$RESOURCES_DIR/PyRadio.command" <<'EOF'
#!/bin/bash
set -euo pipefail

PYRADIO="$HOME/.local/bin/pyradio"

if [[ ! -x "$PYRADIO" ]]; then
    echo "PyRadio not found at: $PYRADIO"
    echo
    read -r -n 1 -p "Press any key to close..."
    echo
    exit 1
fi

printf '\033]0;PyRadio\007'
clear
exec "$PYRADIO"
EOF

chmod +x "$MACOS_DIR/PyRadio"
chmod +x "$RESOURCES_DIR/PyRadio.command"

echo
echo "Cleaning macOS metadata..."
xattr -cr "$APP_DIR" 2>/dev/null || true

echo
echo "Creating release archive..."
tar -cpzf "$ARCHIVE_FILE" "$APP_DIR"

echo
echo "---------------------------------------"
echo "Build complete"
echo
echo "Created:"
echo "  $ARCHIVE_FILE"
echo
echo "Contains:"
echo "  $APP_DIR"
echo
echo "Important:"
echo "  Replace any old PyRadio.app with the new one."
echo "  For Terminal auto-close, set Terminal:"
echo "  Settings -> Profiles -> Shell -> When the shell exits"
echo "  and choose:"
echo "  Close if the shell exited cleanly"
echo "---------------------------------------"
