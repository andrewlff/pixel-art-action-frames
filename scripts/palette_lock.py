#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""palette_lock.py — 提取色板、导出 .gpl、把图像量化到指定色板。

用法：
  # 从首帧提取色板并导出
  python palette_lock.py extract frame_000.png --palette palette.gpl

  # 用已有色板量化图像
  python palette_lock.py apply frame_001.png --palette palette.gpl --out frame_001_q.png

  # 批量：多帧统一色板
  python palette_lock.py batch frames/ --out frames_q/
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixel_core import (load_png, save_png, extract_palette,
                        quantize_to_palette, save_gpl)


def cmd_extract(args):
    px, w, h = load_png(args.input)
    palette = extract_palette(px, w, h)
    save_gpl(args.palette, palette, name=os.path.splitext(os.path.basename(args.input))[0])
    print(f"色板已提取 {len(palette)} 色 → {args.palette}")


def load_gpl(path):
    """读取 .gpl 色板文件，返回 [(r,g,b), ...]。"""
    palette = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[0].isdigit():
                palette.append((int(parts[0]), int(parts[1]), int(parts[2])))
    return palette


def cmd_apply(args):
    px, w, h = load_png(args.input)
    palette = load_gpl(args.palette)
    out = quantize_to_palette(px, w, h, palette)
    save_png(args.out, out, w, h)
    print(f"已用 {len(palette)} 色板量化 → {args.out}")


def cmd_batch(args):
    """批量：用第一张帧的色板量化所有帧。"""
    files = sorted(f for f in os.listdir(args.frames_dir) if f.endswith(".png"))
    if not files:
        print("没找到 PNG")
        sys.exit(1)
    os.makedirs(args.out, exist_ok=True)
    # 提取首帧色板
    first_px, w, h = load_png(os.path.join(args.frames_dir, files[0]))
    palette = extract_palette(first_px, w, h)
    print(f"首帧色板: {len(palette)} 色")
    save_gpl(os.path.join(args.out, "palette.gpl"), palette)
    # 量化所有帧
    for fn in files:
        px, w, h = load_png(os.path.join(args.frames_dir, fn))
        out = quantize_to_palette(px, w, h, palette)
        save_png(os.path.join(args.out, fn), out, w, h)
    print(f"已批量量化 {len(files)} 帧 → {args.out}/")


def main():
    ap = argparse.ArgumentParser(description="色板锁定工具")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="从图像提取色板导出 .gpl")
    e.add_argument("input")
    e.add_argument("--palette", default="palette.gpl")
    e.set_defaults(func=cmd_extract)

    a = sub.add_parser("apply", help="用色板量化单帧")
    a.add_argument("input")
    a.add_argument("--palette", required=True)
    a.add_argument("--out", required=True)
    a.set_defaults(func=cmd_apply)

    b = sub.add_parser("batch", help="批量统一色板")
    b.add_argument("frames_dir")
    b.add_argument("--out", required=True)
    b.set_defaults(func=cmd_batch)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
