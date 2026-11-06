#!/bin/sh
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail || true

LC_ALL=C
export LC_ALL

extra_root="${EXTRA_ROOT:-/app/extra}"
cd "$extra_root"

[ -f app.deb ] || { echo "missing extra-data: app.deb" >&2; exit 1; }

rm -rf stage dsh
mkdir stage
bsdtar -xOf app.deb 'data.tar*' | bsdtar --no-same-owner -xf - -C stage

# electron-builder installs the application under /opt/<productName>/.
binary=$(find stage/opt -maxdepth 3 -type f -name dsh-desktop-next 2>/dev/null | head -n 1 || true)
if [ -z "$binary" ]; then
  echo "dsh-desktop-next executable not found under stage/opt" >&2
  exit 1
fi
app_dir=$(dirname "$binary")

mkdir dsh
mv "$app_dir" dsh/app
# The setuid sandbox helper cannot work inside Flatpak; zypak provides the sandbox.
rm -f dsh/app/chrome-sandbox
rm -rf stage app.deb
