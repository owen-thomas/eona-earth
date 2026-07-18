#!/bin/sh
# build.sh — preprocess eona.html into platform variants
#
# Usage:
#   ./build.sh web    → dist/web/index.html
#   ./build.sh pi     → dist/pi/clock.html
#   ./build.sh all    → both (also the default with no args)
#   ./build.sh check  → build both targets to a temp dir, validate, and
#                       diff the generated HTML against dist/ (no files written)
#
# Directives (HTML comment syntax, must be on their own line):
#   <!-- @if WEB -->          ... <!-- @endif -->
#   <!-- @if PI -->           ... <!-- @endif -->
#   <!-- @if WEB|DESKTOP -->  ... <!-- @endif -->   (OR list — any listed platform matches)
#   <!-- @else -->            flips inclusion between @if and @endif
#
# Lines containing only a directive are stripped from output.
# Everything outside directives is included in every build.
#
# Adding a platform: add its token to PLATFORMS below. No awk/regex edit needed.
#
# Must run on both macOS (bash, BSD awk) and Raspberry Pi OS (dash, mawk) —
# keep the awk below POSIX-only: no gensub, no 4-arg split.

set -e

SOURCE="eona.html"
WEB_OUT="dist/web/index.html"
PI_OUT="dist/pi/clock.html"
PLATFORMS="WEB PI"

if [ ! -f "$SOURCE" ]; then
  echo "error: $SOURCE not found (run from repo root)" >&2
  exit 1
fi

# copy_assets <src-dir> <dest-dir>
# rm -rf the destination first so re-runs can't nest a copy inside a
# previous one (the historical dist/pi/fonts/fonts/ bug).
copy_assets() {
  rm -rf "$2"
  mkdir -p "$(dirname "$2")"
  cp -R "$1" "$2"
}

# build <TARGET> <outfile>
# Writes to <outfile>.tmp, validates, then moves into place. A failed
# build never touches an existing good <outfile>.
build() {
  TARGET="$1"
  OUTFILE="$2"
  TMPFILE="$OUTFILE.tmp"

  # Build stamp — substituted for every __BUILD_INFO__ token. Format is a
  # stable protocol (see BUILD-SYSTEM-PLAN.md D1): "<platform> <sha>[-dirty]
  # <iso-date>", one line. The desktop app's remote-content loader will diff
  # these to decide freshness — don't reformat without updating that reader.
  # `git diff --quiet HEAD` (not just against the index) so a staged-but-
  # uncommitted edit still marks the stamp dirty.
  platform_lc=$(echo "$TARGET" | tr 'A-Z' 'a-z')
  sha=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
  dirty=""
  git diff --quiet HEAD -- "$SOURCE" 2>/dev/null || dirty="-dirty"
  date_iso=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  buildinfo="$platform_lc $sha$dirty $date_iso"

  mkdir -p "$(dirname "$OUTFILE")"

  awk -v target="$TARGET" -v platforms="$PLATFORMS" -v buildinfo="$buildinfo" '
    BEGIN {
      include = 1   # currently including output
      depth = 0     # nesting depth (0 = top level)
      fatal = 0
      nplat = split(platforms, plist, " ")
      for (i = 1; i <= nplat; i++) valid[plist[i]] = 1
    }

    # @if TOKEN[|TOKEN...]
    /^[[:space:]]*<!--[[:space:]]*@if[[:space:]]+[A-Za-z_|]+[[:space:]]*-->/ {
      tmp = $0
      sub(/.*@if[[:space:]]+/, "", tmp)
      sub(/[[:space:]]*-->.*/, "", tmp)
      token = tmp

      nparts = split(token, parts, "|")
      matched = 0
      for (i = 1; i <= nparts; i++) {
        p = parts[i]
        if (!(p in valid)) {
          print "error: unknown platform token \"" p "\" in @if directive (" token ")" > "/dev/stderr"
          fatal = 1
          exit 1
        }
        if (p == target) matched = 1
      }

      stack[depth] = include ? "active" : "skip"
      depth++
      if (stack[depth-1] == "active" && matched) {
        include = 1
      } else {
        include = 0
      }
      next
    }

    # @else
    /^[[:space:]]*<!--[[:space:]]*@else[[:space:]]*-->/ {
      if (depth == 0) {
        print "error: @else with no matching @if" > "/dev/stderr"
        fatal = 1
        exit 1
      }
      if (stack[depth-1] == "active") {
        include = !include
      }
      next
    }

    # @endif
    /^[[:space:]]*<!--[[:space:]]*@endif[[:space:]]*-->/ {
      if (depth == 0) {
        print "error: @endif with no matching @if" > "/dev/stderr"
        fatal = 1
        exit 1
      }
      depth--
      include = (stack[depth] == "active" || stack[depth] == "")
      next
    }

    # normal line — buildinfo is plain lowercase/digits/dashes/colons/T/Z,
    # so it is safe as a gsub replacement string without escaping; awk
    # treats & and \ specially there, so preserve that constraint if the
    # stamp format ever changes.
    { if (include) { gsub(/__BUILD_INFO__/, buildinfo); print } }

    END {
      if (fatal) exit 1
      if (depth != 0) {
        print "error: unbalanced @if/@endif (depth=" depth " at EOF)" > "/dev/stderr"
        exit 1
      }
    }
  ' "$SOURCE" > "$TMPFILE"

  # B3: catch directive residue that slipped past the awk pass (e.g. a
  # malformed directive that never matched a rule and was printed verbatim).
  if grep -qE '<!--[[:space:]]*@(if|else|endif)' "$TMPFILE"; then
    echo "error: $TMPFILE still contains @if/@else/@endif residue" >&2
    exit 1
  fi

  mv "$TMPFILE" "$OUTFILE"
  echo "built $OUTFILE ($(wc -l < "$OUTFILE") lines)"
}

do_web() {
  build WEB "$WEB_OUT"
  copy_assets images dist/web/images
}

do_pi() {
  build PI "$PI_OUT"
  copy_assets images dist/pi/images
  copy_assets fonts dist/pi/fonts
  copy_assets lib dist/pi/lib
}

# check: build both targets into a temp dir (also exercises full validation),
# then diff only the generated HTML against dist/ — asset dirs are verbatim
# copies and just add noise when dist/ is stale.
do_check() {
  tmp_dir=$(mktemp -d)
  trap 'rm -rf "$tmp_dir"' EXIT INT TERM

  build WEB "$tmp_dir/web-index.html"
  build PI "$tmp_dir/pi-clock.html"

  for pair in "web:$WEB_OUT:$tmp_dir/web-index.html" "pi:$PI_OUT:$tmp_dir/pi-clock.html"; do
    name=${pair%%:*}
    rest=${pair#*:}
    old=${rest%%:*}
    new=${rest#*:}

    echo ""
    echo "--- $name ($old) ---"
    if [ ! -f "$old" ]; then
      echo "(no existing $old to compare)"
      continue
    fi
    changed=$(diff -u "$old" "$new" | grep -c '^[+-][^+-]' || true)
    if [ "$changed" -eq 0 ]; then
      echo "unchanged"
    else
      echo "$changed line(s) differ:"
      diff -u "$old" "$new" || true
    fi
  done
}

usage() {
  echo "usage: $0 [web | pi | all | check]  (default: all)" >&2
}

case "${1:-all}" in
  web)
    do_web
    ;;
  pi)
    do_pi
    ;;
  all)
    do_web
    do_pi
    ;;
  check)
    do_check
    ;;
  *)
    usage
    exit 1
    ;;
esac
