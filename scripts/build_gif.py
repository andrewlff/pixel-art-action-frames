#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""透明动画 GIF 编码器（纯标准库，GIF89a）。

把 6 张像素化帧合成为循环播放的动画 GIF。透明动画正确性关键：
- 全局色表 + 专用透明索引，LSD 背景索引指向透明色；
- 每帧 GCE disposal=2（帧前恢复背景=透明），避免上一帧残影叠加到透明区域；
- 全尺寸帧 + LZW 子块，帧延迟/循环与 JSON 清单一致。

用法:
    python build_gif.py <像素目录> <前缀>
输入: <像素目录>/<前缀>_1.png .. _6.png（RGBA PNG）
输出: <像素目录>/<前缀>_sheet.gif（120ms/帧、无限循环、透明）
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_core as pc

FRAME_MS = 120   # 与 JSON 清单一致：120ms/帧
LOOP = 0         # 0 = 无限循环


def load_frames(paths):
    out = []
    for p in paths:
        px, w, h = pc.load_png(p)
        out.append((px, w, h))
    return out


def table_bits(n):
    """GIF 色表位宽：使 2^bits >= n 的最小 bits（2..8）。"""
    bits = 1
    while (1 << bits) < n:
        bits += 1
    return max(2, min(bits, 8))


def build_global_table(frames):
    """合并全部帧的不透明像素颜色为全局色表；
    若存在透明像素，选一个不在色表中的颜色作专用透明色。
    返回 (colors 填充到 2^bits, bits, transparent_index_or_None)。"""
    colors, index = [], {}
    has_transp = False
    for px, _, _ in frames:
        for row in px:
            for c in row:
                if c[3] < 128:
                    has_transp = True
                    continue
                key = (c[0], c[1], c[2])
                if key not in index:
                    index[key] = len(colors)
                    colors.append(key)
    transp_idx = None
    if has_transp:
        used = set(colors)
        for cand in ((255, 0, 255), (0, 255, 255), (255, 255, 0),
                     (255, 0, 0), (0, 255, 0), (0, 0, 255),
                     (255, 128, 0), (128, 0, 255)):
            if cand not in used:
                colors.append(cand)
                transp_idx = len(colors) - 1
                break
        else:
            raise ValueError("无法选择专用透明色")
    bits = table_bits(len(colors))
    size = 1 << bits
    while len(colors) < size:
        colors.append((0, 0, 0))
    return colors, bits, transp_idx


def to_indices(px, w, h, table_index, transp_idx):
    idx = []
    for row in px:
        for c in row:
            if c[3] < 128:
                idx.append(transp_idx)
            else:
                idx.append(table_index[(c[0], c[1], c[2])])
    return bytes(idx)


def lzw_encode(data, min_code_size):
    """GIF 风格 LZW 编码，返回码流字节（未分块）。"""
    clear = 1 << min_code_size
    eoi = clear + 1
    code_len = min_code_size + 1
    next_code = eoi + 1
    table = {bytes([i]): i for i in range(clear)}
    code_pairs = [(clear, code_len)]
    w = bytes([data[0]])

    def add_table(wk):
        nonlocal next_code, code_len
        table[wk] = next_code
        next_code += 1
        while next_code > (1 << code_len) and code_len < 12:
            code_len += 1

    for k in data[1:]:
        wk = w + bytes([k])
        hit = table.get(wk)
        if hit is not None:
            w = wk
            continue
        code_pairs.append((table[w], code_len))
        if next_code < 4096:
            add_table(wk)
        else:
            # 表满：输出 clear 并重置（clear 后不预建条目，解码器表状态才同步）
            code_pairs.append((clear, code_len))
            table = {bytes([i]): i for i in range(clear)}
            next_code = eoi + 1
            code_len = min_code_size + 1
        w = bytes([k])
    code_pairs.append((table[w], code_len))
    code_pairs.append((eoi, code_len))

    # 打包为字节流（LSB 优先）
    stream = bytearray()
    acc, acc_bits = 0, 0
    for code, width in code_pairs:
        acc |= code << acc_bits
        acc_bits += width
        while acc_bits >= 8:
            stream.append(acc & 0xFF)
            acc >>= 8
            acc_bits -= 8
    if acc_bits > 0:
        stream.append(acc & 0xFF)
    return bytes(stream)


def sub_blocks(data):
    """GIF 数据子块：每块最多 255 字节，0 结尾。"""
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i:i + 255]
        out.append(len(chunk))
        out.extend(chunk)
    out.append(0)
    return bytes(out)


def build_gif(frames, w, h, frame_ms, loop):
    colors, bits, transp_idx = build_global_table(frames)
    bg_index = transp_idx if transp_idx is not None else 0
    table_index = {c: i for i, c in enumerate(colors)}
    out = bytearray()
    out += b"GIF89a"
    # 逻辑屏幕描述符：全局色表存在，背景索引指向透明色（无透明时 0）
    packed_lsd = 0x80 | (bits - 1)
    out += struct.pack("<HHBBB", w, h, packed_lsd, bg_index, 0)
    for r, g, b in colors:
        out += bytes((r, g, b))
    # NETSCAPE 循环扩展
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01"
    out += struct.pack("<H", loop)
    out += b"\x00"
    delay = max(1, round(frame_ms / 10))
    for px, _, _ in frames:
        # GCE：disposal=2（帧前恢复背景），透明时置透明标志
        packed_gce = 0x08 | (0x01 if transp_idx is not None else 0)
        out += b"\x21\xf9\x04"
        out += bytes((packed_gce,))
        out += struct.pack("<H", delay)
        out += bytes(((transp_idx if transp_idx is not None else 0), 0))
        # 图像描述符（无局部色表，用全局色表）
        out += b"\x2c"
        out += struct.pack("<HHHH", 0, 0, w, h)
        out += bytes((0,))
        # LZW 最小码长 + 数据
        data = to_indices(px, w, h, table_index, transp_idx)
        out += bytes((bits,))
        out += sub_blocks(lzw_encode(data, bits))
    out += b"\x3b"
    return bytes(out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    pixel_dir, prefix = sys.argv[1], sys.argv[2]
    paths = [os.path.join(pixel_dir, f"{prefix}_{i}.png") for i in range(1, 7)]
    frames = load_frames(paths)
    w, h = frames[0][1], frames[0][2]
    for _, fw, fh in frames:
        assert (fw, fh) == (w, h), "帧尺寸不一致"
    print(f"帧 {len(frames)} 张，{w}x{h}，帧延迟 {FRAME_MS}ms，循环={LOOP}")
    gif = build_gif(frames, w, h, FRAME_MS, LOOP)
    out_path = os.path.join(pixel_dir, f"{prefix}_sheet.gif")
    with open(out_path, "wb") as f:
        f.write(gif)
    print(f"GIF 已生成: {out_path}  ({len(gif) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
