#!/usr/bin/env bash
# Regression test for patches/inject.py against the current upstream skin.nimbus.
#   tests/run.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${UPSTREAM_REPO:-https://github.com/ivarbrandt/skin.nimbus}"
REF="${UPSTREAM_REF:-main}"
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT

echo "# clone $REPO@$REF"
git clone --depth 1 -b "$REF" "$REPO" "$W/src" >/dev/null 2>&1
rm -rf "$W/src/.git"
cp -R "$ROOT/overlay/." "$W/src/"

echo "# inject (pass 1)"
python3 "$ROOT/patches/inject.py" "$W/src" 9.9.9.9

echo "# every patched/new file is valid XML"
for f in addon.xml xml/Includes.xml xml/Font.xml colors/defaults.xml \
         xml/DialogPlayerProcessInfo.xml xml/VideoOSD.xml xml/SkinSettings.xml \
         xml/Includes_PPI.xml xml/Variables_PPI.xml xml/Custom_1159_OSD_PPI_VS10.xml; do
  xmllint --noout "$W/src/$f"
done

echo "# markers present"
grep -q 'id="skin.nimbus"'                "$W/src/addon.xml"   # id unchanged (updates in place)
grep -q 'version="9.9.9.9"'               "$W/src/addon.xml"
! grep -q 'id="skin.nimbus.ppi"'          "$W/src/addon.xml"   # must NOT fork the id
grep -q 'Includes_PPI.xml'                "$W/src/xml/Includes.xml"
grep -q 'Variables_PPI.xml'               "$W/src/xml/Includes.xml"
grep -q 'font_tiny_iconic_regular'        "$W/src/xml/Font.xml"
grep -q 'dialog_fg_100'                   "$W/src/colors/defaults.xml"
grep -q '<include>PPI_Modern</include>'   "$W/src/xml/DialogPlayerProcessInfo.xml"
grep -q '<visible>Skin.HasSetting(PPI.ModernMode)</visible>' "$W/src/xml/VideoOSD.xml"  # 717 only when dashboard on
grep -q 'Container(9000).HasFocus(11)'    "$W/src/xml/SkinSettings.xml"
grep -q 'LOCALIZE\[31995\]'               "$W/src/xml/SkinSettings.xml"
grep -q '#31900'                          "$W/src/language/resource.language.en_gb/strings.po"
test "$(grep -c 'id="717"' "$W/src/xml/VideoOSD.xml")" -ge 3               # 2 live 717 buttons + 1 in the commented block
grep -q 'condition="Control.IsVisible(717)">717</onright>' "$W/src/xml/VideoOSD.xml"  # 716 diverts to 717 only when visible

echo "# idempotent (pass 2 makes no change)"
BEFORE="$(find "$W/src" -type f -exec sha1sum {} + | sort | sha1sum)"
python3 "$ROOT/patches/inject.py" "$W/src" 9.9.9.9
AFTER="$(find "$W/src" -type f -exec sha1sum {} + | sort | sha1sum)"
test "$BEFORE" = "$AFTER" || { echo "FAIL: inject.py not idempotent"; exit 1; }

echo "OK"
