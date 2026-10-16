#!/usr/bin/env python3
"""
measure_reference.py - CLI tool for extracting physical dimensions from reference images.

Usage:
  # 1. Calibrate px/mm ratio from known dimension:
  python3 measure_reference.py calibrate --px 1214 --mm 60.0

  # 2. Find the non-background bounding box (not a feature detector):
  python3 measure_reference.py bbox --image crop.png --scale 20.23

  # 3. Find non-background object bounding box:
  python3 measure_reference.py bbox --image image.png
"""

import argparse
import sys
from PIL import Image
import numpy as np


def cmd_calibrate(args):
    if args.px <= 0 or args.mm <= 0:
        raise ValueError("--px and --mm must be greater than zero")
    ratio = args.px / args.mm
    print(f"Calibration:")
    print(f"  Known span: {args.px:.1f} px = {args.mm:.2f} mm")
    print(f"  Scale: {ratio:.4f} px/mm  (1 px = {1.0 / ratio:.4f} mm)")


def cmd_bbox(args):
    if args.scale is not None and args.scale <= 0:
        raise ValueError("--scale must be greater than zero")
    if not 0 <= args.bg_thresh <= 255:
        raise ValueError("--bg-thresh must be between 0 and 255")
    img = Image.open(args.image).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]
    # Detect non-white or non-transparent pixels
    is_bg = (alpha < 20) | (np.all(rgb > args.bg_thresh, axis=2))
    non_bg_y, non_bg_x = np.where(~is_bg)
    if len(non_bg_x) == 0:
        print("Error: No foreground pixels found.")
        sys.exit(1)

    min_x, max_x = int(non_bg_x.min()), int(non_bg_x.max())
    min_y, max_y = int(non_bg_y.min()), int(non_bg_y.max())
    # Pixel coordinates are inclusive, so include both endpoint pixels.
    width = max_x - min_x + 1
    height = max_y - min_y + 1

    print(f"Foreground Bounding Box for '{args.image}':")
    print(f"  X: [{min_x}, {max_x}] (Width: {width} px)")
    print(f"  Y: [{min_y}, {max_y}] (Height: {height} px)")

    if args.scale:
        print(f"  Width in mm: {width / args.scale:.2f} mm")
        print(f"  Height in mm: {height / args.scale:.2f} mm")


def cmd_crop(args):
    img = Image.open(args.image)
    try:
        box = [int(v.strip()) for v in args.coords.split(",")]
    except ValueError:
        raise ValueError("--coords must be four comma-separated integers: x1,y1,x2,y2")
    if len(box) != 4:
        raise ValueError("--coords must contain exactly four integers: x1,y1,x2,y2")
    if not (0 <= box[0] < box[2] <= img.width and 0 <= box[1] < box[3] <= img.height):
        raise ValueError(f"Crop must satisfy 0 <= x1 < x2 <= {img.width} and 0 <= y1 < y2 <= {img.height}")
    cropped = img.crop(box)
    cropped.save(args.out)
    print(f"Saved cropped image ({box[2]-box[0]}x{box[3]-box[1]} px) to: {args.out}")


def main():
    parser = argparse.ArgumentParser(description="Extract dimensions from reference photos.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # calibrate
    p_cal = subparsers.add_parser("calibrate", help="Calculate px/mm ratio")
    p_cal.add_argument("--px", type=float, required=True, help="Measured span in pixels")
    p_cal.add_argument("--mm", type=float, required=True, help="Known real-world length in mm")

    # bbox
    p_bbox = subparsers.add_parser("bbox", help="Find foreground bbox and dimensions")
    p_bbox.add_argument("--image", required=True, help="Path to image")
    p_bbox.add_argument("--scale", type=float, help="Scale in px/mm")
    p_bbox.add_argument("--bg-thresh", type=int, default=245, help="RGB threshold for white background")

    # crop
    p_crop = subparsers.add_parser("crop", help="Crop image for inspection")
    p_crop.add_argument("--image", required=True, help="Path to image")
    p_crop.add_argument("--coords", required=True, help="x1,y1,x2,y2")
    p_crop.add_argument("--out", required=True, help="Output image path")

    args = parser.parse_args()
    try:
        if args.command == "calibrate":
            cmd_calibrate(args)
        elif args.command == "bbox":
            cmd_bbox(args)
        elif args.command == "crop":
            cmd_crop(args)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
