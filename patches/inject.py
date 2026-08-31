#!/usr/bin/env python3
"""
inject.py - re-apply the Nimbus PPI modifications onto a fresh upstream
skin.nimbus checkout.

Usage:
    python3 patches/inject.py <upstream_dir> <version>

* Every edit is idempotent: running twice is a no-op.
* If an anchor can no longer be found (upstream refactored the file), the
  script exits non-zero naming the file and the anchor, so CI fails loudly
  and the fix is a one-line anchor update here.

The three brand-new skin files (xml/Includes_PPI.xml, xml/Variables_PPI.xml,
xml/Custom_1159_OSD_PPI_VS10.xml) and the art under media/ + extras/ are NOT
handled here - build.sh copies overlay/ over the checkout before calling this.
"""
import sys
import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
STRINGS_BLOCK = (HERE / "strings_ppi.po").read_text(encoding="utf-8").replace("\r\n", "\n")


class AnchorError(SystemExit):
    def __init__(self, fname, what):
        super().__init__(
            f"inject.py: ANCHOR NOT FOUND in {fname}: {what}\n"
            f"  -> upstream probably refactored this file; update the anchor in patches/inject.py")


def _read(p):
    raw = p.read_bytes()
    return raw.decode("utf-8"), (b"\r\n" in raw)


def _write(p, text, crlf):
    if crlf:
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))


def edit(path, fn):
    if not path.is_file():
        raise AnchorError(str(path), "file does not exist in upstream checkout")
    text, crlf = _read(path)
    norm = text.replace("\r\n", "\n")
    new = fn(norm)
    if new != norm:
        _write(path, new, crlf)
        print(f"  + {path.name}: patched")
    else:
        print(f"  = {path.name}: unchanged (already applied)")


# ---------------------------------------------------------------- addon.xml ---
def patch_addon(text, version):
    if 'id="skin.nimbus.ppi"' in text:
        return text
    if 'id="skin.nimbus"' not in text:
        raise AnchorError("addon.xml", 'id="skin.nimbus"')
    text = text.replace('id="skin.nimbus"', 'id="skin.nimbus.ppi"', 1)
    text = re.sub(r'(<addon\b[^>]*?)\bversion="[^"]*"', rf'\1version="{version}"', text, count=1)
    text = text.replace('name="Nimbus"', 'name="Nimbus PPI"', 1)
    text = re.sub(r'(<summary lang="[^"]*">)([^<]*)(</summary>)',
                  lambda m: m.group(1) + m.group(2).replace("Nimbus", "Nimbus PPI", 1) + m.group(3), text)
    text = re.sub(r'(<description lang="[^"]*">)([^<]*)(</description>)',
                  lambda m: m.group(1) + m.group(2).replace("Nimbus", "Nimbus PPI", 1) + m.group(3), text)
    return text


# ------------------------------------------------------------ Includes.xml ---
def patch_includes(text):
    if "Includes_PPI.xml" in text:
        return text
    if '<include file="Includes_Seekbar.xml" />' not in text:
        raise AnchorError("Includes.xml", '<include file="Includes_Seekbar.xml" />')
    if '<include file="Variables_Seekbar.xml" />' not in text:
        raise AnchorError("Includes.xml", '<include file="Variables_Seekbar.xml" />')
    text = text.replace(
        '<include file="Includes_Seekbar.xml" />',
        '<include file="Includes_Seekbar.xml" />\n\t<include file="Includes_PPI.xml" />', 1)
    text = text.replace(
        '<include file="Variables_Seekbar.xml" />',
        '<include file="Variables_Seekbar.xml" />\n\t<include file="Variables_PPI.xml" />', 1)
    return text


