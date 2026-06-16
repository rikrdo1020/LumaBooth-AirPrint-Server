import logging

from PIL import Image

logger = logging.getLogger(__name__)


class StarPrinter:
    """
    Wraps python-escpos to communicate with the Star mC-Print3.
    Reads connection settings from config each call so runtime changes take effect
    without restarting the container.
    """

    def __init__(self, config: dict):
        self.config = config
        self._printer = None

    def _connect(self):
        from escpos.printer import Network, Usb

        conn_cfg = self.config["printer"]
        conn_type = conn_cfg.get("connection_type", "ethernet")

        if conn_type == "ethernet":
            eth = conn_cfg["ethernet"]
            self._printer = Network(
                host=eth["host"],
                port=int(eth.get("port", 9100)),
                timeout=5,
            )
        elif conn_type == "usb":
            usb_cfg = conn_cfg["usb"]
            vid = int(str(usb_cfg["vendor_id"]), 16)
            pid = int(str(usb_cfg["product_id"]), 16)
            in_ep = int(str(usb_cfg.get("in_ep", "82")), 16)
            out_ep = int(str(usb_cfg.get("out_ep", "01")), 16)
            self._printer = Usb(
                idVendor=vid,
                idProduct=pid,
                timeout=5,
                in_ep=in_ep,
                out_ep=out_ep,
            )
        else:
            raise ValueError(f"Unknown connection_type: {conn_type!r}")

    def _close(self):
        if self._printer is not None:
            try:
                self._printer.close()
            except Exception:
                pass
            self._printer = None

    def print_image(self, pil_image: Image.Image) -> None:
        """Send a processed (1-bit) PIL Image to the thermal printer."""
        try:
            self._connect()
            # bitImageRaster (GS v) is preferred over bitImageColumn for mC-Print3 firmware
            self._printer.image(pil_image, impl="bitImageRaster")
            self._printer.cut()
            logger.info("Image printed successfully")
        except Exception:
            logger.exception("print_image failed")
            raise
        finally:
            self._close()

    def test_print(self, config: dict) -> None:  # noqa: ARG002 (config reserved for future use)
        """Print a text test page to verify connectivity."""
        try:
            self._connect()
            self._printer.set(align="center")
            self._printer.text("LumaBooth AirPrint Server\n")
            self._printer.text("Star mC-Print3\n")
            self._printer.text("-" * 32 + "\n")
            self._printer.text("Test print successful!\n")
            self._printer.text("-" * 32 + "\n\n")
            self._printer.cut()
            logger.info("Test print sent successfully")
        except Exception:
            logger.exception("test_print failed")
            raise
        finally:
            self._close()

    def get_status(self) -> dict:
        """Attempt connection; return connectivity status dict."""
        try:
            self._connect()
            return {"connected": True, "status": "online"}
        except Exception as exc:
            return {"connected": False, "error": str(exc)}
        finally:
            self._close()
