#!/usr/bin/env bash
set -euo pipefail

shopt -s nullglob

bad_report="bad_report.txt"
ok_report="ok_report.txt"
out_bad="out_bad.txt"

: > "$bad_report"
: > "$ok_report"
: > "$out_bad"

filter_bad_log() {
  # Ignore index/edit-list/timestamp-index warnings in BAD classification/log
  sed -E \
    -e '/edit list/d' \
    -e '/Cannot find an index entry/d' \
    -e '/Missing key frame while searching for timestamp/d'
}

for f in MVI_*.MP4; do
  echo "Checking: $f"

  raw_log="$(ffmpeg -hide_banner -v warning -i "$f" -f null - 2>&1 || true)"
  bad_log="$(printf '%s\n' "$raw_log" | filter_bad_log)"

  if printf '%s\n' "$bad_log" | grep -qi "corrupt"; then
    echo "$f" >> "$out_bad"
    {
      echo "FILE: $f"
      echo "STATUS: CORRUPT (matched: 'corrupt' after filtering)"
      echo "LOG (filtered for bad):"
      if [[ -n "${bad_log//[[:space:]]/}" ]]; then
        printf '%s\n' "$bad_log" | sed 's/^/  /'
      else
        echo "  <empty after filtering>"
      fi
      echo
    } >> "$bad_report"
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

echo "Scan finished."
echo "Bad files list : $out_bad"
echo "Bad report     : $bad_report"
echo "OK report      : $ok_report"