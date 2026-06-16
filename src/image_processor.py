import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageOps


def pdf_to_image(pdf_path: str, dpi: int = 203) -> Image.Image:
    """Convert first page of a PDF to a PIL Image using Ghostscript."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            [
                "gs",
                "-dNOPAUSE",
                "-dBATCH",
                "-dSAFER",
                "-sDEVICE=png16m",
                f"-r{dpi}",
                "-dFirstPage=1",
                "-dLastPage=1",
                f"-sOutputFile={tmp_path}",
                pdf_path,
            ],
            check=True,
            capture_output=True,
        )
        img = Image.open(tmp_path)
        img.load()
        return img
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def convert_to_grayscale(image: Image.Image) -> Image.Image:
    return image.convert("L")


def auto_contrast(image: Image.Image) -> Image.Image:
    return ImageOps.autocontrast(image, cutoff=1)


def apply_brightness_contrast(
    image: Image.Image, brightness: int, contrast: int
) -> Image.Image:
    """Map -50..+50 integer values to PIL enhancer factors (0.0–2.0)."""
    if brightness != 0:
        factor = 1.0 + (brightness / 50.0)
        image = ImageEnhance.Brightness(image).enhance(factor)
    if contrast != 0:
        factor = 1.0 + (contrast / 50.0)
        image = ImageEnhance.Contrast(image).enhance(factor)
    return image


def apply_sharpening(
    image: Image.Image, enabled: bool, intensity: float
) -> Image.Image:
    if not enabled:
        return image
    return ImageEnhance.Sharpness(image).enhance(intensity)


def scale_to_paper_width(image: Image.Image, width_px: int = 576) -> Image.Image:
    if image.width == width_px:
        return image
    ratio = width_px / image.width
    new_height = max(1, int(image.height * ratio))
    return image.resize((width_px, new_height), Image.LANCZOS)


def atkinson_dither(image: Image.Image) -> Image.Image:
    """
    Atkinson dithering: distributes 6/8 of the error to 6 neighbors.
    Produces crisper output than Floyd-Steinberg — good for photos with text.
    """
    img = np.array(image, dtype=np.float32)
    h, w = img.shape
    for y in range(h):
        for x in range(w):
            old = img[y, x]
            new = 255.0 if old > 127.0 else 0.0
            img[y, x] = new
            err = (old - new) / 8.0
            for dy, dx in [(0, 1), (0, 2), (1, -1), (1, 0), (1, 1), (2, 0)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    img[ny, nx] += err
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("1")


def floyd_steinberg_dither(image: Image.Image) -> Image.Image:
    """
    Floyd-Steinberg dithering: distributes full error to 4 neighbors.
    Smoother gradients — better for photographic content.
    """
    img = np.array(image, dtype=np.float32)
    h, w = img.shape
    for y in range(h):
        for x in range(w):
            old = img[y, x]
            new = 255.0 if old > 127.0 else 0.0
            img[y, x] = new
            err = old - new
            if x + 1 < w:
                img[y, x + 1] += err * 7 / 16
            if y + 1 < h:
                if x > 0:
                    img[y + 1, x - 1] += err * 3 / 16
                img[y + 1, x] += err * 5 / 16
                if x + 1 < w:
                    img[y + 1, x + 1] += err * 1 / 16
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("1")


def ordered_bayer_dither(image: Image.Image, matrix_size: int = 4) -> Image.Image:
    """
    Bayer ordered dithering: fast, no error diffusion, characteristic crosshatch pattern.
    Uses a 4×4 Bayer matrix tiled across the image.
    """
    BAYER_4x4 = np.array(
        [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]],
        dtype=np.float32,
    ) / 16.0

    img = np.array(image, dtype=np.float32) / 255.0
    h, w = img.shape
    matrix = np.tile(BAYER_4x4, (h // 4 + 1, w // 4 + 1))[:h, :w]
    result = (img > matrix).astype(np.uint8) * 255
    return Image.fromarray(result).convert("1")


def process_image(pil_image: Image.Image, config: dict) -> Image.Image:
    """
    Full thermal-print processing pipeline.
    Returns a 1-bit PIL Image ready for ESC/POS printing.
    """
    proc = config["image_processing"]
    img = convert_to_grayscale(pil_image)
    img = auto_contrast(img)
    img = apply_brightness_contrast(img, proc.get("brightness", 0), proc.get("contrast", 0))
    sharpening = proc.get("sharpening", {})
    img = apply_sharpening(
        img,
        sharpening.get("enabled", False),
        sharpening.get("intensity", 1.5),
    )
    img = scale_to_paper_width(img, proc.get("paper_width_px", 576))

    algo = proc.get("dithering", "atkinson")
    if algo == "floyd_steinberg":
        return floyd_steinberg_dither(img)
    elif algo == "bayer":
        return ordered_bayer_dither(img, proc.get("bayer_matrix_size", 4))
    else:
        return atkinson_dither(img)
