#!/usr/bin/env python3
import argparse
import csv
import subprocess
import sys


def build_expr(lines, idx):
    expr = "0" if idx < 2 else "1"
    lerp = "(a + (b-a)*((t-t0)/(t1-t0)))"
    for i in range(len(lines) - 1):
        t0, x0, y0, z0 = lines[i]
        t1, x1, y1, z1 = lines[i + 1]
        if idx == 0:
            a, b = x0, x1
        elif idx == 1:
            a, b = y0, y1
        else:
            a, b = z0, z1
        seg = (
            f"if(between(t,{t0},{t1}), "
            f"{lerp.replace('a', a).replace('b', b).replace('t0', t0).replace('t1', t1)},"
        )
        expr = f"{seg}{expr})"
    return expr


def read_poi(path):
    rows = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return rows
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) < 4:
                raise ValueError("poi.csv rows must be: t,x,y,z")
            rows.append([cell.strip() for cell in row[:4]])
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Reframe/crop a video using POI keyframes from poi.csv."
    )
    parser.add_argument("--in", dest="inp", default="in.mov")
    parser.add_argument("--poi", dest="poi", default="poi.csv")
    parser.add_argument("--out", dest="out", default="out_reframe.mp4")
    parser.add_argument("--out-w", dest="out_w", default="1920")
    parser.add_argument("--out-h", dest="out_h", default="1080")
    parser.add_argument("--venc", dest="venc", default="h264_videotoolbox")
    parser.add_argument("--vb", dest="vb", default="20M")
    args = parser.parse_args()

    lines = read_poi(args.poi)
    if len(lines) < 2:
        print("poi.csv must contain at least 2 data rows", file=sys.stderr)
        return 1

    expr_cx = build_expr(lines, 0)
    expr_cy = build_expr(lines, 1)
    expr_z = build_expr(lines, 2)

    vf = (
        f"scale={args.out_w}:{args.out_h}:force_original_aspect_ratio=increase,"
        f"crop="
        f"w='{args.out_w}/({expr_z})':"
        f"h='{args.out_h}/({expr_z})':"
        f"x='max(0, min(iw-ow, ({expr_cx})-ow/2))':"
        f"y='max(0, min(ih-oh, ({expr_cy})-oh/2))',"
        f"scale={args.out_w}:{args.out_h}"
    )

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        args.inp,
        "-vf",
        vf,
        "-c:v",
        args.venc,
        "-b:v",
        args.vb,
        "-c:a",
        "copy",
        args.out,
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