# ----------------------------------------------------------------- Font.xml ---
_FONT_BLOCK = (
    "\n\t\t<!-- PPI - player process info dashboard fonts -->"
    "\n\t\t<font>\n\t\t\t<name>font_tiny</name>\n\t\t\t<filename>Inter-Regular.ttf</filename>\n\t\t\t<size>21</size>\n\t\t</font>"
    "\n\t\t<font>\n\t\t\t<name>font_tiny_iconic_regular</name>\n\t\t\t<filename>remixicon.ttf</filename>\n\t\t\t<size>22</size>\n\t\t\t<style>symbol</style>\n\t\t</font>"
    "\n\t\t<font>\n\t\t\t<name>font_tiny_iconic</name>\n\t\t\t<filename>remixicon.ttf</filename>\n\t\t\t<size>22</size>\n\t\t\t<style>symbol</style>\n\t\t</font>"
)


def patch_font(text):
    if "font_tiny_iconic_regular" in text:
        return text
    pat = re.compile(r'(<font>\s*<name>SmallIcon</name>.*?</font>)', re.DOTALL)
    text, n = pat.subn(lambda m: m.group(1) + _FONT_BLOCK, text)
    if n == 0:
        raise AnchorError("Font.xml", "<font><name>SmallIcon</name>...</font>")
    return text


# ----------------------------------------------------------- defaults.xml ---
_COLOR_BLOCK = (
    "\t<!-- PPI - neutral foreground ramp for the player process info dashboard -->\n"
    '\t<color name="dialog_fg_100">ffededed</color>\n'
    '\t<color name="dialog_fg_90">e7ededed</color>\n'
    '\t<color name="dialog_fg_70">b3ededed</color>\n'
    '\t<color name="dialog_fg_50">80ededed</color>\n'
    '\t<color name="dialog_fg_30">4dededed</color>\n'
    '\t<color name="dialog_fg_12">1fededed</color>\n'
    '\t<color name="dialog_fg_06">0fededed</color>\n'
    '\t<color name="panel_fg_100">ffededed</color>\n'
    '\t<color name="panel_fg_90">e7ededed</color>\n'
    '\t<color name="panel_fg_70">b3ededed</color>\n'
    '\t<color name="panel_fg_30">4dededed</color>\n'
    '\t<color name="panel_fg_12">1fededed</color>\n'
)


def patch_colors(text):
    if "dialog_fg_100" in text:
        return text
    if "</colors>" not in text:
        raise AnchorError("defaults.xml", "</colors>")
    return text.replace("</colors>", _COLOR_BLOCK + "</colors>", 1)


# ---------------------------------------------- DialogPlayerProcessInfo.xml ---
def patch_dppi(text):
    if "PPI_Modern" in text:
        return text
    pat = re.compile(r'(<controls>\n)(\s*)(<control type="group">\n)')
    m = pat.search(text)
    if not m:
        raise AnchorError("DialogPlayerProcessInfo.xml", '<controls> then <control type="group">')
    ind = m.group(2)
    child = ind + "\t"
    repl = (m.group(1)
            + ind + '<!-- PPI "Modern" dashboard; replaces the panel below when enabled -->\n'
            + ind + "<include>PPI_Modern</include>\n"
            + m.group(2) + m.group(3)
            + child + "<visible>!Skin.HasSetting(PPI.ModernMode)</visible>\n")
    return text[:m.start()] + repl + text[m.end():]


# ------------------------------------------------------------- VideoOSD.xml ---
_OSD_CELL_A = """        <!-- PPI / VS10 button -->
        <control type="grouplist">
          <orientation>vertical</orientation>
          <align>center</align>
          <itemgap>-3</itemgap>
          <visible>!Skin.HasSetting(PPI.HideOSDButton)</visible>
          <control type="button" id="717">
            <font>PlayerIconSmall</font>
            <textoffsety>7</textoffsety>
            <align>center</align>
            <include>PlayerButton</include>
            <label>&#xEC9D;</label>
            <onclick condition="System.AddonIsEnabled(service.coreelec.settings)">ActivateWindow(1159)</onclick>
            <onclick condition="!System.AddonIsEnabled(service.coreelec.settings)">ActivateWindow(playerprocessinfo)</onclick>
            <onleft>716</onleft>
            <onright condition="Control.IsVisible(703)">703</onright>
            <onright condition="!Control.IsVisible(703)">704</onright>
          </control>
          <control type="label">
            <top>0</top>
            <left>0</left>
            <height>48</height>
            <width>48</width>
            <font>Font22</font>
            <align>center</align>
            <label></label>
          </control>
        </control>
"""

