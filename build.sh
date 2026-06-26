#!/bin/sh
# build.sh — preprocess eona.html into platform variants
#
# Usage:
#   ./build.sh web    → dist/web/index.html
#   ./build.sh pi     → dist/pi/clock.html
#   ./build.sh all    → both
#
# Directives (HTML comment syntax, must be on their own line):
#   <!-- @if WEB -->   ... <!-- @endif -->
#   <!-- @if PI -->    ... <!-- @endif -->
#   <!-- @else -->     flips inclusion between @if and @endif
#
# Lines containing only a directive are stripped from output.
# Everything outside directives is included in both builds.

set -e

SOURCE="eona.html"
WEB_OUT="dist/web/index.html"
PI_OUT="dist/pi/clock.html"

if [ ! -f "$SOURCE" ]; then
  echo "error: $SOURCE not found (run from repo root)" >&2
  exit 1
fi

build() {
  TARGET="$1"   # WEB or PI
  OUTFILE="$2"

  mkdir -p "$(dirname "$OUTFILE")"

  awk -v target="$TARGET" '
    BEGIN {
      include = 1   # currently including output
      depth = 0     # nesting depth (0 = top level)
      # stack entries: "include" or "exclude"
      for (i = 0; i < 10; i++) stack[i] = ""
    }

    # @if WEB / @if PI
    /^[[:space:]]*<!--[[:space:]]*@if[[:space:]]+(WEB|PI)[[:space:]]*-->/ {
      # extract platform: grab the token after "@if "
      tmp = $0
      sub(/.*@if[[:space:]]+/, "", tmp)
      sub(/[[:space:]]*-->.*/, "", tmp)
      platform = tmp
      stack[depth] = include ? "active" : "skip"
      depth++
      if (stack[depth-1] == "active" && platform == target) {
        include = 1
      } else {
        include = 0
      }
      next
    }

    # @else
    /^[[:space:]]*<!--[[:space:]]*@else[[:space:]]*-->/ {
      if (depth > 0 && stack[depth-1] == "active") {
        include = !include
      }
      next
    }

    # @endif
    /^[[:space:]]*<!--[[:space:]]*@endif[[:space:]]*-->/ {
      if (depth > 0) {
        depth--
        include = (stack[depth] == "active" || stack[depth] == "")
      }
      next
    }

    # normal line
    { if (include) print }
  ' "$SOURCE" > "$OUTFILE"

  echo "built $OUTFILE ($(wc -l < "$OUTFILE") lines)"
}

case "$1" in
  web)
    build WEB "$WEB_OUT"
    cp -r images dist/web/images
    ;;
  pi)
    build PI "$PI_OUT"
    cp -r images dist/pi/images
    cp -r fonts dist/pi/fonts
    cp -r lib dist/pi/lib
    ;;
  all)
    build WEB "$WEB_OUT"
    cp -r images dist/web/images
    build PI "$PI_OUT"
    cp -r images dist/pi/images
    cp -r fonts dist/pi/fonts
    cp -r lib dist/pi/lib
    ;;
  *)
    echo "usage: $0 web | pi | all" >&2
    exit 1
    ;;
esac
