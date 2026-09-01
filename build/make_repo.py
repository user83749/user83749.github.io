#!/usr/bin/env python3
"""
make_repo.py - assemble the GitHub-Pages Kodi repository tree.

    build/make_repo.py --skin-dir out/skin.nimbus.ppi \
                       --skin-zip out/skin.nimbus.ppi-<ver>.zip \
                       --base-url https://<owner>.github.io/<repo> \
                       --out www

Layout produced under --out:

    addons.xml            addons.xml.md5
    zips/skin.nimbus.ppi/skin.nimbus.ppi-<ver>.zip        (+ addon.xml, icon)
    zips/repository.nimbus.ppi/repository.nimbus.ppi-<rver>.zip (+ addon.xml, icon)
    repository.nimbus.ppi-<rver>.zip                      (root copy, for "install from zip")
    index.html
"""
import argparse
import hashlib
import pathlib
import re
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    REPO_SRC = next(p for p in sorted((ROOT / "repo-src").glob("repository.*")) if p.is_dir())
except StopIteration:
    sys.exit("make_repo.py: no repo-src/repository.* add-on found")


def addon_block(addon_xml_text):
    """Return the <addon ...>...</addon> element with any XML prolog stripped."""
    m = re.search(r"<addon\b.*?</addon>", addon_xml_text, re.DOTALL)
    if not m:
        sys.exit("make_repo.py: could not find <addon> in addon.xml")
    return m.group(0).strip()


def addon_attrs(addon_xml_text):
    m = re.search(r'<addon\b[^>]*\bid="([^"]+)"[^>]*\bversion="([^"]+)"', addon_xml_text)
    if not m:
        m2 = re.search(r'<addon\b[^>]*\bversion="([^"]+)"[^>]*\bid="([^"]+)"', addon_xml_text)
        if not m2:
            sys.exit("make_repo.py: addon.xml missing id/version")
        return m2.group(2), m2.group(1)
    return m.group(1), m.group(2)


def md5_file(path):
    h = hashlib.md5()
    h.update(path.read_bytes())
    return h.hexdigest()


def zipdir(src_dir: pathlib.Path, arc_top: str, dest_zip: pathlib.Path):
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src_dir.rglob("*")):
            if p.is_file() and ".git" not in p.parts and p.name != ".DS_Store":
                z.write(p, f"{arc_top}/{p.relative_to(src_dir).as_posix()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skin-dir", required=True)
    ap.add_argument("--skin-zip", required=True)
    ap.add_argument("--base-url", required=True, help="e.g. https://user.github.io/nimbus-ppi")
    ap.add_argument("--out", default="www")
    a = ap.parse_args()

    base = a.base_url.rstrip("/")
    out = pathlib.Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    skin_dir = pathlib.Path(a.skin_dir)
    skin_zip = pathlib.Path(a.skin_zip)
    skin_axml = (skin_dir / "addon.xml").read_text(encoding="utf-8")
    skin_id, skin_ver = addon_attrs(skin_axml)

    # --- repository addon: substitute @@BASEURL@@, (re)build its zip ------------
    repo_axml_src = (REPO_SRC / "addon.xml").read_text(encoding="utf-8")
    repo_axml = repo_axml_src.replace("@@BASEURL@@", base)
    repo_id, repo_ver = addon_attrs(repo_axml)

    staged_repo = out / "_stage" / repo_id
    staged_repo.mkdir(parents=True)
    (staged_repo / "addon.xml").write_text(repo_axml, encoding="utf-8")
    for extra in ("icon.png", "fanart.jpg"):
        if (REPO_SRC / extra).is_file():
            shutil.copy2(REPO_SRC / extra, staged_repo / extra)

    # --- zips/ tree -----------------------------------------------------------
    zdir_skin = out / "zips" / skin_id
    zdir_repo = out / "zips" / repo_id
    zdir_skin.mkdir(parents=True)
    zdir_repo.mkdir(parents=True)

    shutil.copy2(skin_zip, zdir_skin / f"{skin_id}-{skin_ver}.zip")
    shutil.copy2(skin_dir / "addon.xml", zdir_skin / "addon.xml")
    for ic in ("resources/icon.png", "icon.png"):
        if (skin_dir / ic).is_file():
            shutil.copy2(skin_dir / ic, zdir_skin / "icon.png")
            break

    repo_zip_name = f"{repo_id}-{repo_ver}.zip"
    zipdir(staged_repo, repo_id, zdir_repo / repo_zip_name)
    shutil.copy2(staged_repo / "addon.xml", zdir_repo / "addon.xml")
    if (staged_repo / "icon.png").is_file():
        shutil.copy2(staged_repo / "icon.png", zdir_repo / "icon.png")
    # root copy so users can "install from zip" via a stable-ish URL
    shutil.copy2(zdir_repo / repo_zip_name, out / repo_zip_name)

    shutil.rmtree(out / "_stage")

    # --- addons.xml + md5 ---------------------------------------------------------
    addons_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<addons>\n'
        + addon_block(repo_axml) + "\n"
        + addon_block(skin_axml) + "\n"
        + "</addons>\n"
    )
    (out / "addons.xml").write_text(addons_xml, encoding="utf-8")
    (out / "addons.xml.md5").write_text(
        hashlib.md5(addons_xml.encode("utf-8")).hexdigest() + "\n", encoding="utf-8")

    # --- index.html -------------------------------------------------------------
    # The ONLY <a href> is the repository zip, so Kodi's "Install from zip file"
    # browser shows exactly one selectable entry. addons.xml / md5 / the zips/
    # datadir are still served by direct URL (that's all the repo needs) but are
    # deliberately not linked here, so they don't clutter the picker.
    (out / "index.html").write_text(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Nimbus PPI repository</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:44rem;margin:3rem auto;padding:0 1rem}}
code{{background:#eee;padding:.1em .3em;border-radius:3px}}</style></head><body>
<h1>Nimbus PPI &ndash; Kodi repository</h1>
<p>Skin build: <code>{skin_id} {skin_ver}</code></p>
<p>Repository add-on: <a href="{repo_zip_name}">{repo_zip_name}</a></p>
<h2>Install</h2>
<ol>
<li>Kodi &rarr; <em>Settings &rarr; File manager &rarr; Add source</em> &rarr; <code>{base}/</code></li>
<li><em>Add-ons &rarr; Install from zip file</em> &rarr; that source &rarr; <code>{repo_zip_name}</code></li>
<li><em>Install from repository &rarr; Nimbus PPI Repository &rarr; Look and feel &rarr; Skin &rarr; Nimbus PPI</em></li>
</ol>
<p>Keep <code>repository.ivarbrandt</code> installed too &ndash; it provides
<code>script.nimbus.helper</code>, which this skin depends on.</p>
</body></html>
""", encoding="utf-8")

    print(f"make_repo.py: wrote {out}/  (skin {skin_id} {skin_ver}, repo {repo_id} {repo_ver})")


if __name__ == "__main__":
    main()