_OSD_CELL_B = """        <!-- PPI / VS10 button -->
        <control type="grouplist">
          <orientation>vertical</orientation>
          <align>center</align>
          <itemgap>12</itemgap>
          <width>64</width>
          <visible>!Skin.HasSetting(PPI.HideOSDButton)</visible>
          <control type="radiobutton" id="717">
            <include content="OSDButton">
              <param name="texture" value="special://skin/extras/icons/ppi.png"/>
            </include>
            <onclick condition="System.AddonIsEnabled(service.coreelec.settings)">ActivateWindow(1159)</onclick>
            <onclick condition="!System.AddonIsEnabled(service.coreelec.settings)">ActivateWindow(playerprocessinfo)</onclick>
            <onleft>716</onleft>
            <onright condition="Control.IsVisible(703)">703</onright>
            <onright condition="!Control.IsVisible(703)">704</onright>
          </control>
          <control type="label">
            <top>0</top>
            <left>0</left>
            <height>64</height>
            <width>64</width>
            <font>Font12</font>
            <align>center</align>
            <label></label>
          </control>
        </control>
"""


def patch_videoosd(text):
    if "PPI.HideOSDButton" in text:
        return text
    # Each OSD style variant has a settings button id="716" whose cell ends with
    # the standard onleft/onright block, then a small <label> control, then the
    # wrapping <grouplist> closes. Repoint 716 -> 717 and append the new 717 cell.
    pat = re.compile(
        r'(\n\s*<onleft>715</onleft>\n)'
        r'\s*<onright condition="Control\.IsVisible\(703\)">703</onright>\n'
        r'\s*<onright condition="!Control\.IsVisible\(703\)">704</onright>\n'
        r'(\s*</control>\n\s*<control type="label">\n.*?\n\s*</control>\n\s*</control>\n)',
        re.DOTALL)
    cells = iter((_OSD_CELL_A, _OSD_CELL_B))

    def repl(m):
        try:
            cell = next(cells)
        except StopIteration:
            raise AnchorError("VideoOSD.xml", "more than 2 settings-button (716) cells matched")
        return m.group(1) + "          <onright>717</onright>\n" + m.group(2) + cell

    new, n = pat.subn(repl, text)
    if n != 2:
        raise AnchorError("VideoOSD.xml", f"expected exactly 2 settings-button (716) cells, matched {n}")
    return new


