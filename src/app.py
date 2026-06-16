import base64
import io
import logging
import subprocess
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request
from PIL import Image

from src.config_manager import load_config, save_config
from src.image_processor import process_image
from src.printer import StarPrinter

logger = logging.getLogger(__name__)

SAMPLE_IMAGE_PATH = Path("/app/assets/sample.jpg")
TEMPLATES_PATH = Path("/app/templates")


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATES_PATH))

    # ----------------------------------------------------------------------- #
    # Web UI
    # ----------------------------------------------------------------------- #

    @app.route("/")
    def index():
        return render_template("index.html")

    # ----------------------------------------------------------------------- #
    # Config API
    # ----------------------------------------------------------------------- #

    @app.route("/api/config", methods=["GET"])
    def get_config():
        return jsonify(load_config())

    @app.route("/api/config", methods=["POST"])
    def post_config():
        data = request.get_json(force=True, silent=True)
        if not data:
            abort(400, "No JSON body provided")
        save_config(data)
        return jsonify({"status": "saved"})

    # ----------------------------------------------------------------------- #
    # Test print
    # ----------------------------------------------------------------------- #

    @app.route("/api/test-print", methods=["POST"])
    def test_print():
        config = load_config()
        try:
            StarPrinter(config).test_print(config)
            return jsonify({"status": "ok", "message": "Test print sent"})
        except Exception as exc:
            logger.exception("test_print error")
            return jsonify({"status": "error", "message": str(exc)}), 500

    # ----------------------------------------------------------------------- #
    # Live preview
    # ----------------------------------------------------------------------- #

    @app.route("/api/preview", methods=["GET", "POST"])
    def preview():
        """
        GET  — process sample image with current saved config.
        POST — process sample image with config from request body (unsaved).
        Returns {original: <base64-png>, processed: <base64-png>}.
        """
        if request.method == "POST":
            body = request.get_json(force=True, silent=True) or {}
            config = body if body else load_config()
        else:
            config = load_config()

        try:
            original = Image.open(SAMPLE_IMAGE_PATH)
            original.load()
            processed = process_image(original, config)

            return jsonify(
                {
                    "original": _img_to_b64(original, max_width=400),
                    "processed": _img_to_b64(processed, max_width=400),
                }
            )
        except Exception as exc:
            logger.exception("preview error")
            return jsonify({"error": str(exc)}), 500

    # ----------------------------------------------------------------------- #
    # Status
    # ----------------------------------------------------------------------- #

    @app.route("/api/status", methods=["GET"])
    def status():
        config = load_config()
        printer_name = config.get("cups", {}).get("printer_name", "LumaBooth-Thermal")

        cups_result = subprocess.run(
            ["lpstat", "-p", printer_name],
            capture_output=True,
            text=True,
        )
        cups_ok = cups_result.returncode == 0
        cups_info = (cups_result.stdout or cups_result.stderr).strip()

        printer_status = StarPrinter(config).get_status()

        return jsonify(
            {
                "cups": {"ok": cups_ok, "info": cups_info},
                "printer": printer_status,
            }
        )

    return app


def _img_to_b64(img: Image.Image, max_width: int = 400) -> str:
    """Resize for browser display and encode as base64 PNG."""
    if img.width > max_width:
        ratio = max_width / img.width
        new_h = max(1, int(img.height * ratio))
        img = img.resize((max_width, new_h), Image.NEAREST)
    buf = io.BytesIO()
    # Convert 1-bit images to L for PNG encoding (avoids palette issues)
    save_img = img.convert("L") if img.mode == "1" else img
    save_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")
