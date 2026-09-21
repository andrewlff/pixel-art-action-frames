#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""video_to_frames.py — 视频抽帧为 PNG 序列（依赖 ffmpeg）。

用法：
  python video_to_frames.py walk.mp4 --fps 8 --out frames/
  python video_to_frames.py attack.mp4 --fps 12 --out attack_frames/ --prefix attack
"""
import argparse
import os
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser(description="视频抽帧工具")
    ap.add_argument("input", help="输入视频文件")
    ap.add_argument("--fps", type=float, default=8, help="采样帧率（默认 8）")
    ap.add_argument("--out", default="frames", help="输出目录")
    ap.add_argument("--prefix", default="frame", help="输出文件名前缀")
    args = ap.parse_args()

    if not os.path.exists(args.input):
        print(f"文件不存在: {args.input}")
        sys.exit(1)

    os.makedirs(args.out, exist_ok=True)
    out_pattern = os.path.join(args.out, f"{args.prefix}_%04d.png")

    cmd = [
        "ffmpeg", "-i", args.input,
        "-vf", f"fps={args.fps}",
        "-y",
        out_pattern
    ]
    print("运行:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("ffmpeg 错误:", result.stderr[-500:])
        sys.exit(1)

    frames = sorted(f for f in os.listdir(args.out) if f.endswith(".png"))
    print(f"已抽取 {len(frames)} 帧 → {args.out}/")


if __name__ == "__main__":
    main()
