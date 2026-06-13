# Esoteric Beat News

### 🔮 Live site → **https://t3dy.github.io/EsotericBeatNews/**

A dark-academic static site that gathers the **complete back catalogues** of a
handful of esoteric-studies podcasts and YouTube channels into one place:

- **Latest Emanations** — the marquee landing feed: *every* episode from every
  source, in chronological order, as scrollable cards (paginated). It sits in
  the main **site-features toolbar**, set off from the other features.
- **Featured Podcasts toolbar** — a tab per show; each opens a landing page with
  only that podcast's episodes.
- **Topics toolbar** — its own bar of 20 curated cross-channel currents:
  Neoplatonism, Grimoires, Kabbalah, Renaissance Magic, Ancient Magic, Medieval
  Magic, Agrippa, Ficino, Alchemy, Audiobooks, Conferences, History of Magic,
  Mysticism, Hermeticism, Occultism, Wicca, Witchcraft, Gnosticism, Demonology,
  Astrology. Every episode is auto-sorted into these tabs at build time.
- **Featured Scholars toolbar** — a tab per featured scholar (Hutton, Yates,
  Forshaw, Newman, Principe, Dzwiza), each linking to a page of their episodes.
- **Curated Playlists** — a section for each of Esoterica's own 28 thematic
  playlists (Kabbalah, Solomonic Magic, Ancient Near East, Gnosticism, …).

Every card links out to the creator's own page. Nothing is rehosted — all
content belongs to its makers; please subscribe to and support them directly.

## Sources

**25 sources** are defined in `sources.json` (≈3,000 episodes total) — podcasts,
full YouTube channels, title-filtered channels, playlists, and one-off video
lists. A representative sample:

