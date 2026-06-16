# LumaBooth AirPrint Server

Docker-based middleware that bridges an iPad running LumaBooth (photobooth app) to a **Star mC-Print3** thermal printer via AirPrint.

**How it works:** The container announces itself as an AirPrint printer on the local network. When LumaBooth prints, CUPS receives the job, processes the image through a thermal-optimised pipeline (grayscale → auto-contrast → brightness/contrast → sharpening → dithering → scale to paper width), then sends ESC/POS commands to the Star printer.

---

## Requirements

| Component | Minimum version |
|-----------|----------------|
| Docker | 24+ |
| Docker Compose | v2 (`docker compose`) |
| Docker Buildx | bundled with Docker Desktop / Docker CE 23+ |

The same `docker-compose.yml` works on **amd64** (dev) and **arm64** (Raspberry Pi 4B) without modification.

---

## Quick Start — Development (x86_64)

```bash
# 1. Clone the repository
git clone <repo-url> lumabooth-airprint-server
cd lumabooth-airprint-server

# 2. Build and start (first run takes a few minutes)
docker compose up --build

# 3. Open the web UI
open http://localhost:8080

# 4. Set the printer IP under "Printer Connection" and click "Test Print"
```

CUPS web interface: http://localhost:631

---

## Raspberry Pi 4B — Headless Setup

### Step 1 — Flash SD Card

Use the **Raspberry Pi Imager** to flash **Raspberry Pi OS Lite (64-bit)** (the 64-bit variant is required for arm64 Docker images).

In the imager's advanced options, configure:
- Hostname: `raspberrypi` (or your preferred name)
- Enable SSH
- Set Wi-Fi credentials (if not using Ethernet)

### Step 2 — Boot and SSH In

```bash
ssh pi@raspberrypi.local
```

### Step 3 — Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in so group membership takes effect
exit
ssh pi@raspberrypi.local
```

Verify: `docker run --rm hello-world`

### Step 4 — Clone and Start

```bash
git clone <repo-url> lumabooth-airprint-server
cd lumabooth-airprint-server

# First-time setup: configures hotspot + Docker + starts the server
make setup
```

That's it. See all available commands:

```bash
make help
```

| Command | What it does |
|---------|-------------|
| `make setup` | First-time setup: hotspot + Docker + start server |
| `make hotspot` | Reconfigure the Wi-Fi hotspot (custom SSID/password) |
| `make start` | Start the server |
| `make stop` | Stop the server |
| `make restart` | Restart the server |
| `make logs` | Stream container logs |
| `make status` | Container + printer queue + hotspot status |
| `make printer-ip` | Show IPs of devices on the hotspot (find printer IP) |

To use a custom SSID or password:

```bash
make setup SSID="MiRed" PASSWORD="mipassword123"
# or just the hotspot:
make hotspot SSID="MiRed" PASSWORD="mipassword123"
```

The container starts automatically on every reboot because of `restart: unless-stopped`.

### Step 5 — Open Web UI from Any Device on the Same Network

```
http://raspberrypi.local:8080
```

---

## Router-Free Setup — Raspberry Pi as Wi-Fi Hotspot

If you don't have a router at the event venue, the Pi can create its own Wi-Fi network. The iPad connects directly to the Pi's hotspot; the Star printer connects via Ethernet to the Pi.

```
iPad ──── Wi-Fi ──── Raspberry Pi (AP, 10.42.0.1)
                          │
                     Ethernet
                          │
                    Star mC-Print3
```

### Create the Hotspot

```bash
# SSH into the Pi, then run:
sudo nmcli device wifi hotspot \
  ifname wlan0 \
  ssid "LumaBooth" \
  password "lumabooth123"

# Make it start automatically on every boot
sudo nmcli connection modify Hotspot \
  connection.autoconnect yes \
  connection.autoconnect-priority 10
```

The Pi's IP on this network is always `10.42.0.1`. Connected devices receive IPs in the `10.42.0.x` range via DHCP.

### Find the Printer's IP

After plugging the Star mC-Print3 into the Pi's Ethernet port:

```bash
# Check which IP was assigned to the printer
ip neigh show
# or
arp -a
```

Then set that IP in the web UI at `http://10.42.0.1:8080` under **Printer Connection**.

### Access the Web UI Without a Router

| Resource | URL |
|----------|-----|
| Web config UI | `http://10.42.0.1:8080` |
| CUPS interface | `http://10.42.0.1:631` |

### iPad Connection

1. On the iPad, connect to Wi-Fi **"LumaBooth"**.
2. Open LumaBooth → **Settings → Print Settings → Select Printer**.
3. The printer appears automatically — mDNS works the same inside the hotspot network.

> **Tip:** This setup is more reliable at events than using the venue's Wi-Fi, which often blocks mDNS between devices.

---

## iPad / LumaBooth Setup

No app changes are needed. The printer is discovered automatically.

1. In LumaBooth, go to **Settings → Print Settings**.
2. Tap **Select Printer**.
3. Choose **"LumaBooth Thermal @ \<hostname\>"** from the list.
4. Print a test strip.

