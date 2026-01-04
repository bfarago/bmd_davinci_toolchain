#!/usr/bin/env bash
set -euo pipefail

IN="in.mov"
POI="poi.csv"
OUT="out_reframe.mp4"

# Output resolution (pl. 1920x1080, vagy állított 1080x1920)
OUT_W=1920
OUT_H=1080

# Encoder (Macen gyors)
VENC="h264_videotoolbox"
VB=20M

# Read POI into arrays (skip header). macOS bash 3.2 lacks mapfile.
LINES=()
while IFS= read -r line; do
  LINES+=("$line")
done < <(tail -n +2 "$POI")

# Build piecewise expressions for cx(t), cy(t), z(t)
# We'll create functions using if(between(t,t0,t1), lerp(...), ...)
expr_cx="0"
expr_cy="0"
expr_z="1"

lerp='(a + (b-a)*((t-t0)/(t1-t0)))'

for ((i=0; i<${#LINES[@]}-1; i++)); do
  IFS=',' read -r t0 x0 y0 z0 <<< "${LINES[$i]}"
  IFS=',' read -r t1 x1 y1 z1 <<< "${LINES[$((i+1))]}"

  seg_cx="if(between(t,${t0},${t1}), ${lerp//a/$x0//b/$x1//t0/$t0//t1/$t1},"
  seg_cy="if(between(t,${t0},${t1}), ${lerp//a/$y0//b/$y1//t0/$t0//t1/$t1},"
  seg_z="if(between(t,${t0},${t1}), ${lerp//a/$z0//b/$z1//t0/$t0//t1/$t1},"

  expr_cx="${seg_cx}${expr_cx})"
  expr_cy="${seg_cy}${expr_cy})"
  expr_z="${seg_z}${expr_z})"
done

# Crop size derived from zoom: crop_w = OUT_W / z, crop_h = OUT_H / z
# Then crop x,y so that crop center follows (cx,cy)
# Clamp to frame boundaries.
vf="
scale=${OUT_W}:${OUT_H}:force_original_aspect_ratio=increase,
crop=
w='${OUT_W}/(${expr_z})':
h='${OUT_H}/(${expr_z})':
x='max(0, min(iw-ow, (${expr_cx})-ow/2))':
y='max(0, min(ih-oh, (${expr_cy})-oh/2))',
scale=${OUT_W}:${OUT_H}
"

ffmpeg -hide_banner -y -i "$IN" \
  -vf "$vf" \
  -c:v "$VENC" -b:v "$VB" \
  -c:a copy \
  "$OUT"