| Source | Type | Episodes |
|---|---|---|
| [SHWEP](https://shwep.net) — The Secret History of Western Esotericism Podcast | Podcast (RSS) | ~218 |
| [Esoterica](https://www.youtube.com/channel/UCoydhtfFSk1fZXNRnkGnneQ) (Dr. Justin Sledge) | YouTube | ~373 + 28 playlists |
| [The Modern Hermeticist](https://www.youtube.com/channel/UCcluftdk1tuDU71ZdGNpHTA) | YouTube | ~249 |
| [Seekers of Unity](https://www.youtube.com/channel/UCL9A83sJIYNAovCA92uaTRQ) | YouTube | ~225 |
| [Esoteric Beat](https://www.youtube.com/playlist?list=PL44vk5wOpZBkFRSHcia1KNP0OJoUpd8Jk) (Ted Hand) | YouTube playlist | ~8 |
| [Tarot for the Soulless Materialist](https://soundcloud.com/faderanger93) (Ted Hand) | YouTube + SoundCloud | ~5 |

…plus channels for alchemy and esoteric studies from Angela's Symposium,
Religion for Breakfast, Glitch Bottle, Hermitix, Adam McLean, Matteo Martelli,
the Warburg Institute, and the Newman/Principe alchemy lecture channels, among
others. The full list lives in `sources.json`.

Each source declares a `kind` that controls how it is fetched:

| `kind` | Pulls |
|---|---|
| `podcast` / `podcast_rss` | a podcast RSS/Atom feed |
| `youtube` | a channel's complete uploads (`channel_id` / `channel_url`) |
| `youtube_channel_filtered` | only uploads whose title matches `filter_title[]` — for mixed channels where you want just the on-topic videos |
| `youtube_playlist` | a single playlist |
| `youtube_videos` | an explicit `videos[]` id list — for one-off / featured appearances |
| `composite` | merges multiple feeds (channel + SoundCloud), de-duplicating the same episode across platforms |

YouTube is scraped via `yt-dlp` (no API key); SoundCloud also uses `yt-dlp`
(install `curl_cffi` for full listings).

## Tech stack

Deliberately minimal — no framework, no JavaScript runtime, no API keys.

| Layer | Choice | Why |
|---|---|---|
| **Catalog fetch** | [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) + Python `urllib` | YouTube's RSS feed only returns the latest ~15 videos; `yt-dlp` scrapes the **full** upload list and every playlist with no API key. SHWEP comes from its podcast RSS. |
| **Data store** | `data/catalog.json` (committed) | A plain JSON snapshot of all episodes + playlists. Committed to the repo so builds are reproducible and CI never has to touch YouTube. |
| **Renderer** | Python 3.9+ **standard library only** | Reads `catalog.json`, auto-tags episodes into topics, emits static HTML. Zero build dependencies. |
| **Styling** | Hand-written CSS with custom properties | Dark-academic ["SHWEP" design system](https://shwep.net) — Georgia headings, system-sans body, `#1a1a1a` palette. No web fonts, no CSS framework. |
| **Hosting** | GitHub Pages | Free static hosting. |
| **CI/CD** | GitHub Actions (`.github/workflows/rebuild.yml`) | Renders `site/` from the committed catalog and deploys to Pages on every push. |

### Why fetch and build are split

`fetch_catalog.py` (network-bound, uses `yt-dlp`) is separate from `build.py`
(offline, stdlib-only). YouTube frequently blocks datacenter IP ranges, so
running `yt-dlp` *inside* CI is unreliable. Instead the catalog is fetched
**locally**, committed as `data/catalog.json`, and CI only does the offline
render. Refreshing the catalog = re-run the fetcher and push.

## Repository layout

```
sources.json          # sources, the 20 curated topics (keywords + playlist maps), scholars, branding
fetch_catalog.py      # yt-dlp + RSS  -> data/catalog.json   (slow, network, run locally)
build.py              # data/catalog.json -> site/           (fast, offline, runs in CI)
tags.json             # optional manual tag overrides per episode URL
assets/               # style.css (SHWEP base) + aggregator.css (cards, grid, pagination)
data/catalog.json     # committed snapshot of every episode + playlist
data/raw/             # per-source yt-dlp/RSS dumps (cache; gitignored)
site/                 # build output (gitignored; produced by CI)
.github/workflows/    # rebuild + deploy to Pages
```

## Local development

```bash
# 1. Refresh the catalog (needs network access to youtube.com; run locally)
python -m pip install --upgrade yt-dlp
python fetch_catalog.py            # writes data/catalog.json
python fetch_catalog.py --cache    # re-assemble from data/raw/ without re-fetching

# 2. Render the static site (offline, stdlib only)
python build.py                    # writes site/

# 3. Preview
python -m http.server 8099 --directory site   # http://localhost:8099
```

## Adding episodes & sorting into tabs

Every episode that enters the catalog is **automatically sorted into its topic
tabs** by `build.py` — keyword matches on its title + summary, Esoterica
playlist membership, and any manual `tags.json` overrides. You never assign tabs
by hand; you only refresh and rebuild.

- **New episode from a source already listed** — just refresh:
  `python fetch_catalog.py` → `python build.py` → commit `data/catalog.json` →
  push. The new upload is pulled, auto-tagged, and appears in the feed and its
  topic tabs.
- **Add a whole new source** — add an entry to `sources` in `sources.json` with
  the right `kind` (table above), then refresh as above. YouTube needs only the
  `UC…` channel id; set `"fetch_playlists": true` to pull its playlists.
- **Add a single one-off video** — use a `youtube_videos` source with a
  `videos: [<id>]` list (see the `dzwiza` entry), then refresh.

## Customizing

- **Add / edit a curated topic (tab)** — edit `topics` in `sources.json`. Each
  topic has a `keywords` list (matched against episode title + summary) and an
  optional `playlists` list (Esoterica playlist titles whose members are
  auto-tagged into the topic — using the channel's own curation as a strong
  signal).
- **Fix a mis-sorted episode** — if an episode lands in the wrong tab (or none),
  add/adjust a topic `keyword`, or add an entry to `tags.json` keyed by the
  episode URL (copy it from `site/data.json`) with `add` / `remove` topic ids.
  Overrides win. Then re-run `build.py`. **Never edit `data/catalog.json` by
  hand** — it is regenerated by the fetcher.
- **Add / edit a featured scholar** — edit `scholars` in `sources.json`.
- **Rebrand / rename the feed** — edit the `site` block in `sources.json`
  (`title`, `feed_name`, etc.).

## Deploying

1. Push to `main`.
2. GitHub → **Settings → Pages → Source: GitHub Actions** (one-time).
3. `.github/workflows/rebuild.yml` renders and deploys on every push and via the
   manual **Run workflow** button.

## Credits & licensing

This is a fan-made index. SHWEP, Esoterica, The Modern Hermeticist, and Seekers
of Unity own all their respective content; this site only stores titles, links,
and thumbnails pulled from their public feeds, and links back to the originals.
Code is provided as-is for personal use.
