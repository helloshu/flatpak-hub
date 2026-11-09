#!/bin/sh
set -eu
(set -o pipefail) 2>/dev/null && set -o pipefail || true

LC_ALL=C
export LC_ALL

extra_root="${EXTRA_ROOT:-/app/extra}"
cd "$extra_root"

[ -f app.deb ] || { echo "missing extra-data: app.deb" >&2; exit 1; }

rm -rf stage odg
mkdir stage
bsdtar -xOf app.deb 'data.tar*' | bsdtar --no-same-owner -xf - -C stage

if [ ! -x stage/opt/OneDriveGUI/onedrive-gui ]; then
  echo "OneDriveGUI launcher not found at stage/opt/OneDriveGUI/onedrive-gui" >&2
  exit 1
fi

mv stage/opt/OneDriveGUI odg
rm -rf stage app.deb
