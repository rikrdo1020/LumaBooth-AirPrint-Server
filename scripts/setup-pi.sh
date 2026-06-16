#!/bin/bash
# LumaBooth AirPrint Server — Raspberry Pi first-time setup
# Run once after cloning the project on the Pi.
set -euo pipefail

SSID="${LUMABOOTH_SSID:-LumaBooth}"
PASSWORD="${LUMABOOTH_PASSWORD:-lumabooth123}"
IFACE="${LUMABOOTH_IFACE:-wlan0}"

log()  { echo "[setup] $*"; }
ok()   { echo "[setup] ✓ $*"; }
fail() { echo "[setup] ✗ $*" >&2; exit 1; }

# --------------------------------------------------------------------------- #
# 1. Docker
# --------------------------------------------------------------------------- #
if ! command -v docker &>/dev/null; then
    log "Docker not found — installing..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    ok "Docker installed. You will need to log out and back in for group membership to take effect."
    NEED_RELOGIN=1
else
    ok "Docker already installed ($(docker --version | cut -d' ' -f3 | tr -d ','))"
    NEED_RELOGIN=0
fi

# --------------------------------------------------------------------------- #
# 2. Wi-Fi Hotspot
# --------------------------------------------------------------------------- #
if ! command -v nmcli &>/dev/null; then
    fail "NetworkManager (nmcli) is not available. Install it with: sudo apt install network-manager"
fi

log "Configuring Wi-Fi hotspot (SSID: $SSID) on $IFACE..."

# Remove any previous hotspot connection to avoid duplicates
if nmcli connection show "LumaBooth-Hotspot" &>/dev/null; then
    log "Removing existing hotspot connection..."
    sudo nmcli connection delete "LumaBooth-Hotspot"
fi

sudo nmcli device wifi hotspot \
    ifname "$IFACE" \
    con-name "LumaBooth-Hotspot" \
    ssid "$SSID" \
    password "$PASSWORD"

sudo nmcli connection modify "LumaBooth-Hotspot" \
    connection.autoconnect yes \
    connection.autoconnect-priority 10

ok "Hotspot configured — SSID: $SSID | Password: $PASSWORD"
ok "Pi IP on hotspot network: 10.42.0.1"

# --------------------------------------------------------------------------- #
# 3. Start the server
# --------------------------------------------------------------------------- #
log "Starting LumaBooth AirPrint Server..."
docker compose up --build -d
ok "Server started."

# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  LumaBooth AirPrint Server is running!"
echo ""
echo "  Wi-Fi:        $SSID  (password: $PASSWORD)"
echo "  Web UI:       http://10.42.0.1:8080"
echo "  CUPS:         http://10.42.0.1:631"
echo ""
echo "  Connect iPad to '$SSID' Wi-Fi, then open"
echo "  LumaBooth → Settings → Print Settings."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "${NEED_RELOGIN:-0}" = "1" ]; then
    echo ""
    echo "  NOTE: Log out and back in so Docker group takes effect,"
    echo "  then run 'make start' to restart the server."
fi
