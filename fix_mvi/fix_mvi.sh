#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

bad_report="bad_report.txt"
ok_report="ok_report.txt"
out_bad="out_bad.txt"

# If you want a dedicated folder for backups, set e.g. backup_dir="./_corrupt_backup"
backup_dir="."

: > "$bad_report"
: > "$ok_report"
: > "$out_bad"

filter_bad_log() {
  sed -E \
    -e '/edit list/d' \
    -e '/Cannot find an index entry/d' \
    -e '/Missing key frame while searching for timestamp/d'
}

fix_file() {
  local f="$1"
  local base
  base="$(basename "$f")"
  local dir
  dir="$(dirname "$f")"

  local backup="${backup_dir%/}/CORRUPT_${base}"
  local tmp="${dir%/}/.__FIXING__.${base}"
  local tmp2="${dir%/}/.__FIXING2__.${base}"

  # Backup original (only if backup doesn't exist yet)
  if [[ ! -f "$backup" ]]; then
    mv -f "$f" "$backup"
  else
    # If backup exists, assume original was already moved earlier; ensure we don't overwrite it.
    rm -f "$f" || true
  fi

  # Re-encode to a robust stream (H.264/AAC copy) in MP4
  # Keep format: MP4, keep audio as-is.
  # Pixel format: keep 4:2:0 (matches your source subsampling).
  # CRF 18: high quality.
  ffmpeg -hide_banner -y -err_detect ignore_err -i "$backup" \
    -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p \
    -c:a copy \
    "$tmp"

  # Rewrite container once more to be safe (faststart)
  ffmpeg -hide_banner -y -i "$tmp" -c copy -movflags +faststart "$tmp2"
  rm -f "$tmp"

  # Put fixed file back under original name
  mv -f "$tmp2" "$f"
}

for f in MVI_*.MP4; do
  echo "Checking: $f"

  raw_log="$(ffmpeg -hide_banner -v warning -i "$f" -f null - 2>&1 || true)"
  bad_log="$(printf '%s\n' "$raw_log" | filter_bad_log)"

  if printf '%s\n' "$bad_log" | grep -qi "corrupt"; then
    echo "$f" >> "$out_bad"
    {
      echo "FILE: $f"
      echo "STATUS: CORRUPT (matched 'corrupt' after filtering)"
      echo "LOG (filtered for bad):"
      if [[ -n "${bad_log//[[:space:]]/}" ]]; then
        printf '%s\n' "$bad_log" | sed 's/^/  /'
      else
        echo "  <empty after filtering>"
      fi
      echo "ACTION: fixing -> backup as CORRUPT_*, fixed back to original name"
      echo
    } >> "$bad_report"

    fix_file "$f"

  else
    {
      echo "FILE: $f"
      echo "STATUS: OK (no 'corrupt' after filtering)"
      echo "LOG (raw):"
      if [[ -n "${raw_log//[[:space:]]/}" ]]; then
        printf '%s\n' "$raw_log" | sed 's/^/  /'
      else
        echo "  <empty>"
      fi
      echo
    } >> "$ok_report"
  fi
done

echo "Scan+fix finished."
echo "Bad files list : $out_bad"
echo "Bad report     : $bad_report"
echo "OK report      : $ok_report"