#!/usr/bin/env python3
"""
CUPS filter for LumaBooth thermal printer.

CUPS calls this executable as:
    lumabooth-filter job-id user title copies options [filename]

stdin carries the job data when no filename argument is provided.
All progress/diagnostic output MUST go to stderr — stdout is the CUPS data pipeline.
Exit 0 on success, non-zero on failure.
"""
import logging
import os
import sys
import tempfile
from pathlib import Path

# Add /app to path so relative imports work when called by CUPS as a subprocess
sys.path.insert(0, "/app")

from src.config_manager import load_config
from src.image_processor import pdf_to_image, process_image
from src.printer import StarPrinter
from PIL import Image

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(levelname)s [lumabooth-filter]: %(message)s",
)
logger = logging.getLogger("lumabooth-filter")


def _is_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"%PDF"
    except OSError:
        return False


def _notice(msg: str) -> None:
    """Send a CUPS progress notice to the scheduler."""
    print(f"NOTICE: {msg}", file=sys.stderr, flush=True)


def main() -> int:
    if len(sys.argv) < 6:
        logger.error(
            "Usage: lumabooth-filter job-id user title copies options [filename]"
        )
        return 1

    job_id = sys.argv[1]
    user = sys.argv[2]
    title = sys.argv[3]
    copies = max(1, int(sys.argv[4]))
    # sys.argv[5] = options string (not currently used; settings come from YAML)
    filename = sys.argv[6] if len(sys.argv) > 6 else None

    logger.info(f"Job {job_id!r} — '{title}' from {user!r}, copies={copies}")

    tmp_input: str | None = None

    try:
        # ------------------------------------------------------------------ #
        # 1. Acquire input data
        # ------------------------------------------------------------------ #
        if filename and os.path.exists(filename):
            input_path = filename
        else:
            # CUPS passes data via stdin when no filename argument is given
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dat") as tmp:
                tmp.write(sys.stdin.buffer.read())
                tmp_input = input_path = tmp.name

        # ------------------------------------------------------------------ #
        # 2. Decode to PIL Image
        # ------------------------------------------------------------------ #
        _notice("Loading image")
        if _is_pdf(input_path):
            logger.info("Detected PDF input — converting via Ghostscript")
            pil_image = pdf_to_image(input_path, dpi=203)
        else:
            try:
                pil_image = Image.open(input_path)
                pil_image.load()
            except Exception as exc:
                logger.error(f"Cannot open as image: {exc}")
                return 1

        # ------------------------------------------------------------------ #
        # 3. Process through the thermal pipeline
        # ------------------------------------------------------------------ #
        _notice("Processing image")
        config = load_config()
        processed = process_image(pil_image, config)

        # ------------------------------------------------------------------ #
        # 4. Send to printer (one connection per copy to avoid timeout issues)
        # ------------------------------------------------------------------ #
        _notice("Sending to printer")
        printer = StarPrinter(config)
        for i in range(copies):
            logger.info(f"Printing copy {i + 1}/{copies}")
            printer.print_image(processed)

        _notice("Done")
        logger.info(f"Job {job_id!r} completed successfully")
        return 0

    except Exception:
        logger.exception(f"Unhandled error processing job {job_id!r}")
        return 1

    finally:
        if tmp_input and os.path.exists(tmp_input):
            os.unlink(tmp_input)


if __name__ == "__main__":
    sys.exit(main())
