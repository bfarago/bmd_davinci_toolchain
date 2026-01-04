#!/usr/bin/env python3
import argparse
import os
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS camera (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  note TEXT,
  lens_focal_min REAL,
  lens_focal_max REAL,
  lens_stop_min REAL,
  lens_stop_max REAL,
  stop_type TEXT,
  lens_note TEXT
);

CREATE TABLE IF NOT EXISTS media_file (
  id INTEGER PRIMARY KEY,
  parent_id INTEGER REFERENCES media_file(id),
  path TEXT NOT NULL,
  kind TEXT NOT NULL,
  width INTEGER,
  height INTEGER,
  frame_rate REAL,
  codec TEXT,
  duration REAL,
  start_time REAL,
  cfg_start REAL,
  cfg_max_duration REAL,
  raw_mtime TEXT,
  poi_mtime TEXT,
  conv_mtime TEXT,
  note TEXT
);

CREATE TABLE IF NOT EXISTS poi (
  id INTEGER PRIMARY KEY,
  media_id INTEGER NOT NULL REFERENCES media_file(id),
  t REAL,
  x REAL,
  y REAL,
  z REAL,
  distance REAL,
  default_camera_id INTEGER REFERENCES camera(id),
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS edit_point (
  id INTEGER PRIMARY KEY,
  original_media_id INTEGER NOT NULL REFERENCES media_file(id),
  output_media_id INTEGER NOT NULL REFERENCES media_file(id),
  poi_id INTEGER REFERENCES poi(id),
  camera_id INTEGER REFERENCES camera(id),
  poi_t REAL,
  poi_x REAL,
  poi_y REAL,
  poi_z REAL,
  poi_distance REAL,
  camera_name TEXT,
  camera_note TEXT,
  lens_focal_min REAL,
  lens_focal_max REAL,
  lens_stop_min REAL,
  lens_stop_max REAL,
  stop_type TEXT
);

CREATE TABLE IF NOT EXISTS marker (
  id INTEGER PRIMARY KEY,
  media_id INTEGER NOT NULL REFERENCES media_file(id),
  t REAL NOT NULL,
  type TEXT NOT NULL,
  text TEXT
);
"""


def main():
    parser = argparse.ArgumentParser(description="Create SQLite schema for toweb.")
    parser.add_argument("--db", default="toweb.db")
    parser.add_argument("--reset-db", action="store_true", help="Delete and recreate the DB")
    args = parser.parse_args()

    if args.reset_db and os.path.exists(args.db):
        os.remove(args.db)

    conn = sqlite3.connect(args.db)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
