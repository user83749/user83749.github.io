# user83749.github.io — Kodi skin mods

Keeps a personal build of the **Nimbus** Kodi skin — `skin.nimbus.ppi` — that adds a
**Player Process Info (PPI) dashboard** and a **VS10 output-mode quick switch** for
P3i / CoreELEC "VS10" Kodi 21 builds, and **rebuilds itself automatically whenever
upstream Nimbus publishes a new version**. Delivered as a Kodi repository on GitHub
Pages, so Kodi auto-updates it in place.

`skin.nimbus.ppi` installs **alongside** stock `skin.nimbus` (separate add-on id) — an
official Nimbus update never touches it, and vice-versa.

## How it works

The modification is almost entirely **additive**, so it isn't a fork:

```
overlay/     new files copied verbatim onto a fresh upstream checkout
             (xml/Includes_PPI.xml, xml/Variables_PPI.xml,
              xml/Custom_1159_OSD_PPI_VS10.xml, media/…, extras/…)
patches/     inject.py — re-applies 8 small anchored edits to upstream files
             (addon.xml, Includes.xml, Font.xml, defaults.xml,
              DialogPlayerProcessInfo.xml, VideoOSD.xml, SkinSettings.xml, strings.po)
             strings_ppi.po — the PPI language strings, appended to upstream's .po
build/       build.sh   — clone upstream → overlay → inject → validate → zip
             make_repo.py — assemble the Pages/Kodi-repository tree
repo-src/    repository.user83749 — the Kodi repository add-on
.github/     sync.yml  — daily: if upstream changed OR overlay/patches changed,
                         rebuild + publish Pages + cut a Release
             test.yml  — runs tests/run.sh on every push/PR
```

`inject.py` is **idempotent** and **fails loudly**: if upstream refactors a file so an
anchor no longer matches, the run goes red and the error names the file + anchor. The
fix is a one-line anchor update in `patches/inject.py`, verified with `tests/run.sh`.

Versioning: the built skin is `<upstream-version>.<serial>` (e.g. `0.1.43.4`), which
always sorts above plain upstream, so Kodi offers the update.

## One-time setup

1. Create a new GitHub repo, push this tree to `main`.
2. **Settings → Pages → Build and deployment → Source = GitHub Actions.**
3. **Actions** tab → *Sync & publish Nimbus PPI* → **Run workflow** (seeds the first build).
4. In Kodi:
   - Keep `repository.ivarbrandt` installed — it provides `script.nimbus.helper`,
     which this skin depends on.
   - *Settings → File manager → Add source* → `https://user83749.github.io/`
   - *Add-ons → Install from zip file* → that source → `repository.user83749-1.0.0.zip`
   - *Install from repository → user83749 Repository → Look and feel → Skin → Nimbus PPI*
   - Enable auto-updates for the skin.

After that it is hands-off. New upstream Nimbus release → daily job rebuilds → Kodi
updates `skin.nimbus.ppi` on its next add-on check.

## Local use

```sh
bash tests/run.sh                     # regression + idempotency check
bash build/build.sh main             # build out/skin.nimbus.ppi-<ver>.zip
python3 build/make_repo.py \
  --skin-dir out/skin.nimbus.ppi \
  --skin-zip out/skin.nimbus.ppi-<ver>.zip \
  --base-url https://user83749.github.io \
  --out out/www
```

`state/last-build.json` only seeds the local `SERIAL`; CI tracks its own state in the
published `www/last-build.json`.

## Changing the mod

Edit files under `overlay/` or `patches/`, push. `test.yml` verifies `inject.py` still
applies cleanly against current upstream; `sync.yml` then rebuilds and republishes with
the serial bumped.

## Requirements to run the scripts

`bash`, `git`, `python3` (3.8+), `zip`, and `xmllint` (`libxml2-utils`).
