## MVI MP4 corrupt-frame scan and fix

These scripts were created for a project with many video files where a bad SD
card caused frequent corrupt frames. The corrupt frames were not obvious during
normal playback, but DaVinci Resolve stops during render when it hits a corrupt
frame. The scripts help you identify affected files and optionally fix them.

## Requirements

- `ffmpeg` available on your PATH.

## How it works (both scripts)

- Put the script in the folder that contains your video files named
  `MVI_*.MP4`.
- Run the script from that folder.
- The scripts run `ffmpeg` in warning mode, filter out known non-critical
  warnings, and classify a file as corrupt when the filtered log contains
  `corrupt`.

Reports are written to:

- `out_bad.txt` list of corrupt files (one per line).
- `bad_report.txt` detailed report for corrupt files.
- `ok_report.txt` detailed report for clean files.

## scan_mvi.sh (scan only)

This script scans and reports corrupt files without modifying your media.

Run:

```bash
./scan_mvi.sh
```

## fix_mvi.sh (scan + fix)

This script scans and fixes corrupt files. The fix is done by re-encoding the
video to H.264 (CRF 18, slow preset) while copying audio, then rewriting the
container with `-movflags +faststart`.

Run:

```bash
./fix_mvi.sh
```

Behavior on corrupt files:

- The original file is renamed to `CORRUPT_<original_name>`.
- The fixed file is written back with the original file name.
- Reports are updated as described above.

Backup location:

- By default, corrupt originals are stored in the same folder.
- You can change this by editing `backup_dir` at the top of `fix_mvi.sh`.
