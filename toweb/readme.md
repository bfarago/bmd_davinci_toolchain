## Toweb snapshot pipeline

This folder contains a small test pipeline that creates low-resolution snapshot
videos from original media files based on tasks stored in SQLite.

## Files

- `snapshot.py` main conversion script (reads SQLite, runs ffmpeg).
- `seed_db.py` test DB generator (creates sample data and tasks).
- `create_db.py` creates the SQLite schema.
- `toweb.db` SQLite database (created by `seed_db.py`).
- `prompt.txt` the original spec text.

## Requirements

- `python3`
- `ffmpeg` on PATH

## SQLite schema overview

- `camera` camera metadata and lens limits.
- `media_file` originals and outputs (outputs link to their original via
  `parent_id`).
- `poi` points of interest attached to an original.
- `edit_point` joins original/output/poi/camera and stores redundant data used
  during processing.
- `marker` timeline annotations (review/marker/subtitle/chapter).

Timestamp fields (ISO 8601 strings, PHP-editable):

- `media_file.raw_mtime` last known modification time of the raw file.
- `media_file.conv_mtime` last successful conversion time.
- `media_file.poi_mtime` last time the POI list changed (global for the original).
- `poi.updated_at` per-POI change time.
- `marker.t` seconds (float, ffmpeg-compatible), `marker.type`, `marker.text`.

Format/config fields in `media_file` (shared by originals and outputs):

- `width`, `height`, `frame_rate`, `codec`
- `duration`, `start_time`
- `cfg_start` and `cfg_max_duration` control what segment to convert
  (if `cfg_max_duration` is NULL, the full file is converted).
- Output size/codec/frame rate are read from the output `media_file` row.
- Missing original format fields are filled from `ffprobe` on first run.

## Processing rules (summary)

- If `conv_mtime` is newer than `raw_mtime`, `poi_mtime`, and all `poi.updated_at`
  values, nothing is processed.
- If the raw file is newer than `conv_mtime`: create the base snapshot and all
  POI snapshots.
- If only POIs are newer: regenerate only the POI snapshots that are newer
  (or all POIs if `poi_mtime` is newer).

## Usage

Create a test database:

```bash
python3 create_db.py --reset-db
python3 seed_db.py
```

Clear conversion timestamps (force re-run):

```bash
python3 seed_db.py --clear-conv
```

Run snapshot conversion:

```bash
python3 snapshot.py --db toweb.db
```

Optional flags:

- `--out-dir` output base directory (defaults to DB directory).
- `--out-w`, `--out-h` output size override (if DB is missing values).
- `--duration` max duration override in seconds (if DB is missing values).
- `--dry-run` prints ffmpeg commands without executing them.
