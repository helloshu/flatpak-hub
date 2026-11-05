#!/bin/sh
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail || true

LC_ALL=C
export LC_ALL

extra_root="${EXTRA_ROOT:-/app/extra}"
cd "$extra_root"

[ -f app.deb ] || { echo "missing extra-data: app.deb" >&2; exit 1; }

rm -rf stage rssh
mkdir stage
bsdtar -xOf app.deb 'data.tar*' | bsdtar --no-same-owner -xf - -C stage

desktop=$(find stage/usr/share/applications -name '*.desktop' 2>/dev/null | head -n 1 || true)
binary=""
if [ -n "$desktop" ]; then
  binary=$(sed -n 's/^Exec=//p' "$desktop" | head -n 1 | sed 's/ %[A-Za-z]*$//; s:.*/::')
fi
if [ -z "$binary" ] || [ ! -x "stage/usr/bin/$binary" ]; then
  if [ -x "stage/usr/bin/rssh" ]; then
    binary="rssh"
  else
    echo "rssh executable not found in stage/usr/bin" >&2
    exit 1
  fi
fi

mkdir rssh
mv stage/usr rssh/usr
ln -sf "$binary" rssh/usr/bin/com.rssh.app
rm -rf stage app.deb
