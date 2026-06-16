# python:3.11-slim is Debian Bookworm slim and ships both linux/amd64 and
# linux/arm64 manifest entries — no QEMU emulation needed at runtime on the Pi.
FROM python:3.11-slim

# --------------------------------------------------------------------------- #
# System dependencies — single RUN layer to keep image size minimal
# --------------------------------------------------------------------------- #
RUN apt-get update && apt-get install -y --no-install-recommends \
        cups \
        cups-filters \
        cups-bsd \
        avahi-daemon \
        avahi-utils \
        ghostscript \
        libusb-1.0-0 \
        poppler-utils \
        usbutils \
        dbus \
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------- #
# Python dependencies
# --------------------------------------------------------------------------- #
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# --------------------------------------------------------------------------- #
# CUPS filter — must be root:root 0755 in the CUPS filter directory
# --------------------------------------------------------------------------- #
COPY src/cups_filter.py /usr/lib/cups/filter/lumabooth-filter
RUN chmod 0755 /usr/lib/cups/filter/lumabooth-filter \
    && chown root:root /usr/lib/cups/filter/lumabooth-filter

# --------------------------------------------------------------------------- #
# CUPS configuration
# --------------------------------------------------------------------------- #
COPY cups/cupsd.conf  /etc/cups/cupsd.conf
COPY cups/lumabooth.ppd /etc/cups/ppd/lumabooth.ppd
COPY cups/mime.types  /etc/cups/mime.types
COPY cups/mime.convs  /etc/cups/mime.convs

# --------------------------------------------------------------------------- #
# Avahi AirPrint service advertisement
# --------------------------------------------------------------------------- #
COPY avahi/airprint.service /etc/avahi/services/airprint.service

# --------------------------------------------------------------------------- #
# Application source, templates, and default config
# --------------------------------------------------------------------------- #
COPY src/        /app/src/
COPY templates/  /app/templates/
COPY config/     /app/config/

# --------------------------------------------------------------------------- #
# Generate the bundled sample image (requires Pillow, already installed above)
# --------------------------------------------------------------------------- #
COPY scripts/generate_sample.py /tmp/generate_sample.py
RUN python /tmp/generate_sample.py

# --------------------------------------------------------------------------- #
# Entrypoint
# --------------------------------------------------------------------------- #
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app

# CUPS web interface (631) and LumaBooth web config UI (8080)
EXPOSE 631 8080

ENTRYPOINT ["/entrypoint.sh"]
