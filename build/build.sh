#!/usr/bin/env bash
# Build skin.nimbus.ppi from a fresh upstream skin.nimbus checkout + overlay + inject.py
#
#   build/build.sh [upstream_ref]
#
# env:
#   UPSTREAM_REPO   default: https://github.com/ivarbrandt/skin.nimbus
#   SERIAL          default: read from state/last-build.json (".serial"), else 1
#   OUT             default: <repo>/out
#
# Produces:  $OUT/skin.nimbus.ppi/                 (the built skin folder)
#            $OUT/skin.nimbus.ppi-<version>.zip
# and prints the resolved version to stdout as the last line: VERSION=<x>

set -euo pipefail

REF="${1:-main}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/ivarbrandt/skin.nimbus}"
OUT="${OUT:-$ROOT/out}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

if [ -z "${SERIAL:-}" ]; then
  SERIAL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("serial",1))' "$ROOT/state/last-build.json" 2>/dev/null || echo 1)"
fi

echo ">> cloning $UPSTREAM_REPO @ $REF"
git clone --depth 1 --branch "$REF" "$UPSTREAM_REPO" "$WORK/src" 2>&1 | sed 's/^/   /'
rm -rf "$WORK/src/.git"

UPVER="$(python3 - "$WORK/src/addon.xml" <<'PY'
import sys,re
print(re.search(r'<addon\b[^>]*\bversion="([^"]+)"', open(sys.argv[1],encoding="utf-8").read()).group(1))
PY
)"
VERSION="${UPVER}.${SERIAL}"
echo ">> upstream version $UPVER  ->  skin.nimbus.ppi $VERSION"

echo ">> applying overlay"
cp -R "$ROOT/overlay/." "$WORK/src/"

echo ">> running inject.py"
python3 "$ROOT/patches/inject.py" "$WORK/src" "$VERSION"

echo ">> validating XML"
CHANGED="addon.xml xml/Includes.xml xml/Font.xml colors/defaults.xml
         xml/DialogPlayerProcessInfo.xml xml/VideoOSD.xml xml/SkinSettings.xml
         xml/Includes_PPI.xml xml/Variables_PPI.xml xml/Custom_1159_OSD_PPI_VS10.xml"
for f in $CHANGED; do
  xmllint --noout "$WORK/src/$f"
done
# full skin sweep (best effort - upstream is expected to be clean)
find "$WORK/src/xml" "$WORK/src/colors" -name '*.xml' -print0 | xargs -0 -n1 xmllint --noout

echo ">> packaging"
mkdir -p "$OUT"
rm -rf "$OUT/skin.nimbus.ppi"
mv "$WORK/src" "$OUT/skin.nimbus.ppi"
( cd "$OUT" && rm -f "skin.nimbus.ppi-$VERSION.zip" \
    && zip -q -r -X "skin.nimbus.ppi-$VERSION.zip" skin.nimbus.ppi \
       -x '*.DS_Store' -x '*/.git*' )

echo ">> done: $OUT/skin.nimbus.ppi-$VERSION.zip"
echo "VERSION=$VERSION"
