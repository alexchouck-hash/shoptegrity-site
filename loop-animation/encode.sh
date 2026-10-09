#!/usr/bin/env bash
set -euo pipefail

# Ensure gifski and ffmpeg are discoverable on Windows / Git Bash / macOS / Linux
export PATH="$PATH:/c/Program Files/gifski:/c/Program Files (x86)/gifski:/usr/local/bin"

mkdir -p out

# GIF (gifski: best quality per byte)
echo "Encoding GIF with gifski..."
gifski --fps 20 --width 760 --quality 80 -o out/loop.gif frames/f_*.png

# Check GIF size: if > 10MB, optimize as per spec
GIF_SIZE=$(stat -c%s out/loop.gif 2>/dev/null || stat -f%z out/loop.gif 2>/dev/null || echo 0)
if [ "$GIF_SIZE" -gt 10485760 ]; then
  echo "GIF is over 10MB ($(($GIF_SIZE / 1024 / 1024))MB), re-encoding with --quality 65..."
  gifski --fps 20 --width 760 --quality 65 -o out/loop.gif frames/f_*.png
  GIF_SIZE=$(stat -c%s out/loop.gif 2>/dev/null || stat -f%z out/loop.gif 2>/dev/null || echo 0)
  if [ "$GIF_SIZE" -gt 10485760 ]; then
    echo "Still over 10MB, re-encoding with --fps 15..."
    gifski --fps 15 --width 760 --quality 65 -o out/loop.gif frames/f_*.png
    GIF_SIZE=$(stat -c%s out/loop.gif 2>/dev/null || stat -f%z out/loop.gif 2>/dev/null || echo 0)
    if [ "$GIF_SIZE" -gt 10485760 ]; then
      echo "Still over 10MB, re-encoding with --width 640..."
      gifski --fps 15 --width 640 --quality 65 -o out/loop.gif frames/f_*.png
    fi
  fi
fi

# MP4 (H.264, universally playable)
echo "Encoding MP4 with ffmpeg..."
ffmpeg -y -framerate 20 -i frames/f_%04d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -preset slow -movflags +faststart out/loop.mp4

# WebM (VP9, smallest)
echo "Encoding WebM with ffmpeg..."
ffmpeg -y -framerate 20 -i frames/f_%04d.png \
  -c:v libvpx-vp9 -pix_fmt yuv420p -crf 32 -b:v 0 out/loop.webm

# Poster = final frame (also the reduced-motion still)
echo "Generating poster..."
cp frames/f_0479.png out/loop_poster.png

echo "Done! Output files:"
ls -lh out/
