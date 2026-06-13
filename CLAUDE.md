# Esoteric Beat News — Project Instructions

Entry point for Claude Code sessions in this repo. Read this first.

- **What it is:** a dependency-free static site that aggregates the *complete*
  back catalogues of esoteric-studies podcasts and YouTube channels into one
  browsable index, auto-sorting every episode into thematic **topic tabs**.
- **Working directory:** `C:\Dev\EsotericBeatNews` (this folder). It is a git
  clone of `https://github.com/t3dy/EsotericBeatNews` (`origin/main`).
- **Live site:** https://t3dy.github.io/EsotericBeatNews/
- **Not** NSFRIPPER / ESOFEED. Any doc that references those paths is stale —
  fix it.

## The two-stage pipeline (read before changing anything)

```
sources.json ──> fetch_catalog.py ──> data/catalog.json ──> build.py ──> site/
  (config)        (network, LOCAL)       (committed)         (offline, CI)   (deployed)
```

1. **`fetch_catalog.py`** — network-bound, uses `yt-dlp`. Reads `sources.json`,
   pulls every episode from every source, writes `data/catalog.json`. **Runs
   locally only** — YouTube blocks CI/datacenter IPs, so this never runs in CI.
2. **`build.py`** — offline, Python stdlib only. Reads `data/catalog.json` +
   `sources.json` + `tags.json`, auto-tags each episode into topics, renders
   `site/`. This is what CI runs.
3. **CI** — `.github/workflows/rebuild.yml` runs `build.py` on every push to
   `main` and deploys `site/` to GitHub Pages. `site/` is **gitignored** — it is
   never committed; CI regenerates it. (Older handover notes that say "commit
   /site/" are wrong.)

## How content gets cataloged and sorted into tabs

This is the core invariant the project must always uphold: **every episode that
enters the catalog is automatically sorted into the relevant topic tabs.** That
sorting happens in `auto_tag()` ([build.py](build.py), ~line 166) and runs on
every build. An episode's tags come from three layers, applied in order:

1. **Keyword match** — for each topic in `sources.json` → `topics`, if any of its
   `keywords` appears in the episode's `title + summary` (case-insensitive), the
   episode joins that topic's tab.
2. **Playlist membership** — if the episode is in one of Esoterica's own
   playlists that a topic lists under `playlists`, it inherits that topic
   (uses the creator's own curation as a strong signal).
3. **Manual override** — `tags.json`, keyed by exact episode URL, can `add` or
   `remove` topics. Overrides win.

### Adding a new podcast episode (the common case)

> **Goal: "whenever I add another podcast episode it gets cataloged and sorted
> into the tabs."** The pipeline already guarantees this — you only run the
> fetch + build + push. Sorting is automatic.

- **New episode from a source already in `sources.json`:** nothing to configure.
  Re-run the catalog fetch; the new upload is pulled, auto-tagged, and rendered.
  ```bash
  python fetch_catalog.py        # pulls new uploads into data/catalog.json
  python build.py                # re-tags + re-renders site/ (sanity check locally)
  git add data/catalog.json && git commit -m "Refresh catalog" && git push
  # CI rebuilds + deploys; the new episode appears in the feed and its topic tabs
  ```
- **A brand-new source (whole channel/podcast):** add an entry to `sources` in
  `sources.json` (pick the right `kind` — see below), then run the fetch + build
  + push as above.
- **A single one-off video** that isn't from a tracked channel: add a
  `youtube_videos` source with a `videos: [<id>, ...]` list (see the `dzwiza`
  entry for the pattern), then fetch + build + push.

### If an episode lands in the wrong tabs (or no tab)

The fix is always one of these — never edit `data/catalog.json` by hand (it is
regenerated):

- **Should be in a topic but isn't:** add a keyword to that topic's `keywords`
  in `sources.json`, OR add a per-URL `add` override in `tags.json`.
- **Wrongly tagged into a topic:** tighten the keyword, or add a `remove`
  override in `tags.json`.
- Then re-run `python build.py` and eyeball the topic page before pushing.

## Source kinds (the `kind` field in `sources.json`)

| `kind` | Pulls | Notes |
|---|---|---|
| `podcast` / `podcast_rss` | a podcast RSS/Atom feed | e.g. SHWEP, History of Alchemy |
| `youtube` | a channel's full uploads | needs `channel_id` (`UC…`) or `channel_url` |
| `youtube_channel_filtered` | only uploads whose title matches `filter_title[]` | for mixed channels where you want just the on-topic videos (e.g. Spiritus Mundi → alchemy only) |
| `youtube_playlist` | one playlist | needs `playlist_id` |
| `youtube_videos` | an explicit list of `videos[]` ids | for one-off / featured appearances |
| `composite` | merges multiple `feeds[]` (channel + SoundCloud), de-duped | e.g. Tarot for the Soulless Materialist |

`fetch_playlists: true` on a `youtube` source also pulls its playlists (used for
Esoterica's playlist-membership tagging). `house: true` flags Ted Hand's own
shows. `tab:` overrides the toolbar label.

## Folder / output structure

```
sources.json        # sources, topics (keywords + playlist maps), scholars, branding
tags.json           # manual per-URL tag overrides
fetch_catalog.py    # yt-dlp + RSS  -> data/catalog.json   (LOCAL, network)
build.py            # catalog.json  -> site/               (CI, offline, stdlib)
assets/             # style.css (SHWEP base) + aggregator.css (cards/toolbars)
data/catalog.json   # committed snapshot of every episode + playlist
data/raw/           # per-source fetch caches (gitignored)
site/               # build output (gitignored; CI regenerates + deploys)
  ├── index*.html   # paginated "Latest Emanations" feed
  ├── topics/       # one page per topic tab
  ├── sources/      # one landing page per source
  ├── scholars/     # featured-scholar pages
  └── playlists/    # Esoterica playlist pages
.github/workflows/  # rebuild.yml — build + deploy to Pages
```

## Conventions / guardrails

- **Never hand-edit `data/catalog.json` or anything in `site/`** — both are
  generated. Change `sources.json` / `tags.json` / `*.py` instead, then rebuild.
- **Always run `python build.py` after editing `sources.json`** and visually
  check the affected topic/source pages before committing.
- **Commit `data/catalog.json` after every `fetch_catalog.py` run** — it is the
  source of truth CI builds from.
- CSS is cache-busted by content hash in `build.py`; just rebuild after editing
  CSS and the version token updates itself.
- Pushing to `main` triggers a live deploy. Treat it as an outward-facing action.

## Project docs

- [README.md](README.md) — public-facing overview and local-dev quickstart.
- [HANDOVER.md](HANDOVER.md) — strategy / roadmap / monetization (some figures
  predate the current catalog; treat as direction, not current state).
- [SESSION_SUMMARY.md](SESSION_SUMMARY.md), [DISCOVERING_ADAM_MCLEAN.md](DISCOVERING_ADAM_MCLEAN.md)
  — prior session notes.
