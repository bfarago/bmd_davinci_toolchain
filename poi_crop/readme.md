## POI crop / reframe

This folder contains two versions of the same workflow:

- `poi_crop.sh` (bash) using only `read` so it works on macOS bash 3.2
- `poi_crop.py` (python3)

Both scripts generate a dynamic crop that follows a point-of-interest (POI)
path over time, with optional zoom, and then scale to a fixed output size.

## Requirements

- `ffmpeg` available on your PATH.
- For the bash version: macOS default bash is OK.
- For the Python version: `python3`.

## Input files

- `in.mov` input video (change via flags or edit defaults).
- `poi.csv` POI keyframes.

`poi.csv` format (first row is a header):

```
t,x,y,z
0.0,960,540,1.0
1.5,980,560,1.2
...
```

Notes:

- `t` is time in seconds (used in ffmpeg expressions).
- `x,y` are pixel coordinates in the source frame.
- `z` is zoom (1.0 = no zoom, 2.0 = 2x).

## Output

- `out_reframe.mp4` reframe output (change via flags or edit defaults).

## Usage (bash)

```bash
./poi_crop.sh
```

## Usage (python)

```bash
python3 poi_crop.py
```

Optional flags (python):

- `--in`, `--poi`, `--out`
- `--out-w`, `--out-h`
- `--venc`, `--vb`
