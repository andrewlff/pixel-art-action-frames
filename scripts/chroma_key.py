#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chroma_key.py — 色键去背：绿幕/白地/黑地一键透明化。

用法：
  # 绿幕去背
  python chroma_key.py green_screen.png --mode green --out transparent.png

  # 白地去背
  python chroma_key.py white_bg.png --mode white --out transparent.png

  # 黑地去背
  python chroma_key.py black_bg.png --mode black --out transparent.png

  # 批量：整个目录
  python chroma_key.py frames/ --mode green --out transparent_frames/
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixel_core import load_png, save_png, chroma_key, remove_flat_bg


def process_file(in_path, out_path, mode, tolerance):
    px, w, h = load_png(in_path)
    if mode == "green":
        chroma_key(px, w, h, key_color=(0, 255, 0), tolerance=tolerance)
    elif mode == "white":
        remove_flat_bg(px, w, h, mode="white", threshold=255 - tolerance * 4)
    elif mode == "black":
        remove_flat_bg(px, w, h, mode="black", threshold=tolerance * 4)
    else:
        print(f"未知模式: {mode}")
        sys.exit(1)
    save_png(out_path, px, w, h)


def main():
    ap = argparse.ArgumentParser(description="色键去背工具")
    ap.add_argument("input", help="输入图片或目录")
    ap.add_argument("--mode", choices=["green", "white", "black"], required=True,
                    help="去背模式")
    ap.add_argument("--out", required=True, help="输出文件或目录")
    ap.add_argument("--tolerance", type=int, default=25, help="容差（默认 25）")
    args = ap.parse_args()

    if os.path.isdir(args.input):
        os.makedirs(args.out, exist_ok=True)
        files = sorted(f for f in os.listdir(args.input) if f.endswith(".png"))
        for fn in files:
            process_file(os.path.join(args.input, fn),
                         os.path.join(args.out, fn),
                         args.mode, args.tolerance)
        print(f"已批量处理 {len(files)} 帧 → {args.out}/")
    else:
        if not os.path.exists(args.input):
            print(f"文件不存在: {args.input}")
            sys.exit(1)
        process_file(args.input, args.out, args.mode, args.tolerance)
        print(f"已处理 → {args.out}")


if __name__ == "__main__":
    main()
