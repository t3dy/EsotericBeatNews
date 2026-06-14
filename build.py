#!/usr/bin/env python3
"""
Esoteric Beat News renderer.

Reads data/catalog.json (produced by fetch_catalog.py) and renders the static
SHWEP-styled site. This half is OFFLINE — no network — so it runs reliably in
CI even though the catalog itself is gathered by yt-dlp elsewhere.

    python build.py            # render site/ from data/catalog.json

Outputs:
    site/index.html, site/index-N.html   -- "Emanations" news feed (paginated)
    site/topics/<id>.html (+ -N.html)     -- 20 curated cross-channel topics
    site/playlists.html                   -- index of Esoterica's curated playlists
    site/playlists/<id>.html              -- one page per playlist
    site/about.html
    site/data.json                        -- machine-readable snapshot
    site/assets/                          -- CSS

A small RSS/Atom fetch helper (fetch / parse_rss / parse_youtube) is kept here
because fetch_catalog.py imports it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
SOURCES_FILE = ROOT / "sources.json"
TAGS_FILE = ROOT / "tags.json"
CATALOG = ROOT / "data" / "catalog.json"

PER_PAGE = 60
ASSET_VER = "0"  # cache-busting token, set in main() from CSS content hash
ESO_TABS: list[dict] = []   # top-N esotericist figures (id/name/color) for the toolbar — set in render()
ESO_NAMES: dict[str, str] = {}  # esotericist id -> display name, for card pills — set in render()
FEATURED_SRC_IDS: set[str] = set()  # source ids shown in the Featured Podcasts toolbar — set in render()
SCHOLAR_TABS: list[dict] = []   # featured scholars for the toolbar (site-wide) — set in render()
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
}
USER_AGENT = "EsotericBeatNews/1.0 feed aggregator"
EPOCH = dt.datetime.min.replace(tzinfo=dt.timezone.utc)


# --------------------------------------------------------------------------- #
# Feed helpers (used by fetch_catalog.py for the SHWEP RSS path)
# --------------------------------------------------------------------------- #
def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _parse_date(raw: str):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
        return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def _clean_summary(raw: str, limit: int = 320) -> str:
    txt = re.sub(r"<[^>]+>", " ", raw or "")
    txt = html.unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) > limit:
        txt = txt[:limit].rsplit(" ", 1)[0] + "…"
    return txt


def parse_rss(xml_bytes: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    if channel is None:
        return []
    chan_img = ""
    itimg = channel.find("itunes:image", NS)
    if itimg is not None:
        chan_img = itimg.get("href", "")
    out = []
    for it in channel.findall("item"):
        summary = _text(it.find("description")) or _text(it.find("itunes:summary", NS))
        thumb = ""
        iimg = it.find("itunes:image", NS)
        if iimg is not None:
            thumb = iimg.get("href", "")
        enc = it.find("enclosure")
        out.append({
            "source": source["id"], "source_name": source["name"], "kind": "podcast",
            "title": _text(it.find("title")), "url": _text(it.find("link")),
            "audio": enc.get("url") if enc is not None else "",
            "published": _parse_date(_text(it.find("pubDate"))),
            "summary": _clean_summary(summary), "thumb": thumb or chan_img,
        })
    return out


def parse_youtube(xml_bytes: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    out = []
    for entry in root.findall("atom:entry", NS):
        vid = _text(entry.find("yt:videoId", NS))
        link_el = entry.find("atom:link", NS)
        url = link_el.get("href") if link_el is not None else (
            f"https://www.youtube.com/watch?v={vid}" if vid else "")
        group = entry.find("media:group", NS)
        summary = thumb = ""
        if group is not None:
            summary = _text(group.find("media:description", NS))
            th = group.find("media:thumbnail", NS)
            if th is not None:
                thumb = th.get("url", "")
        if not thumb and vid:
            thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        out.append({
            "source": source["id"], "source_name": source["name"], "kind": "youtube",
            "title": _text(entry.find("atom:title", NS)), "url": url, "video_id": vid,
            "published": _parse_date(_text(entry.find("atom:published", NS))),
            "summary": _clean_summary(summary), "thumb": thumb,
        })
    return out


# --------------------------------------------------------------------------- #
# Tagging
# --------------------------------------------------------------------------- #
def build_membership_topics(playlists, topics):
    """video_id -> set(topic_id) implied by Esoterica's own playlist curation."""
    title_to_topics: dict[str, set] = {}
    for t in topics:
        for pl_title in t.get("playlists", []):
            title_to_topics.setdefault(pl_title.lower(), set()).add(t["id"])
    vid_topics: dict[str, set] = {}
    for pl in playlists:
        extra = title_to_topics.get(pl["title"].lower())
        if not extra:
            continue
        for vid in pl.get("video_ids", []):
            vid_topics.setdefault(vid, set()).update(extra)
    return vid_topics


def eso_tag(items, esotericists):
    """Mark each item with the esoteric figures it deals with.

    Matches figure keywords against title + summary with WORD BOUNDARIES — vital
    for short names like "Dee" or "Pico" that would otherwise match inside other
    words. Sets it["esotericists"] = sorted list of figure ids.
    """
    compiled = [
        (e["id"], [re.compile(r"\b" + re.escape(kw.lower()) + r"\b") for kw in e.get("keywords", [])])
        for e in esotericists
    ]
    for it in items:
        hay = f"{it['title']} {it.get('summary','')}".lower()
        it["esotericists"] = sorted(
            eid for eid, pats in compiled if any(p.search(hay) for p in pats)
        )


