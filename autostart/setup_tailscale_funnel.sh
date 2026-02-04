#!/bin/bash
# Setup Tailscale Funnel to auto-start on boot
# Run this once on DW4 to enable public HTTPS access on every boot

set -e

echo "======================================================================"
echo "🐉 Dragon Wings - Tailscale Funnel Auto-Start Setup"
echo "======================================================================"
echo ""

PLIST_PATH="/Library/LaunchDaemons/com.dragonwings.tailscale-funnel.plist"

# Check if already exists
if [ -f "$PLIST_PATH" ]; then
    echo "⚠️  LaunchDaemon already exists at $PLIST_PATH"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled"
        exit 0
    fi

    # Unload existing
    sudo launchctl unload "$PLIST_PATH" 2>/dev/null || true
fi

# Create the plist file
echo "📝 Creating LaunchDaemon plist..."
sudo tee "$PLIST_PATH" > /dev/null <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dragonwings.tailscale-funnel</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Tailscale.app/Contents/MacOS/Tailscale</string>
        <string>funnel</string>
        <string>--bg</string>
        <string>3000</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/opt/dragon/logs/tailscale_funnel.log</string>

    <key>StandardErrorPath</key>
    <string>/opt/dragon/logs/tailscale_funnel_error.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# Set correct permissions
echo "🔒 Setting permissions..."
sudo chown root:wheel "$PLIST_PATH"
sudo chmod 644 "$PLIST_PATH"

# Load the launch daemon
echo "🚀 Loading LaunchDaemon..."
sudo launchctl load "$PLIST_PATH"

# Wait a moment for it to start
sleep 2

# Verify it's running
echo ""
echo "======================================================================"
echo "✅ Tailscale Funnel Auto-Start Configured!"
echo "======================================================================"
echo ""
echo "Verification:"
sudo launchctl list | grep tailscale-funnel && echo "  ✅ LaunchDaemon loaded" || echo "  ❌ LaunchDaemon not found"

echo ""
echo "Public URL:"
echo "  https://dwingss-mac-mini-2.tail624919.ts.net/"
echo ""
echo "Logs:"
echo "  stdout: /opt/dragon/logs/tailscale_funnel.log"
echo "  stderr: /opt/dragon/logs/tailscale_funnel_error.log"
echo ""
echo "To disable:"
echo "  sudo launchctl unload $PLIST_PATH"
echo ""
echo "Tailscale Funnel will now start automatically on every boot!"
echo "======================================================================"
