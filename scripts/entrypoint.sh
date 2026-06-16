#!/bin/bash
# LumaBooth AirPrint Server — container entrypoint
# Starts D-Bus → Avahi → CUPS → Flask/Gunicorn in the correct order.
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/config/settings.yaml}"
DEFAULTS_PATH="${DEFAULTS_PATH:-/app/config/defaults.yaml}"
PRINTER_NAME="LumaBooth-Thermal"
LOG_DIR="/var/log/lumabooth"

log() { echo "[entrypoint] $*"; }

# --------------------------------------------------------------------------- #
# 1. Bootstrap persistent config
# --------------------------------------------------------------------------- #
if [ ! -f "$CONFIG_PATH" ]; then
    log "No settings.yaml found — copying defaults..."
    mkdir -p "$(dirname "$CONFIG_PATH")"
    cp "$DEFAULTS_PATH" "$CONFIG_PATH"
fi

# --------------------------------------------------------------------------- #
# 2. Create log directory
# --------------------------------------------------------------------------- #
mkdir -p "$LOG_DIR"

# --------------------------------------------------------------------------- #
# 3. Start D-Bus (required by Avahi)
# --------------------------------------------------------------------------- #
log "Starting D-Bus..."
mkdir -p /run/dbus
dbus-daemon --system --fork
sleep 1

# --------------------------------------------------------------------------- #
# 4. Start Avahi
# --------------------------------------------------------------------------- #
log "Starting Avahi daemon..."
avahi-daemon --daemonize --no-drop-root
sleep 1

# --------------------------------------------------------------------------- #
# 5. Start CUPS
# --------------------------------------------------------------------------- #
log "Starting CUPS..."
mkdir -p /run/cups
cupsd

# Wait until the CUPS Unix socket is ready before calling lpadmin
log "Waiting for CUPS socket..."
for i in $(seq 1 30); do
    [ -S /run/cups/cups.sock ] && break
    sleep 1
done
if [ ! -S /run/cups/cups.sock ]; then
    log "ERROR: CUPS socket never appeared. Aborting."
    exit 1
fi
log "CUPS is ready."

# --------------------------------------------------------------------------- #
# 6. Create the printer queue (idempotent)
#    Backend URI: file:///dev/null (built-in CUPS null backend).
#    The lumabooth-filter handles all actual printer communication.
# --------------------------------------------------------------------------- #
if ! lpstat -p "$PRINTER_NAME" > /dev/null 2>&1; then
    log "Creating printer queue: $PRINTER_NAME"
    lpadmin \
        -p "$PRINTER_NAME" \
        -E \
        -v "file:///dev/null" \
        -P /etc/cups/ppd/lumabooth.ppd \
        -o printer-is-shared=true \
        -D "Star mC-Print3 via LumaBooth AirPrint Server" \
        -L "Photo Booth"
    lpoptions -d "$PRINTER_NAME"
    log "Printer queue created."
else
    log "Printer queue $PRINTER_NAME already exists — skipping."
fi

# --------------------------------------------------------------------------- #
# 7. Launch Gunicorn (replaces the shell so it becomes PID 1 → clean SIGTERM)
# --------------------------------------------------------------------------- #
log "Starting web application on port 8080..."
exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --timeout 120 \
    --access-logfile "$LOG_DIR/gunicorn-access.log" \
    --error-logfile  "$LOG_DIR/gunicorn-error.log" \
    --log-level info \
    "src.app:create_app()"
