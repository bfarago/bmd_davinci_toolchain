#!/usr/bin/env python3
import argparse
import os
import sqlite3
from datetime import datetime, timezone, timedelta


def now_iso(dt=None):
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat(timespec="seconds").replace("+00:00", "Z")


def reset_db(path):
    if os.path.exists(path):
        os.remove(path)


def seed(path, clear_conv):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM media_file LIMIT 1")
    except sqlite3.OperationalError as exc:
        conn.close()
        raise RuntimeError("Database schema missing. Run create_db.py first.") from exc

    if clear_conv:
        cur.execute("UPDATE media_file SET conv_mtime = NULL")
        conn.commit()
        conn.close()
        return

    cur.execute("DELETE FROM edit_point")
    cur.execute("DELETE FROM poi")
    cur.execute("DELETE FROM marker")
    cur.execute("DELETE FROM media_file")
    cur.execute("DELETE FROM camera")

    cur.execute(
        """
        INSERT INTO camera
          (name, note, lens_focal_min, lens_focal_max, lens_stop_min, lens_stop_max, stop_type, lens_note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("A-Cam", "Main camera", 24.0, 70.0, 1.4, 2.8, "T", "Test lens"),
    )
    cam_id = cur.lastrowid

    base_time = datetime.now(timezone.utc) - timedelta(days=2)
    raw_old = now_iso(base_time)
    poi_old = now_iso(base_time + timedelta(hours=2))
    conv_old = now_iso(base_time + timedelta(hours=1))
    conv_new = now_iso(base_time + timedelta(hours=5))

    # Original 1: raw is newer than conv -> full rebuild
    cur.execute(
        """
        INSERT INTO media_file
          (path, kind, width, height, frame_rate, codec, duration, start_time,
           cfg_start, cfg_max_duration, raw_mtime, poi_mtime, conv_mtime, note)
        VALUES (?, 'original', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "media/orig_01.mov",
            1920,
            1080,
            25.0,
            "prores",
            30.0,
            0.0,
            1.0,
            3.0,
            raw_old,
            poi_old,
            conv_old,
            "Needs full rebuild",
        ),
    )
    orig1 = cur.lastrowid

    # Original 2: conv is newer, but one POI is newer -> partial rebuild
    cur.execute(
        """
        INSERT INTO media_file
          (path, kind, width, height, frame_rate, codec, duration, start_time,
           cfg_start, cfg_max_duration, raw_mtime, poi_mtime, conv_mtime, note)
        VALUES (?, 'original', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "media/orig_02.mov",
            3840,
            2160,
            24.0,
            "h264",
            45.0,
            0.0,
            None,
            None,
            raw_old,
            poi_old,
            conv_new,
            "Only POI rebuild",
        ),
    )
    orig2 = cur.lastrowid

    # Output media files (base + poi)
    outputs = []
    for orig_id, label in ((orig1, "01"), (orig2, "02")):
        cur.execute(
            """
            INSERT INTO media_file
              (parent_id, path, kind, width, height, frame_rate, codec, duration,
               cfg_start, cfg_max_duration, note)
            VALUES (?, ?, 'snapshot_base', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                orig_id,
                f"out/orig_{label}_base.mp4",
                320,
                180,
                25.0,
                "h264",
                3.0,
                None,
                3.0,
                "Base snapshot",
            ),
        )
        out_base = cur.lastrowid
        outputs.append((orig_id, out_base, None))

        for idx in range(1, 3):
            cur.execute(
                """
                INSERT INTO media_file
                  (parent_id, path, kind, width, height, frame_rate, codec, duration,
                   cfg_start, cfg_max_duration, note)
                VALUES (?, ?, 'snapshot_poi', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    orig_id,
                    f"out/orig_{label}_poi_{idx}.mp4",
                    320,
                    180,
                    25.0,
                    "h264",
                    3.0,
                    None,
                    3.0,
                    "POI snapshot",
                ),
            )
            outputs.append((orig_id, cur.lastrowid, idx))

    # POIs
    poi_rows = []
    poi_updated_new = now_iso(base_time + timedelta(hours=6))
    poi_updated_old = now_iso(base_time + timedelta(hours=1))

    for orig_id in (orig1, orig2):
        for idx in range(1, 3):
            updated = poi_updated_new if (orig_id == orig2 and idx == 2) else poi_updated_old
            cur.execute(
                """
                INSERT INTO poi (media_id, t, x, y, z, distance, default_camera_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (orig_id, 1.0 * idx, 960 + 20 * idx, 540 + 10 * idx, 1.0 + 0.1 * idx, 3.5, cam_id, updated),
            )
            poi_rows.append((orig_id, idx, cur.lastrowid))

    poi_map = {(orig_id, idx): poi_id for orig_id, idx, poi_id in poi_rows}

    # Markers (review/marker/subtitle/chapter)
    for orig_id in (orig1, orig2):
        cur.execute(
            "INSERT INTO marker (media_id, t, type, text) VALUES (?, ?, ?, ?)",
            (orig_id, 2.0, "review", "Check focus on subject"),
        )
        cur.execute(
            "INSERT INTO marker (media_id, t, type, text) VALUES (?, ?, ?, ?)",
            (orig_id, 5.5, "marker", "Camera shake noticeable"),
        )
        cur.execute(
            "INSERT INTO marker (media_id, t, type, text) VALUES (?, ?, ?, ?)",
            (orig_id, 8.0, "subtitle", "Intro title"),
        )
        cur.execute(
            "INSERT INTO marker (media_id, t, type, text) VALUES (?, ?, ?, ?)",
            (orig_id, 12.0, "chapter", "Scene 1"),
        )

    # Edit points (base + poi)
    for orig_id, out_id, idx in outputs:
        if idx is None:
            cur.execute(
                """
                INSERT INTO edit_point
                  (original_media_id, output_media_id, poi_id, camera_id,
                   camera_name, camera_note, lens_focal_min, lens_focal_max,
                   lens_stop_min, lens_stop_max, stop_type)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (orig_id, out_id, cam_id, "A-Cam", "Main camera", 24.0, 70.0, 1.4, 2.8, "T"),
            )
            continue

        poi_id = poi_map[(orig_id, idx)]
        cur.execute(
            """
            INSERT INTO edit_point
              (original_media_id, output_media_id, poi_id, camera_id,
               poi_t, poi_x, poi_y, poi_z, poi_distance,
               camera_name, camera_note, lens_focal_min, lens_focal_max,
               lens_stop_min, lens_stop_max, stop_type)
            SELECT ?, ?, p.id, ?, p.t, p.x, p.y, p.z, p.distance,
                   c.name, c.note, c.lens_focal_min, c.lens_focal_max,
                   c.lens_stop_min, c.lens_stop_max, c.stop_type
            FROM poi p
            JOIN camera c ON c.id = ?
            WHERE p.id = ?
            """,
            (orig_id, out_id, cam_id, cam_id, poi_id),
        )

    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Seed a test SQLite DB for snapshot tasks.")
    parser.add_argument("--db", default="toweb.db")
    parser.add_argument("--reset-db", action="store_true", help="Delete and recreate the DB")
    parser.add_argument("--clear-conv", action="store_true", help="Clear conv_mtime to force re-run")
    args = parser.parse_args()

    if args.reset_db:
        reset_db(args.db)

    try:
        seed(args.db, args.clear_conv)
    except RuntimeError as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