def auto_tag(items, topics, overrides, vid_topics):
    for it in items:
        hay = f"{it['title']} {it.get('summary','')}".lower()
        tags = set()
        for topic in topics:
            if topic.get("sources") and it["source"] not in topic["sources"]:
                continue
            if any(kw in hay for kw in topic["keywords"]):
                tags.add(topic["id"])
        if it.get("video_id"):
            tags.update(vid_topics.get(it["video_id"], set()))
        ov = overrides.get(it["url"])
        if ov:
            tags.update(ov.get("add", []))
            tags.difference_update(ov.get("remove", []))
        it["topics"] = sorted(tags)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def human_date(d):
    return d.strftime("%d %b %Y") if d else ""


def rel_date(d, now):
    if not d:
        return ""
    days = (now - d).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        return f"{days // 30} mo ago"
    return f"{days // 365} yr ago"


def fmt_duration(sec):
    if not sec:
        return ""
    sec = int(sec)
    h, m = sec // 3600, (sec % 3600) // 60
    return f"{h}:{m:02d}h" if h else f"{m} min"


def card(it, now, colors, depth):
    prefix = "../" * depth
    color = colors.get(it["source"], "#cf2e2e")
    thumb = it.get("thumb") or ""
    kind_label = {"youtube": "Video", "podcast": "Podcast",
                  "soundcloud": "SoundCloud"}.get(it["kind"], "")
    dur = fmt_duration(it.get("duration"))
    thumb_html = (
        f'<img class="card__thumb" src="{esc(thumb)}" alt="" loading="lazy">'
        if thumb else
        f'<div class="card__thumb card__thumb--blank" style="--src:{color}">{esc(it["source_name"][:1])}</div>'
    )
    dur_html = f'<span class="card__dur">{esc(dur)}</span>' if dur else ""
    excerpt = f'<p class="card__excerpt">{esc(it["summary"])}</p>' if it.get("summary") else ""
    pills = "".join(
        f'<a class="pill" href="{prefix}topics/{esc(t)}.html">{esc(t)}</a>'
        for t in it.get("topics", [])
    )
    pills += "".join(
        f'<a class="pill pill--eso" href="{prefix}esotericists/{esc(e)}.html">{esc(ESO_NAMES.get(e, e))}</a>'
        for e in it.get("esotericists", [])
    )
    return f"""
    <article class="card">
      <a class="card__media" href="{esc(it['url'])}" target="_blank" rel="noopener">{thumb_html}{dur_html}</a>
      <div class="card__body">
        <div class="card__meta">
          <span class="card__source" style="--src:{color}">{esc(it['source_name'])}</span>
          <span class="card__kind">{kind_label}</span>
          <span class="card__date" title="{esc(human_date(it['published']))}">{esc(rel_date(it['published'], now))}</span>
        </div>
        <h3 class="card__title"><a href="{esc(it['url'])}" target="_blank" rel="noopener">{esc(it['title'])}</a></h3>
        {excerpt}
        <div class="card__pills">{pills}</div>
      </div>
    </article>"""


def pagination(base, page, total_pages):
    if total_pages <= 1:
        return ""
    def name(p):
        return f"{base}.html" if p == 1 else f"{base}-{p}.html"
    parts = []
    if page > 1:
        parts.append(f'<a class="pg" href="{name(page-1)}">‹ prev</a>')
    # windowed page numbers
    lo, hi = max(1, page - 3), min(total_pages, page + 3)
    if lo > 1:
        parts.append(f'<a class="pg" href="{name(1)}">1</a>')
        if lo > 2:
            parts.append('<span class="pg pg--gap">…</span>')
    for p in range(lo, hi + 1):
        cls = "pg pg--cur" if p == page else "pg"
        parts.append(f'<a class="{cls}" href="{name(p)}">{p}</a>')
    if hi < total_pages:
        if hi < total_pages - 1:
            parts.append('<span class="pg pg--gap">…</span>')
        parts.append(f'<a class="pg" href="{name(total_pages)}">{total_pages}</a>')
    if page < total_pages:
        parts.append(f'<a class="pg" href="{name(page+1)}">next ›</a>')
    return f'<nav class="pagination">{"".join(parts)}</nav>'


def featured_sources(sources):
    """Featured-podcasts toolbar = every real podcast source with episodes.

    The id set is computed in render() (FEATURED_SRC_IDS): all sources that
    have at least one episode, minus the ones folded into another tab
    (tarotsoulless → the combined Ted Hand tab) or that aren't podcasts
    (dzwiza → a scholar's guest appearances, surfaced via her scholar tab).
    Order follows sources.json.
    """
    return [s for s in sources if s["id"] in FEATURED_SRC_IDS]


def featured_scholars(scholars):
    """Return the featured scholars for the toolbar."""
    featured_ids = {"newman", "principe", "forshaw", "hutton", "yates", "dzwiza",
                    "hanegraaff", "kaczynski", "martelli"}
    return [s for s in scholars if s["id"] in featured_ids]


