SSID     ?= LumaBooth
PASSWORD ?= lumabooth123

# ── First-time setup ─────────────────────────────────────────────────────────

.PHONY: setup
setup:          ## Full Pi setup: hotspot + Docker + start server (run once)
	@bash scripts/setup-pi.sh

# ── Hotspot ──────────────────────────────────────────────────────────────────

.PHONY: hotspot
hotspot:        ## (Re)configure the Wi-Fi hotspot
	@echo "[hotspot] Configuring SSID=$(SSID)..."
	@if nmcli connection show "LumaBooth-Hotspot" &>/dev/null; then \
	    sudo nmcli connection delete "LumaBooth-Hotspot"; \
	fi
	@sudo nmcli device wifi hotspot \
	    ifname wlan0 \
	    con-name "LumaBooth-Hotspot" \
	    ssid "$(SSID)" \
	    password "$(PASSWORD)"
	@sudo nmcli connection modify "LumaBooth-Hotspot" \
	    connection.autoconnect yes \
	    connection.autoconnect-priority 10
	@echo "[hotspot] ✓ SSID: $(SSID) | Password: $(PASSWORD) | Pi IP: 10.42.0.1"

# ── Server lifecycle ─────────────────────────────────────────────────────────

.PHONY: start
start:          ## Start the server (build if needed)
	docker compose up --build -d

.PHONY: stop
stop:           ## Stop the server
	docker compose down

.PHONY: restart
restart:        ## Restart the server
	docker compose restart

.PHONY: rebuild
rebuild:        ## Force full image rebuild and restart
	docker compose up --build --force-recreate -d

# ── Observability ─────────────────────────────────────────────────────────────

.PHONY: logs
logs:           ## Stream container logs
	docker compose logs -f

.PHONY: status
status:         ## Show container and printer queue status
	@echo "=== Container ==="
	@docker compose ps
	@echo ""
	@echo "=== Printer queue ==="
	@docker compose exec airprint-server lpstat -p LumaBooth-Thermal 2>/dev/null || echo "(container not running)"
	@echo ""
	@echo "=== Hotspot ==="
	@nmcli connection show "LumaBooth-Hotspot" 2>/dev/null | grep -E "connection\.(id|autoconnect)|802-11-wireless\." || echo "(hotspot not configured)"

.PHONY: printer-ip
printer-ip:     ## Show IPs of devices connected to the hotspot (find printer IP)
	@echo "=== Devices on hotspot network ==="
	@arp -a | grep -v incomplete || ip neigh show

# ── Help ──────────────────────────────────────────────────────────────────────

.PHONY: help
help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' Makefile | awk 'BEGIN {FS = ":.*##"}; {printf "  %-14s %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
