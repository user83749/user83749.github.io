#!/usr/bin/env bash
# Build the modded Nimbus skin from a fresh upstream skin.nimbus checkout
# + overlay + inject.py.
#
#   build/build.sh [upstream_ref]
#
# The build keeps the upstream add-on id ("skin.nimbus") and name ("Nimbus"),
# so Kodi updates it in place and keeps the user's skin settings. The version
# is  <VERSION_BASE>.<SERIAL>  (e.g. 1.6.0) - deliberately far above upstream's
# 0.1.x so the official repo never overrides this build.
#
# env:
#   UPSTREAM_REPO   default: https://github.com/ivarbrandt/skin.nimbus
#   VERSION_BASE    default: contents of state/version-base.txt, else "1.6"
#   SERIAL          default: read from state/last-build.json (".serial"), else 0
#   OUT             default: <repo>/out
#
# Produces:  $OUT/skin.nimbus/                    (built skin folder)
#            $OUT/skin.nimbus-<version>.zip
# Last stdout line:  VERSION=<x>

set -euo pipefail

REF="${1:-main}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_REPO="${UPSTREAM_REPO:-https://github.com/ivarbrandt/skin.nimbus}"
OUT="${OUT:-$ROOT/out}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

BASE="${VERSION_BASE:-$(cat "$ROOT/state/version-base.txt" 2>/dev/null || echo 1.6)}"
BASE="$(echo "$BASE" | tr -d '[:space:]')"
if [ -z "${SERIAL:-}" ]; then
  SERIAL="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("serial",0))' "$ROOT/state/last-build.json" 2>/dev/null || echo 0)"
fi
VERSION="${BASE}.${SERIAL}"

echo ">> cloning $UPSTREAM_REPO @ $REF"
git clone --depth 1 --branch "$REF" "$UPSTREAM_REPO" "$WORK/src" 2>&1 | sed 's/^/   /'
rm -rf "$WORK/src/.git"

UPVER="$(python3 - "$WORK/src/addon.xml" <<'PY'
import sys, re
print(re.search(r'<addon\b[^>]*\bversion="([^"]+)"', open(sys.argv[1], encoding="utf-8").read()).group(1))
PY
)"
echo ">> upstream skin.nimbus $UPVER  ->  building skin.nimbus $VERSION"

if [ "${NOMOD:-}" = "true" ] || [ "${NOMOD:-}" = "1" ]; then
  echo ">> NOMOD set - publishing STOCK Nimbus (no PPI mod), version bump only"
  python3 - "$WORK/src/addon.xml" "$VERSION" <<'PY'
import sys, re, pathlib
p = pathlib.Path(sys.argv[1])
p.write_text(re.sub(r'(<addon\b[^>]*?)\bversion="[^"]*"', r'\1version="%s"' % sys.argv[2],
                    p.read_text(encoding="utf-8"), count=1), encoding="utf-8")
PY
else
  echo ">> applying overlay"
  cp -R "$ROOT/overlay/." "$WORK/src/"
  echo ">> running inject.py"
  python3 "$ROOT/patches/inject.py" "$WORK/src" "$VERSION" "${STAGE:-full}"
fi

echo ">> validating XML"
if [ "${NOMOD:-}" != "true" ] && [ "${NOMOD:-}" != "1" ]; then
  CHANGED="addon.xml xml/Includes.xml xml/Font.xml colors/defaults.xml
           xml/DialogPlayerProcessInfo.xml xml/VideoOSD.xml xml/SkinSettings.xml
           xml/Includes_PPI.xml xml/Variables_PPI.xml xml/Custom_1159_OSD_PPI_VS10.xml"
  for f in $CHANGED; do
    xmllint --noout "$WORK/src/$f"
  done
fi
find "$WORK/src/xml" "$WORK/src/colors" -name '*.xml' -print0 | xargs -0 -n1 xmllint --noout

echo ">> packaging"
mkdir -p "$OUT"
rm -rf "$OUT/skin.nimbus"
mv "$WORK/src" "$OUT/skin.nimbus"
( cd "$OUT" && rm -f "skin.nimbus-$VERSION.zip" \
    && zip -q -r -X "skin.nimbus-$VERSION.zip" skin.nimbus \
       -x '*.DS_Store' -x '*/.git*' )

echo ">> done: $OUT/skin.nimbus-$VERSION.zip  (based on upstream $UPVER)"
echo "UPSTREAM=$UPVER"
echo "VERSION=$VERSION"