def header_block(site, sources, topics, depth, active="", scholars=None):
    prefix = "../" * depth
    fname = site.get("feed_name", "Latest Emanations")

    def feat(label, href, key, primary=False):
        cls = "feature feature--primary" if primary else "feature"
        if active == key:
            cls += " feature--active"
        return f'<a class="{cls}" href="{prefix}{href}">{esc(label)}</a>'

    # main site-features toolbar — "Latest Emanations" set off as the marquee landing
    features = (
        feat(f"✶ {fname}", "index.html", "feed", primary=True)
        + feat("Search", "search.html", "search")
        + feat("Browse", "browse.html", "browse")
        + feat("Scholars", "scholars.html", "scholars")
        + feat("Figures", "esotericists.html", "esotericists")
        + feat("Audiobooks", "topics/audiobooks.html", "audiobooks")
        + feat("Playlists", "playlists.html", "playlists")
        + feat("About", "about.html", "about")
    )
    # featured-podcasts toolbar — a tab per show, each to its own landing page
    def podtab(s):
        cls = "podtab podtab--active" if active == "src:" + s["id"] else "podtab"
        color = s.get("color", "#cf2e2e")
        # Esoteric Beat + Tarot for the Soulless Materialist share the combined Ted Hand page
        if s["id"] == "esotericbeat":
            label, href = "Ted Hand", "ted-hand.html"
        else:
            label, href = s.get("tab", s["name"]), f"sources/{s['id']}.html"
        return (f'<a class="{cls}" style="--src:{color}" '
                f'href="{prefix}{href}">{esc(label)}</a>')

    tabs = "".join(podtab(s) for s in featured_sources(sources))

    # featured-scholars toolbar — a tab per scholar, site-wide (reads SCHOLAR_TABS global)
    def schol_tab(s):
        cls = "podtab podtab--active" if active == "sch:" + s["id"] else "podtab"
        color = s.get("color", "#8b7355")
        label = esc(s.get("tab", s["name"]))
        return (f'<a class="{cls}" style="--src:{color}" '
                f'href="{prefix}scholars/{s["id"]}.html">{label}</a>')

    schol_tabs = "".join(schol_tab(s) for s in SCHOLAR_TABS)
    schol_bar = (
        f'<div class="podbar podbar--scholars"><div class="podbar__inner">'
        f'<span class="podbar__label"><span>Featured</span><span>Scholars</span></span>'
        f'{schol_tabs}</div></div>'
        if SCHOLAR_TABS else ""
    )

    # topics toolbar — the thematic currents, their own bar
    chips = "".join(
        f'<a class="chip{" chip--active" if active==t["id"] else ""}" '
        f'href="{prefix}topics/{t["id"]}.html">{esc(t.get("nav", t["title"]))}</a>'
        for t in topics
    )
    # esotericists toolbar — the top figures by episode count (set in render())
    eso_chips = "".join(
        f'<a class="chip chip--eso{" chip--active" if active=="eso:"+e["id"] else ""}" '
        f'style="--src:{e.get("color", "#8b7355")}" '
        f'href="{prefix}esotericists/{e["id"]}.html">{esc(e["name"])}</a>'
        for e in ESO_TABS
    )
    eso_bar = (
        f'<div class="subnav subnav--figures"><div class="subnav__inner">'
        f'<span class="subnav__label">Esotericists</span>{eso_chips}</div></div>'
        if ESO_TABS else ""
    )
    return f"""
<header class="site-header">
  <div class="donate-bar">
    <p class="donate-bar__text">Support this research: <a href="https://venmo.com/u/T3dyhand" class="donate-btn donate-btn--venmo" target="_blank" rel="noopener">Venmo</a> <a href="https://paypal.me/tedhand" class="donate-btn donate-btn--paypal" target="_blank" rel="noopener">PayPal</a></p>
  </div>
  <div class="header__container">
    <a class="header__logo" href="{prefix}index.html">✶ {esc(site['title'])}</a>
    <nav class="feature-bar" aria-label="Site features">{features}</nav>
  </div>
  <div class="podbar"><div class="podbar__inner"><span class="podbar__label"><span>Featured</span><span>Podcasts</span></span>{tabs}</div></div>
  {schol_bar}
  <div class="subnav"><div class="subnav__inner"><span class="subnav__label">Topics</span>{chips}</div></div>
  {eso_bar}
</header>"""


def shell(title, body, site, sources, topics, depth, active="", scholars=None):
    prefix = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(site['tagline'])}">
<link rel="stylesheet" href="{prefix}assets/style.css?v={ASSET_VER}">
<link rel="stylesheet" href="{prefix}assets/aggregator.css?v={ASSET_VER}">
</head>
<body>
{header_block(site, sources, topics, depth, active, scholars)}
<main class="container">
{body}
</main>
<footer class="site-footer">
  <div class="container">
    <p>{esc(site['title'])} aggregates public RSS/Atom feeds. Every card links to the
    creator's own page — all content belongs to its makers. Sources:
    <a href="https://shwep.net" target="_blank" rel="noopener">SHWEP</a>,
    <a href="https://www.youtube.com/channel/UCoydhtfFSk1fZXNRnkGnneQ" target="_blank" rel="noopener">Esoterica</a>,
    <a href="https://www.youtube.com/channel/UCcluftdk1tuDU71ZdGNpHTA" target="_blank" rel="noopener">The Modern Hermeticist</a>,
    <a href="https://www.youtube.com/channel/UCL9A83sJIYNAovCA92uaTRQ" target="_blank" rel="noopener">Seekers of Unity</a>.
    <a href="{esc(site.get('repo',''))}" target="_blank" rel="noopener">Source on GitHub</a>.</p>
  </div>
