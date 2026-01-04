#!/usr/bin/env python3
import argparse
import os
import sqlite3
import subprocess
import sys
import json
from datetime import datetime, timezone


def parse_ts(val):
    if not val:
        return None
    return datetime.fromisoformat(val.replace("Z", "+00:00"))


def iso_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def file_mtime(path):
    try:
        ts = os.path.getmtime(path)
    except OSError:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def ensure_schema(conn):
    try:
        conn.execute("SELECT 1 FROM media_file LIMIT 1")
    except sqlite3.OperationalError as exc:
        raise RuntimeError("Database schema missing. Run create_db.py first.") from exc


def load_poi_max_ts(conn, media_id):
    rows = conn.execute(
        "SELECT updated_at FROM poi WHERE media_id = ? AND updated_at IS NOT NULL",
        (media_id,),
    ).fetchall()
    max_ts = None
    for (val,) in rows:
        ts = parse_ts(val)
        if ts and (max_ts is None or ts > max_ts):
            max_ts = ts
    return max_ts


def load_edit_points(conn, media_id):
    return conn.execute(
        """
        SELECT ep.*,
               mf.id AS out_id,
               mf.path AS out_path,
               mf.kind AS out_kind,
               mf.width AS out_width,
               mf.height AS out_height,
               mf.frame_rate AS out_frame_rate,
               mf.codec AS out_codec,
               mf.duration AS out_duration,
               mf.cfg_start AS out_cfg_start,
               mf.cfg_max_duration AS out_cfg_max_duration,
               p.t AS poi_t,
               p.x AS poi_x,
               p.y AS poi_y,
               p.z AS poi_z,
               p.distance AS poi_distance,
               p.updated_at AS poi_updated_at
        FROM edit_point ep
        JOIN media_file mf ON mf.id = ep.output_media_id
        LEFT JOIN poi p ON p.id = ep.poi_id
        WHERE ep.original_media_id = ?
        ORDER BY mf.kind, mf.id
        """,
        (media_id,),
    ).fetchall()


def resolve_path(base_dir, path_value):
    if os.path.isabs(path_value):
        return path_value
    return os.path.join(base_dir, path_value)


def run_ffmpeg(cmd, dry_run):
    if dry_run:
        print("DRY RUN:", " ".join(cmd))
        return True
    result = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    return result.returncode == 0


def probe_media(path):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,codec_name",
        "-show_entries",
        "format=duration,start_time",
        "-of",
        "json",
        path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        return {}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    frame_rate = stream.get("avg_frame_rate") or ""
    if "/" in frame_rate:
        num, den = frame_rate.split("/", 1)
        try:
            frame_rate = float(num) / float(den)
        except (ValueError, ZeroDivisionError):
            frame_rate = None
    else:
        try:
            frame_rate = float(frame_rate)
        except (ValueError, TypeError):
            frame_rate = None
    try:
        duration = float(fmt.get("duration")) if fmt.get("duration") is not None else None
    except (ValueError, TypeError):
        duration = None
    try:
        start_time = float(fmt.get("start_time")) if fmt.get("start_time") is not None else None
    except (ValueError, TypeError):
        start_time = None
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "frame_rate": frame_rate,
        "codec": stream.get("codec_name"),
        "duration": duration,
        "start_time": start_time,
    }


def choose_codec(value):
    if not value:
        return "libx264"
    if value.lower() == "h264":
        return "libx264"
    return value


def render_base(inp, outp, out_w, out_h, start, duration, codec, frame_rate, dry_run):
    vf = (
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,"
        f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2"
    )
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", inp]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vf",
        vf,
        "-an",
        "-c:v",
        choose_codec(codec),
        "-crf",
        "28",
        "-preset",
        "veryfast",
        outp,
    ]
    if frame_rate:
        vf_index = cmd.index("-vf")
        cmd[vf_index:vf_index] = ["-r", str(frame_rate)]
    return run_ffmpeg(cmd, dry_run)


def render_poi(inp, outp, out_w, out_h, start, duration, codec, frame_rate, poi, dry_run):
    x = poi["poi_x"]
    y = poi["poi_y"]
    z = poi["poi_z"] or 1.0
    t = poi["poi_t"] or 0

    vf = (
        f"crop="
        f"w='{out_w}/({z})':"
        f"h='{out_h}/({z})':"
        f"x='max(0, min(iw-ow, ({x})-ow/2))':"
        f"y='max(0, min(ih-oh, ({y})-oh/2))',"
        f"scale={out_w}:{out_h}"
    )
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    seek = t
    if start is not None:
        seek = start + t
    if seek:
        cmd += ["-ss", str(seek)]
    cmd += ["-i", inp]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vf",
        vf,
        "-an",
        "-c:v",
        choose_codec(codec),
        "-crf",
        "28",
        "-preset",
        "veryfast",
        outp,
    ]
    if frame_rate:
        vf_index = cmd.index("-vf")
        cmd[vf_index:vf_index] = ["-r", str(frame_rate)]
    return run_ffmpeg(cmd, dry_run)


