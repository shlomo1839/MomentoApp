"""Lightweight generator for a single, minimalist digital album page.

Picks 3 random images from ./input_images/, applies face/saliency-aware
smart cropping to fit each layout slot, and renders a clean high-res page
to ./output/page_1.png (3000x3000px @ 300 DPI).

Dependencies: Pillow, opencv-python, numpy
"""

import os
import random

import cv2
import numpy as np
from PIL import Image

from templets import define_slots  # layout templates live in templets.py

# Enable HEIC/HEIF support (iPhone photos) if pillow-heif is installed.
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    pass

# --- Configuration -----------------------------------------------------------
INPUT_DIR = "./input_images/"
OUTPUT_DIR = "./output/"
OUTPUT_PREFIX = "page_"     # files are named page_1.png, page_2.png, ...

PAGE_SIZE = 3000           # square page in pixels
DPI = 300
BG_COLOR = (255, 255, 255)  # clean white background (use (28, 28, 30) for dark)
MARGIN = 220                # outer page margin
GUTTER = 70                 # spacing between images

# Which layout to render: a name from LAYOUTS (see below) or "random".
LAYOUT = "random"

VALID_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff",
             ".heic", ".heif")


def list_images(folder):
    """Return absolute paths of all usable images in the folder."""
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Input folder not found: {folder}")
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(VALID_EXT)
    ]
    return files


def next_output_path():
    """Return a fresh, non-overwriting path like ./output/page_3.png."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    i = 1
    while True:
        path = os.path.join(OUTPUT_DIR, f"{OUTPUT_PREFIX}{i}.png")
        if not os.path.exists(path):
            return path
        i += 1


def detect_focus(cv_img):
    """Return (cx, cy) focus point in pixel coords.

    Strategy: face/body via Haar cascades -> saliency map -> image center.
    """
    h, w = cv_img.shape[:2]
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # 1) Try face/body detection using bundled Haar cascades.
    base = cv2.data.haarcascades
    cascades = [
        "haarcascade_frontalface_default.xml",
        "haarcascade_fullbody.xml",
    ]
    boxes = []
    for name in cascades:
        clf = cv2.CascadeClassifier(os.path.join(base, name))
        if clf.empty():
            continue
        found = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                     minSize=(int(w * 0.05), int(h * 0.05)))
        boxes.extend(found)

    if boxes:
        # Center the crop on the bounding box of all detections.
        xs = [b[0] for b in boxes]
        ys = [b[1] for b in boxes]
        xe = [b[0] + b[2] for b in boxes]
        ye = [b[1] + b[3] for b in boxes]
        return ((min(xs) + max(xe)) / 2.0, (min(ys) + max(ye)) / 2.0)

    # 2) Fallback: saliency map centroid (if available in this OpenCV build).
    try:
        sal = cv2.saliency.StaticSaliencySpectralResidual_create()
        ok, sal_map = sal.computeSaliency(cv_img)
        if ok:
            sal_map = (sal_map * 255).astype("uint8")
            _, thresh = cv2.threshold(sal_map, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            m = cv2.moments(thresh, binaryImage=True)
            if m["m00"] > 0:
                return (m["m10"] / m["m00"], m["m01"] / m["m00"])
    except Exception:
        pass

    # 3) Default: geometric center.
    return (w / 2.0, h / 2.0)


def smart_crop(pil_img, target_ratio):
    """Crop pil_img to target_ratio (w/h), keeping the detected subject centered.

    Only trims the outer edges; never distorts the image.
    """
    cv_img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = cv_img.shape[:2]
    fx, fy = detect_focus(cv_img)

    cur_ratio = w / h
    if cur_ratio > target_ratio:
        # Too wide: trim left/right.
        new_w = int(round(h * target_ratio))
        new_h = h
        x0 = int(round(fx - new_w / 2.0))
        x0 = max(0, min(x0, w - new_w))  # clamp inside image
        y0 = 0
    else:
        # Too tall: trim top/bottom.
        new_w = w
        new_h = int(round(w / target_ratio))
        y0 = int(round(fy - new_h / 2.0))
        y0 = max(0, min(y0, h - new_h))  # clamp inside image
        x0 = 0

    return pil_img.crop((x0, y0, x0 + new_w, y0 + new_h))


def fit_to_slot(pil_img, slot_w, slot_h):
    """Smart-crop to the slot ratio, then resize to exact slot dimensions."""
    cropped = smart_crop(pil_img, slot_w / slot_h)
    return cropped.resize((slot_w, slot_h), Image.LANCZOS)


def build_page():
    images = list_images(INPUT_DIR)
    name, slots = define_slots(PAGE_SIZE, MARGIN, GUTTER, LAYOUT)

    if len(images) < len(slots):
        raise ValueError(
            f"Layout '{name}' needs {len(slots)} images, "
            f"found {len(images)} in {INPUT_DIR}")

    chosen = random.sample(images, len(slots))  # unique random images

    page = Image.new("RGB", (PAGE_SIZE, PAGE_SIZE), BG_COLOR)
    for path, (x, y, w, h) in zip(chosen, slots):
        with Image.open(path) as src:
            tile = fit_to_slot(src, w, h)
        page.paste(tile, (x, y))

    output_path = next_output_path()  # never overwrites an existing page
    page.save(output_path, dpi=(DPI, DPI))
    print(f"Saved {output_path} (layout: {name}, "
          f"{PAGE_SIZE}x{PAGE_SIZE}px @ {DPI} DPI)")
    print("Images used:", ", ".join(os.path.basename(p) for p in chosen))


if __name__ == "__main__":
    build_page()