</footer>
</body>
</html>
"""


def write_paginated(items, base, hero_html, page_title, site, sources, topics, now, colors, depth, active, sort_controls=False):
    total_pages = max(1, ceil(len(items) / PER_PAGE))
    sort_html = ""
    if sort_controls:
        sort_html = """
  <div class="sort-controls">
    <label for="sort-select">Sort by:</label>
    <select id="sort-select" class="sort-select">
      <option value="date-desc">Newest first</option>
      <option value="date-asc">Oldest first</option>
      <option value="source">Source</option>
      <option value="title">Title</option>
    </select>
  </div>
  <script>
  const sortSelect = document.getElementById('sort-select');
  const cardList = document.querySelector('.card-list');
  if (sortSelect && cardList) {
    sortSelect.addEventListener('change', (e) => {
      const cards = Array.from(cardList.querySelectorAll('.card'));
      cards.sort((a, b) => {
        const aTitle = a.querySelector('.card__title').textContent;
        const aSource = a.querySelector('.card__source').textContent;
        const aDate = a.querySelector('.card__date').getAttribute('title') || '';
        const bTitle = b.querySelector('.card__title').textContent;
        const bSource = b.querySelector('.card__source').textContent;
        const bDate = b.querySelector('.card__date').getAttribute('title') || '';

        switch(e.target.value) {
          case 'date-asc': return aDate.localeCompare(bDate);
          case 'date-desc': return bDate.localeCompare(aDate);
          case 'source': return aSource.localeCompare(bSource) || aTitle.localeCompare(bTitle);
          case 'title': return aTitle.localeCompare(bTitle);
          default: return 0;
        }
      });
      cards.forEach(c => cardList.appendChild(c));
    });
  }
  </script>"""

    for page in range(1, total_pages + 1):
        chunk = items[(page - 1) * PER_PAGE: page * PER_PAGE]
        cards = "".join(card(i, now, colors, depth) for i in chunk) or \
            '<p class="empty">Nothing here yet.</p>'
        hero = hero_html if page == 1 else \
            f'<section class="hero hero--slim"><h1>{esc(page_title)}</h1>' \
            f'<p class="count">page {page} of {total_pages}</p></section>'
        body = f"{hero}{sort_html if page == 1 else ''}\n<section class=\"timeline-section\"><div class=\"card-list\">{cards}</div>" \
               f"{pagination(base.split('/')[-1], page, total_pages)}</section>"
        fname = f"{base}.html" if page == 1 else f"{base}-{page}.html"
        (SITE / fname).write_text(
            shell(page_title, body, site, sources, topics, depth, active), encoding="utf-8")
    return total_pages


def render(catalog, cfg, now):
    site, sources, topics = cfg["site"], cfg["sources"], cfg["topics"]
    colors = {s["id"]: s.get("color", "#cf2e2e") for s in sources}
    src_by_id = {s["id"]: s for s in sources}
    items = catalog["items"]
    for it in items:
        it["published"] = _parse_date(it.get("published_iso", ""))
    items.sort(key=lambda x: x["published"] or EPOCH, reverse=True)
    by_vid = {i["video_id"]: i for i in items if i.get("video_id")}

    # ---- Featured Podcasts toolbar: every source with episodes (order = sources.json) ----
    src_counts = {s["id"]: 0 for s in sources}
    for it in items:
        if it["source"] in src_counts:
            src_counts[it["source"]] += 1
    # Sources kept OUT of the Featured Podcasts toolbar (their episodes still live
    # in the feed, topics, search, and scholar pages — only the tab is dropped):
    #   tarotsoulless        -> folded into the combined Ted Hand tab
    #   dzwiza               -> a scholar's appearances, shown via her scholar tab
    #   kazrowe/bytesize...  -> general-interest channels, not esoteric-themed
    #   michaelkuhlman, greshamhutton, joekiernan, cafeneaua_newman,
    #   spiritus_mundi_newman -> trimmed for toolbar space (verbose niche tabs)
    not_a_podcast = {"tarotsoulless", "dzwiza", "kazrowe", "bytesizescience",
                     "michaelkuhlman", "greshamhutton", "joekiernan",
                     "cafeneaua_newman", "spiritus_mundi_newman"}
    global FEATURED_SRC_IDS, SCHOLAR_TABS
    FEATURED_SRC_IDS = {s["id"] for s in sources
                        if src_counts.get(s["id"], 0) > 0 and s["id"] not in not_a_podcast}
    SCHOLAR_TABS = featured_scholars(cfg.get("scholars", []))

    # ---- Esotericists: count episodes per figure, pick the top 10 for the toolbar ----
    esotericists = cfg.get("esotericists", [])
    eso_by_id = {e["id"]: e for e in esotericists}
    eso_counts = {e["id"]: 0 for e in esotericists}
    for it in items:
        for eid in it.get("esotericists", []):
            if eid in eso_counts:
                eso_counts[eid] += 1
    eso_ranked = sorted((e for e in esotericists if eso_counts[e["id"]] > 0),
                        key=lambda e: (-eso_counts[e["id"]], e["name"]))
    global ESO_TABS, ESO_NAMES
    ESO_TABS = [{"id": e["id"], "name": e["name"], "color": e.get("color", "#8b7355")}
                for e in eso_ranked[:10]]
    ESO_NAMES = {e["id"]: e["name"] for e in esotericists}

    (SITE / "topics").mkdir(parents=True, exist_ok=True)
    (SITE / "scholars").mkdir(parents=True, exist_ok=True)
    (SITE / "esotericists").mkdir(parents=True, exist_ok=True)
    (SITE / "playlists").mkdir(parents=True, exist_ok=True)

    # ---- News feed (index) ----
    counts = {s["id"]: sum(1 for i in items if i["source"] == s["id"]) for s in sources}
    stat = " · ".join(f'{esc(src_by_id[sid]["name"])} {n}' for sid, n in counts.items())
    feed_hero = f"""
  <section class="hero">
    <h1>{esc(site['feed_name'])}</h1>
    <p class="hero__tagline">{esc(site['feed_blurb'])}</p>
    <p class="count">{len(items)} episodes &nbsp;·&nbsp; {stat}</p>
  </section>"""
    feed_pages = write_paginated(items, "index", feed_hero, site["feed_name"],
                                 site, sources, topics, now, colors, depth=0, active="feed")

    # ---- Featured-podcast landing pages (one per source) ----
    (SITE / "sources").mkdir(parents=True, exist_ok=True)
    kind_word = {"podcast": "podcast", "youtube": "YouTube channel",
                 "youtube_playlist": "YouTube series", "composite": "podcast"}
    for s in featured_sources(sources):
        s_items = [i for i in items if i["source"] == s["id"]]
        where = kind_word.get(s["kind"], "series")
        hero = f"""
  <section class="hero hero--source" style="--src:{s.get('color','#cf2e2e')}">
    <p class="crumb"><a href="../index.html">{esc(site['feed_name'])}</a> / Featured Podcasts</p>
    <h1>{esc(s.get('long_name', s['name']))}</h1>
    <p class="hero__tagline">Every episode of {esc(s['name'])} we track — this {esc(where)} in one place.
      <a href="{esc(s.get('link','#'))}" target="_blank" rel="noopener">Visit the source ›</a></p>
    <p class="count">{len(s_items)} episode{'s' if len(s_items)!=1 else ''}</p>
  </section>"""
        write_paginated(s_items, f"sources/{s['id']}", hero, s["name"],
                        site, sources, topics, now, colors, depth=1, active="src:" + s["id"])

    # ---- Curated topic pages ----
    for t in topics:
        t_items = [i for i in items if t["id"] in i.get("topics", [])]
        hero = f"""
  <section class="hero hero--topic">
    <p class="crumb"><a href="../index.html">{esc(site['feed_name'])}</a> / Curated</p>
    <h1>{esc(t['title'])}</h1>
    <p class="hero__tagline">{esc(t.get('blurb',''))}</p>
    <p class="count">{len(t_items)} episode{'s' if len(t_items)!=1 else ''}</p>
  </section>"""
        write_paginated(t_items, f"topics/{t['id']}", hero, t["title"],
                        site, sources, topics, now, colors, depth=1, active=t["id"], sort_controls=True)

    # ---- Scholar pages ----
    scholars = cfg.get("scholars", [])
    for sch in scholars:
        sch_items = []
        keywords = sch.get("keywords", [])
        for item in items:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            if any(kw in text for kw in keywords):
                sch_items.append(item)
        hero = f"""
  <section class="hero hero--topic">
    <p class="crumb"><a href="../index.html">{esc(site['feed_name'])}</a> / Scholars</p>
    <h1>{esc(sch['name'])}</h1>
    <p class="hero__tagline">{esc(sch.get('blurb',''))}</p>
    <p class="count">{len(sch_items)} episode{'s' if len(sch_items)!=1 else ''}</p>
  </section>"""
        write_paginated(sch_items, f"scholars/{sch['id']}", hero, sch["name"],
                        site, sources, topics, now, colors, depth=1, active=f"sch:{sch['id']}", sort_controls=True)

    # ---- Esotericist figure pages (one per figure that appears in the catalog) ----
    eso_lists = {e["id"]: [i for i in items if e["id"] in i.get("esotericists", [])]
                 for e in esotericists}
    for e in eso_ranked:
        e_items = eso_lists[e["id"]]
        rank = next((n for n, t in enumerate(ESO_TABS, 1) if t["id"] == e["id"]), None)
        rank_note = f" &nbsp;·&nbsp; #{rank} most-discussed figure" if rank else ""
        hero = f"""
  <section class="hero hero--topic" style="--src:{e.get('color', '#8b7355')}">
    <p class="crumb"><a href="../index.html">{esc(site['feed_name'])}</a> /
      <a href="../esotericists.html">Esotericists</a></p>
    <h1>{esc(e['name'])}</h1>
    <p class="hero__tagline">{esc(e.get('blurb', ''))}</p>
    <p class="count">{len(e_items)} episode{'s' if len(e_items)!=1 else ''}{rank_note}</p>
  </section>"""
        write_paginated(e_items, f"esotericists/{e['id']}", hero, e["name"],
                        site, sources, topics, now, colors, depth=1,
                        active=f"eso:{e['id']}", sort_controls=True)

    # ---- esotericists.html (all figures, ranked, with episode counts) ----
    eso_cards = "".join(
        f"""
      <a class="figure-card" href="esotericists/{esc(e['id'])}.html" style="--src:{e.get('color', '#8b7355')}">
        <span class="figure-card__count">{eso_counts[e['id']]}</span>
        <span class="figure-card__name">{esc(e['name'])}</span>
        <span class="figure-card__blurb">{esc(e.get('blurb', ''))}</span>
      </a>""" for e in eso_ranked)
    eso_index_body = f"""
  <section class="hero hero--slim">
    <h1>Esotericists</h1>
    <p class="hero__tagline">The figures of Western esotericism — magi, mystics, alchemists, and
      Hermetic philosophers — ranked by how many episodes across the catalogue discuss them.
      The top ten ride in the toolbar above; every figure below has their own page.</p>
  </section>
  <section class="figure-grid">{eso_cards}</section>"""
    (SITE / "esotericists.html").write_text(
        shell(f"Esotericists — {site['title']}", eso_index_body, site, sources, topics, 0, "esotericists", scholars),
        encoding="utf-8")

    # ---- Playlist pages + index (Esoterica's own curation) ----
    playlists = sorted(catalog.get("playlists", []), key=lambda p: -len(p.get("video_ids", [])))
    pl_cards = []
    for pl in playlists:
        slug = pl["id"]
        src = src_by_id.get(pl["source"], {})
        rows = []
        for v in pl.get("videos", []):
            it = by_vid.get(v["id"])
            if it is None:  # video not in uploads list (e.g. cross-posted) — build a stub
                it = {
                    "source": pl["source"], "source_name": src.get("name", ""), "kind": "youtube",
                    "title": v.get("title", ""), "url": v.get("url", ""),
                    "published": None, "summary": "",
                    "thumb": f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg", "topics": [],
                }
            rows.append(card(it, now, colors, depth=1))
        body = f"""
  <section class="hero hero--topic">
    <p class="crumb"><a href="../playlists.html">Playlists</a> / {esc(src.get('name',''))}</p>
    <h1>{esc(pl['title'])}</h1>
    <p class="hero__tagline">A curated playlist by {esc(src.get('name',''))}.
      <a href="{esc(pl['url'])}" target="_blank" rel="noopener">Open on YouTube ›</a></p>
    <p class="count">{len(pl.get('video_ids', []))} videos</p>
  </section>
  <section class="timeline-section"><div class="card-list">{''.join(rows)}</div></section>"""
        (SITE / "playlists" / f"{slug}.html").write_text(
            shell(f"{pl['title']} — {site['title']}", body, site, sources, topics, depth=1, active="playlists"),
            encoding="utf-8")
        pl_cards.append(f"""
      <a class="pl-card" href="playlists/{esc(slug)}.html">
        <span class="pl-card__count">{len(pl.get('video_ids', []))}</span>
        <span class="pl-card__title">{esc(pl['title'])}</span>
        <span class="pl-card__src" style="--src:{colors.get(pl['source'],'#cf2e2e')}">{esc(src.get('name',''))}</span>
      </a>""")

    pl_index_body = f"""
  <section class="hero">
    <h1>Curated Playlists</h1>
    <p class="hero__tagline">Esoterica's own thematic playlists — {len(playlists)} curated series,
      from the Ancient Near East to Renaissance occult philosophy.</p>
  </section>
  <section class="pl-grid">{''.join(pl_cards)}</section>"""
    (SITE / "playlists.html").write_text(
        shell(f"Curated Playlists — {site['title']}", pl_index_body, site, sources, topics, 0, "playlists"),
        encoding="utf-8")

    # ---- ted-hand.html (combined Esoteric Beat + Tarot for Soulless Materialist) ----
    ted_hand_items = [i for i in items if i["source"] in ("esotericbeat", "tarotsoulless")]
    ted_hand_body = """
  <section class="hero hero--slim">
    <h1>Ted Hand</h1>
    <p class="hero__tagline">Esoteric studies and tarot from Ted Hand's projects.</p>
  </section>
  <section class="source-sections">"""
    for src_id in ("esotericbeat", "tarotsoulless"):
        src = src_by_id.get(src_id, {})
        src_items = [i for i in ted_hand_items if i["source"] == src_id]
        cards = "".join(card(i, now, colors, 0) for i in src_items) or '<p class="empty">Nothing here.</p>'
        ted_hand_body += f"""
    <div class="source-section">
      <h2>{esc(src.get('name', ''))}</h2>
      <div class="card-list">{cards}</div>
    </div>"""
    ted_hand_body += """
  </section>"""
    (SITE / "ted-hand.html").write_text(
        shell(f"Ted Hand — {site['title']}", ted_hand_body, site, sources, topics, 0, "src:esotericbeat", scholars),
        encoding="utf-8")

    # ---- scholars.html (featured scholars aggregated) ----
    sch_body = """
  <section class="hero hero--slim">
    <h1>Featured Scholars</h1>
    <p class="hero__tagline">Luminaries of Western esotericism and Renaissance philosophy.</p>
  </section>
  <section class="source-sections">"""
    for sch in scholars:
        sch_items = []
        keywords = sch.get("keywords", [])
        for item in items:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            if any(kw in text for kw in keywords):
                sch_items.append(item)
        cards = "".join(card(i, now, colors, 0) for i in sch_items) or '<p class="empty">Nothing here.</p>'
        sch_body += f"""
    <div class="source-section">
      <h2>{esc(sch['name'])} <span class="section-count">({len(sch_items)} episodes)</span></h2>
      <div class="card-list">{cards}</div>
    </div>"""
    sch_body += """
  </section>"""
    (SITE / "scholars.html").write_text(
        shell(f"Featured Scholars — {site['title']}", sch_body, site, sources, topics, 0, "scholars", scholars),
        encoding="utf-8")

    # ---- Individual scholar pages (scholars/[id].html) ----
    (SITE / "scholars").mkdir(exist_ok=True)
    for sch in scholars:
        sch_items = []
        keywords = sch.get("keywords", [])
        for item in items:
            text = (item.get("title", "") + " " + item.get("summary", "")).lower()
            if any(kw in text for kw in keywords):
                sch_items.append(item)
        sch_item_cards = "".join(card(i, now, colors, 1) for i in sch_items) or '<p class="empty">Nothing here.</p>'
        sch_page_body = f"""
  <section class="hero hero--slim">
    <h1>{esc(sch['name'])}</h1>
    <p class="hero__tagline">{len(sch_items)} episodes</p>
  </section>
  <section class="card-list">{sch_item_cards}</section>"""
        (SITE / "scholars" / f"{sch['id']}.html").write_text(
            shell(f"{sch['name']} — {site['title']}", sch_page_body, site, sources, topics, 1, f"sch:{sch['id']}", scholars),
            encoding="utf-8")

    # ---- About ----
    src_rows = "".join(
        f'<li><a href="{esc(s["link"])}" target="_blank" rel="noopener">{esc(s.get("long_name", s["name"]))}</a>'
        f' — {counts.get(s["id"],0)} episodes</li>' for s in sources)
    about_body = f"""
  <section class="hero"><h1>About {esc(site['title'])}</h1>
    <p class="hero__tagline">{esc(site['tagline'])}</p></section>
  <section class="prose content-narrow">
    <p>{esc(site['title'])} gathers the complete back catalogues of a handful of
    esoteric-studies podcasts and YouTube channels into one place — a single
    <a href="index.html">news feed</a> of every episode in order, curated
    cross-channel <em>currents</em> (Neoplatonism, Grimoires, Kabbalah, and more),
    and a section for each of Esoterica's own <a href="playlists.html">curated playlists</a>.</p>
    <h2>Sources</h2>
    <ul>{src_rows}</ul>
    <h2>How it works</h2>
    <p>Episode data is gathered from public RSS/Atom feeds and (for full YouTube
    back catalogues) <code>yt-dlp</code> — no API keys. The site is static HTML,
    rebuilt by a Python pipeline and deployed via GitHub Pages. Every card links
    out to the creator's own page; nothing is rehosted. All content belongs to
    its makers — please subscribe to and support them directly.</p>
  </section>"""
    (SITE / "about.html").write_text(
        shell(f"About — {site['title']}", about_body, site, sources, topics, 0, "about"), encoding="utf-8")

    # ---- search.html ----
    search_body = """
  <div class="hero hero--slim">
    <h1>Search</h1>
    <p class="hero__tagline">Filter by keyword, source, or topic across all episodes.</p>
  </div>

  <form class="search-form" id="search-form">
    <div class="search-controls">
      <input type="text" id="query" class="search-input" placeholder="Search titles & summaries..." autocomplete="off">
      <select id="source" class="search-filter">
        <option value="">All Sources</option>""" + "".join(
            f'<option value="{esc(s["id"])}">{esc(s["name"])}</option>'
            for s in sources) + """
      </select>
      <select id="topic" class="search-filter">
        <option value="">All Topics</option>""" + "".join(
            f'<option value="{esc(t["id"])}">{esc(t["title"])}</option>'
            for t in topics) + """
      </select>
      <button type="button" class="search-clear" id="clear-btn">Clear</button>
    </div>
  </form>

  <div class="search-results">
    <p id="result-count" class="search-count"></p>
    <div id="results" class="card-list"></div>
  </div>

  <script>
  (async () => {
    const data = await fetch('data.json').then(r => r.json());
    const form = document.getElementById('search-form');
    const query = document.getElementById('query');
    const source = document.getElementById('source');
    const topic = document.getElementById('topic');
    const clearBtn = document.getElementById('clear-btn');
    const resultsDiv = document.getElementById('results');
    const countDiv = document.getElementById('result-count');

    function makeCard(item) {
      const color = source.value ? '#cf2e2e' : '#cf2e2e';
      const thumb = item.thumb
        ? `<img class="card__thumb" src="${item.thumb}" alt="" loading="lazy">`
        : `<div class="card__thumb card__thumb--blank" style="--src:${color}">${item.source_name[0]}</div>`;
      const kind = {'youtube': 'Video', 'podcast': 'Podcast', 'soundcloud': 'SoundCloud'}[item.kind] || '';
      const topics = (item.topics || []).map(t => `<a class="pill" href="topics/${t}.html">${t}</a>`).join('');
      return `
        <article class="card">
          <a class="card__media" href="${item.url}" target="_blank" rel="noopener">${thumb}</a>
          <div class="card__body">
            <div class="card__meta">
              <span class="card__source">${item.source_name}</span>
              <span class="card__kind">${kind}</span>
            </div>
            <h3 class="card__title"><a href="${item.url}" target="_blank" rel="noopener">${item.title}</a></h3>
            ${item.summary ? `<p class="card__excerpt">${item.summary}</p>` : ''}
            <div class="card__pills">${topics}</div>
          </div>
        </article>`;
    }

    function search() {
      const q = query.value.toLowerCase();
      const s = source.value;
      const t = topic.value;

      let results = data.items.filter(item => {
        if (q && !item.title.toLowerCase().includes(q) && !item.summary.toLowerCase().includes(q)) return false;
        if (s && item.source !== s) return false;
        if (t && !(item.topics || []).includes(t)) return false;
        return true;
      });

      countDiv.textContent = `${results.length} result${results.length===1?'':'s'}`;
      resultsDiv.innerHTML = results.length ? results.map(makeCard).join('') : '<p class="empty">No results found.</p>';
    }

    form.addEventListener('change', search);
    query.addEventListener('input', () => setTimeout(search, 100));
    clearBtn.addEventListener('click', () => {
      query.value = '';
      source.value = '';
      topic.value = '';
      search();
    });
  })();
  </script>"""
    (SITE / "search.html").write_text(
        shell(f"Search — {site['title']}", search_body, site, sources, topics, 0, "search"), encoding="utf-8")

    # ---- browse.html (chronological timeline) ----
    browse_body = """
  <div class="hero hero--slim">
    <h1>Browse by Date</h1>
    <p class="hero__tagline">Explore all episodes in chronological order.</p>
  </div>

  <div class="browse-controls">
    <label for="browse-source">Filter by source:</label>
    <select id="browse-source" class="browse-filter">
      <option value="">All Sources</option>""" + "".join(
            f'<option value="{esc(s["id"])}">{esc(s["name"])}</option>'
            for s in sources) + """
    </select>
    <label for="browse-topic">Filter by topic:</label>
    <select id="browse-topic" class="browse-filter">
      <option value="">All Topics</option>""" + "".join(
            f'<option value="{esc(t["id"])}">{esc(t["title"])}</option>'
            for t in topics) + """
    </select>
  </div>

  <div class="browse-results">
    <p id="browse-count" class="browse-count"></p>
    <div id="browse-items" class="card-list"></div>
  </div>

  <script>
  (async () => {
    const data = await fetch('data.json').then(r => r.json());
    const sourceFilter = document.getElementById('browse-source');
    const topicFilter = document.getElementById('browse-topic');
    const countDiv = document.getElementById('browse-count');
    const itemsDiv = document.getElementById('browse-items');

    function makeCard(item) {
      const color = '#cf2e2e';
      const thumb = item.thumb
        ? `<img class="card__thumb" src="${item.thumb}" alt="" loading="lazy">`
        : `<div class="card__thumb card__thumb--blank" style="--src:${color}">${item.source_name[0]}</div>`;
      const kind = {'youtube': 'Video', 'podcast': 'Podcast', 'soundcloud': 'SoundCloud'}[item.kind] || '';
      const topics = (item.topics || []).map(t => `<a class="pill" href="topics/${t}.html">${t}</a>`).join('');
      return `
        <article class="card">
          <a class="card__media" href="${item.url}" target="_blank" rel="noopener">${thumb}</a>
          <div class="card__body">
            <div class="card__meta">
              <span class="card__source">${item.source_name}</span>
              <span class="card__kind">${kind}</span>
              <span class="card__date">${item.published_iso ? new Date(item.published_iso).toLocaleDateString() : ''}</span>
            </div>
            <h3 class="card__title"><a href="${item.url}" target="_blank" rel="noopener">${item.title}</a></h3>
            ${item.summary ? `<p class="card__excerpt">${item.summary}</p>` : ''}
            <div class="card__pills">${topics}</div>
          </div>
        </article>`;
    }

    function browse() {
      const s = sourceFilter.value;
      const t = topicFilter.value;

      let results = data.items.filter(item => {
        if (s && item.source !== s) return false;
        if (t && !(item.topics || []).includes(t)) return false;
        return true;
      });

      countDiv.textContent = `${results.length} episode${results.length===1?'':'s'}`;
      itemsDiv.innerHTML = results.length ? results.map(makeCard).join('') : '<p class="empty">No episodes found.</p>';
    }

    sourceFilter.addEventListener('change', browse);
    topicFilter.addEventListener('change', browse);
    browse();
  })();
  </script>"""
    (SITE / "browse.html").write_text(
        shell(f"Browse by Date — {site['title']}", browse_body, site, sources, topics, 0, "browse"), encoding="utf-8")

    # ---- data.json ----
    (SITE / "data.json").write_text(json.dumps({
        "generated": now.isoformat(), "count": len(items),
        "items": [{k: v for k, v in i.items() if k != "published"} for i in items],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    return len(items), len(topics), len(playlists), feed_pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default=str(CATALOG))
    args = ap.parse_args()

    cat_path = Path(args.catalog)
    if not cat_path.exists():
        sys.exit(f"{cat_path} not found. Run: python fetch_catalog.py")
    catalog = json.loads(cat_path.read_text(encoding="utf-8"))
    cfg = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    overrides = {}
    if TAGS_FILE.exists():
        overrides = json.loads(TAGS_FILE.read_text(encoding="utf-8")).get("overrides", {})

    SITE.mkdir(exist_ok=True)
    dst = SITE / "assets"
    dst.mkdir(exist_ok=True)
    import hashlib
    hasher = hashlib.sha1()
    for css in (ROOT / "assets").glob("*.css"):
        data = css.read_bytes()
        hasher.update(data)
        shutil.copy2(css, dst / css.name)
    global ASSET_VER
    ASSET_VER = hasher.hexdigest()[:8]

    vid_topics = build_membership_topics(catalog.get("playlists", []), cfg["topics"])
    auto_tag(catalog["items"], cfg["topics"], overrides, vid_topics)
    eso_tag(catalog["items"], cfg.get("esotericists", []))
    now = dt.datetime.now(dt.timezone.utc)
    n, nt, npl, fp = render(catalog, cfg, now)
    print(f"Rendered {n} items · {nt} topic pages · {npl} playlist pages · "
          f"{fp}-page feed -> {SITE}\\index.html")


if __name__ == "__main__":
    main()