If the printer doesn't appear, ensure the iPad and the Pi/server are on the **same Wi-Fi network**.

---

## Configuration

All settings are stored in `config/settings.yaml` (created from defaults on first run). Edit via the web UI at port 8080, or directly:

```yaml
image_processing:
  dithering: atkinson          # atkinson | floyd_steinberg | bayer
  brightness: 0                # -50 to +50
  contrast: 0                  # -50 to +50
  sharpening:
    enabled: false
    intensity: 1.5             # 0.5 to 3.0
  paper_width_px: 576          # 576px = 80mm at 203dpi

printer:
  connection_type: ethernet    # ethernet | usb
  ethernet:
    host: 192.168.1.100        # Star mC-Print3 IP address
    port: 9100
  usb:
    vendor_id: "0519"          # Star Micronics VID
    product_id: "0003"         # mC-Print3 PID

cups:
  printer_name: LumaBooth-Thermal
  description: "Star mC-Print3 via LumaBooth AirPrint Server"
  location: "Photo Booth"
```

Changes saved via the web UI take effect on the next print job (no restart required).

---

## Multi-Architecture Build (for Distribution)

Build and push a single manifest for both platforms:

```bash
# One-time: set up a multi-platform builder
docker buildx create --use --name multiarch --driver docker-container
docker run --privileged --rm tonistiigi/binfmt --install all

# Build and push
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t yourregistry/lumabooth-airprint-server:latest \
  --push .
```

Then on the Pi, use the pre-built image:

```yaml
# docker-compose.yml — swap build: for image:
services:
  airprint-server:
    image: yourregistry/lumabooth-airprint-server:latest
```

---

## Logs

Container logs (Docker):
```bash
docker compose logs -f
```

Application logs on the host:
```
logs/gunicorn-access.log
logs/gunicorn-error.log
logs/cups-error.log
logs/cups-access.log
```

Log rotation is configured automatically (`max-size: 10m`, 3 files). On the Raspberry Pi this protects the SD card from wear.

---

## Troubleshooting

### AirPrint printer not appearing on iPad

1. Verify host network mode is active: the compose file must have `network_mode: host`.
2. Check Avahi is running inside the container:
   ```bash
   docker exec <container-id> avahi-browse -tr _ipp._tcp
   ```
   You should see `LumaBooth Thermal` with a `URF=` TXT record.
3. Confirm both the iPad and the server/Pi are on the same subnet.
4. Some managed Wi-Fi networks block mDNS. Try a direct Wi-Fi hotspot from the Pi for events.

### Job received but nothing prints

```bash
# Check the CUPS queue
docker exec <container-id> lpstat -p LumaBooth-Thermal

# Watch CUPS error log
docker exec <container-id> tail -f /var/log/lumabooth/cups-error.log
```

The CUPS filter logs prefix every line with `[lumabooth-filter]`.

### USB printer not detected

```bash
# List USB devices from inside the container
docker exec <container-id> lsusb | grep -i star
```

If the device is missing, ensure the `devices:` entry in `docker-compose.yml` is present and the user has permission to access `/dev/bus/usb` on the host (add to `plugdev` group on Linux).

### Printer rejects the image / blank output

- Try switching the dithering algorithm in the web UI — **Atkinson** works best for photos.
- Increase contrast (+15 to +25) if the print is too light.
- Verify `paper_width_px` matches the printer's configured paper width (576px = 80mm, 832px = 112mm).

### Out of memory on Raspberry Pi

- Reduce Gunicorn workers in `entrypoint.sh` from 2 to 1.
- Enable the Pi GPU memory split reduction: `gpu_mem=16` in `/boot/config.txt`.

---

## Project Structure

```
lumabooth-airprint-server/
├── Dockerfile              Multi-arch Docker image (amd64 + arm64)
├── docker-compose.yml      Orchestration (host network, volumes, log rotation)
├── requirements.txt        Python dependencies
├── config/
│   └── defaults.yaml       Default settings (copied to /config on first run)
├── avahi/
│   └── airprint.service    Avahi mDNS advertisement for AirPrint
├── cups/
│   ├── cupsd.conf          CUPS server configuration
│   ├── lumabooth.ppd       PPD file for the virtual printer queue
│   ├── mime.types          MIME type registrations (adds image/urf)
│   └── mime.convs          Filter routing rules
├── scripts/
│   ├── entrypoint.sh       Container startup sequence
│   └── generate_sample.py  Generates sample.jpg during Docker build
├── src/
│   ├── config_manager.py   YAML config load/save
│   ├── image_processor.py  Grayscale + dithering pipeline
│   ├── printer.py          ESC/POS communication (python-escpos)
│   ├── cups_filter.py      CUPS filter executable
│   └── app.py              Flask web application
└── templates/
    └── index.html          Web config UI (vanilla JS, no build step)
```
#   L u m a B o o t h - A i r P r i n t - S e r v e r  
 