def main():
    parser = argparse.ArgumentParser(description="Generate small snapshot videos from a SQLite task DB.")
    parser.add_argument("--db", default="toweb.db")
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--out-w", default=None, type=int)
    parser.add_argument("--out-h", default=None, type=int)
    parser.add_argument("--duration", default=None, type=float, help="Override max duration (seconds)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(args.db))
    out_base = args.out_dir or base_dir

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    originals = conn.execute(
        "SELECT * FROM media_file WHERE parent_id IS NULL AND kind = 'original'"
    ).fetchall()

    if not originals:
        print("No original media files found.")
        return 0

    for media in originals:
        media_id = media["id"]
        in_path = resolve_path(base_dir, media["path"])
        if not os.path.exists(in_path):
            print(f"Missing input: {in_path} (media_id={media_id})")
            continue

        raw_ts = parse_ts(media["raw_mtime"]) or file_mtime(in_path)
        poi_ts = parse_ts(media["poi_mtime"])
        conv_ts = parse_ts(media["conv_mtime"])
        poi_max_ts = load_poi_max_ts(conn, media_id)

        if any(media[key] is None for key in ("width", "height", "frame_rate", "codec", "duration", "start_time")):
            meta = probe_media(in_path)
            if meta:
                for key, value in meta.items():
                    if media[key] is None and value is not None:
                        conn.execute(
                            f"UPDATE media_file SET {key} = ? WHERE id = ?",
                            (value, media_id),
                        )
                conn.commit()

        needs_base = conv_ts is None or (raw_ts and raw_ts > conv_ts)
        poi_changed = (
            conv_ts is None
            or (poi_ts and poi_ts > conv_ts)
            or (poi_max_ts and poi_max_ts > conv_ts)
        )

        edit_points = load_edit_points(conn, media_id)
        if not edit_points:
            print(f"No edit points for media_id={media_id}")
            continue

        updated_outputs = []
        ran_any = False

        for ep in edit_points:
            out_path = resolve_path(out_base, ep["out_path"])
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            out_w = ep["out_width"] or args.out_w
            out_h = ep["out_height"] or args.out_h
            if not out_w or not out_h:
                print(f"Missing output size for out_id={ep['out_id']}")
                continue

            cfg_start = ep["out_cfg_start"]
            if cfg_start is None:
                cfg_start = media["cfg_start"]
            max_duration = ep["out_cfg_max_duration"]
            if max_duration is None:
                max_duration = media["cfg_max_duration"]
            if max_duration is None and args.duration is not None:
                max_duration = args.duration

            if ep["out_kind"] == "snapshot_base":
                if not needs_base:
                    continue
                ok = render_base(
                    in_path,
                    out_path,
                    out_w,
                    out_h,
                    cfg_start,
                    max_duration,
                    ep["out_codec"],
                    ep["out_frame_rate"],
                    args.dry_run,
                )
            else:
                if not (needs_base or poi_changed):
                    continue
                poi_updated = parse_ts(ep["poi_updated_at"])
                if not needs_base and conv_ts and poi_updated and poi_updated <= conv_ts and (not poi_ts or poi_ts <= conv_ts):
                    continue
                ok = render_poi(
                    in_path,
                    out_path,
                    out_w,
                    out_h,
                    cfg_start,
                    max_duration,
                    ep["out_codec"],
                    ep["out_frame_rate"],
                    ep,
                    args.dry_run,
                )

            if ok:
                updated_outputs.append(ep["out_id"])
                ran_any = True
            else:
                print(f"ffmpeg failed for output: {out_path}")

        if ran_any:
            ts_now = iso_now()
            conn.execute(
                "UPDATE media_file SET conv_mtime = ? WHERE id = ?",
                (ts_now, media_id),
            )
            for out_id in updated_outputs:
                conn.execute(
                    "UPDATE media_file SET conv_mtime = ? WHERE id = ?",
                    (ts_now, out_id),
                )

        if media["raw_mtime"] is None and raw_ts:
            conn.execute(
                "UPDATE media_file SET raw_mtime = ? WHERE id = ?",
                (raw_ts.isoformat(timespec="seconds").replace("+00:00", "Z"), media_id),
            )

        conn.commit()

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
