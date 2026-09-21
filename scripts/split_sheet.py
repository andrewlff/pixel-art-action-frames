#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""split_sheet.py — 把一张 sprite sheet 大图按 cols×rows 切成单帧 PNG。

用法：
  python split_sheet.py sheet.png --cols 4 --rows 4 --out frames/
  python split_sheet.py walk_sheet.png --cols 3 --rows 2 --out walk_frames/ --prefix walk
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixel_core import split_sheet


def main():
    ap = argparse.ArgumentParser(description="Sprite Sheet 拆分器")
    ap.add_argument("input", help="输入 sprite sheet PNG")
    ap.add_argument("--cols", type=int, required=True, help="列数")
    ap.add_argument("--rows", type=int, required=True, help="行数")
    ap.add_argument("--out", default="frames", help="输出目录")
    ap.add_argument("--prefix", default="frame", help="输出文件名前缀")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"文件不存在: {args.input}")
        sys.exit(1)

    paths, fw, fh = split_sheet(args.input, args.cols, args.rows, args.out, args.prefix)
    print(f"已拆分 {len(paths)} 帧 → {args.out}/")
    print(f"单帧尺寸: {fw}×{fh}")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