# --------------------------------------------------------- SkinSettings.xml ---
_SETTINGS_GROUPLIST = """			<!-- PLAYER INFO / PPI -->
			<control type="grouplist" id="645">
				<top>133</top>
				<left>25</left>
				<right>0</right>
				<bottom>140</bottom>
				<onleft>9000</onleft>
				<onright>60</onright>
				<onup>645</onup>
				<pagecontrol>60</pagecontrol>
				<ondown>645</ondown>
				<visible>Container(9000).HasFocus(11)</visible>
				<control type="radiobutton" id="64501">
					<label>$LOCALIZE[31983]</label>
					<label2>$VAR[PPIModeSettingVar]</label2>
					<include>DefaultSettingButton</include>
					<selected>Skin.HasSetting(PPI.ModernMode)</selected>
					<onclick>Skin.ToggleSetting(PPI.ModernMode)</onclick>
				</control>
				<control type="button" id="64502">
					<label>    - $LOCALIZE[31984]</label>
					<label2>$VAR[PPICodecLogoSettingVar]</label2>
					<include>DefaultSettingButton</include>
					<onclick>$VAR[PPICodecLogoCycleVar]</onclick>
					<visible>Skin.HasSetting(PPI.ModernMode)</visible>
				</control>
				<control type="radiobutton" id="64503">
					<label>    - $LOCALIZE[31985]</label>
					<include>DefaultSettingButton</include>
					<selected>!Skin.HasSetting(PPI.HideChannelLayout)</selected>
					<onclick>Skin.ToggleSetting(PPI.HideChannelLayout)</onclick>
					<visible>Skin.HasSetting(PPI.ModernMode)</visible>
				</control>
				<control type="radiobutton" id="64504">
					<label>    - $LOCALIZE[31986]</label>
					<include>DefaultSettingButton</include>
					<selected>Skin.HasSetting(Filename.PPI)</selected>
					<onclick>Skin.ToggleSetting(Filename.PPI)</onclick>
					<visible>Skin.HasSetting(PPI.ModernMode)</visible>
				</control>
				<control type="radiobutton" id="64505">
					<label>$LOCALIZE[31994]</label>
					<include>DefaultSettingButton</include>
					<selected>Skin.HasSetting(PPI.HideOSDButton)</selected>
					<onclick>Skin.ToggleSetting(PPI.HideOSDButton)</onclick>
				</control>
				<control type="button" id="64506">
					<label>[CAPITALIZE]$LOCALIZE[10116][/CAPITALIZE]</label>
					<include>DefaultSettingButton</include>
					<onclick>Dialog.Close(all)</onclick>
					<onclick>ActivateWindow(playerprocessinfo)</onclick>
					<visible>Player.HasVideo</visible>
				</control>
			</control>
"""

_SETTINGS_ITEM = """					<item id="11">
						<label>$LOCALIZE[31995]</label>
						<onclick>noop</onclick>
					</item>
"""


def patch_skinsettings(text):
    done_group = "Container(9000).HasFocus(11)" in text
    done_item = "LOCALIZE[31995]" in text
    if done_group and done_item:
        return text

    if not done_group:
        pat = re.compile(r'(mode=remove_all_spaths\)</onclick>\n\t+</control>\n\t+</control>\n)')
        text, n = pat.subn(lambda m: m.group(1) + _SETTINGS_GROUPLIST + "\n", text, count=1)
        if n == 0:
            raise AnchorError("SkinSettings.xml", "end of grouplist id=641 (…remove_all_spaths…)")

    if not done_item:
        pat = re.compile(
            r'(<item id="10">\n\t+<label>Extras</label>\n\t+<onclick>noop</onclick>\n\t+</item>\n)')
        text, n = pat.subn(lambda m: m.group(1) + _SETTINGS_ITEM, text, count=1)
        if n == 0:
            raise AnchorError("SkinSettings.xml", '<item id="10"> … </item> (category list)')
    return text


# ------------------------------------------------------------- strings.po ---
def patch_strings(text):
    if "#31900" in text:
        return text
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + STRINGS_BLOCK


# --------------------------------------------------------------------- main ---
def main(argv):
    if len(argv) < 3:
        sys.exit("usage: inject.py <upstream_dir> <version>")
    root = pathlib.Path(argv[1]).resolve()
    version = argv[2]
    if not (root / "addon.xml").is_file():
        sys.exit(f"inject.py: {root} is not a skin.nimbus checkout (no addon.xml)")

    print(f"inject.py: patching {root} as version {version}")
    edit(root / "addon.xml", lambda t: patch_addon(t, version))
    edit(root / "xml/Includes.xml", patch_includes)
    edit(root / "xml/Font.xml", patch_font)
    edit(root / "colors/defaults.xml", patch_colors)
    edit(root / "xml/DialogPlayerProcessInfo.xml", patch_dppi)
    edit(root / "xml/VideoOSD.xml", patch_videoosd)
    edit(root / "xml/SkinSettings.xml", patch_skinsettings)
    edit(root / "language/resource.language.en_gb/strings.po", patch_strings)
    print("inject.py: done")


if __name__ == "__main__":
    main(sys.argv)
