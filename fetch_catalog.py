#!/usr/bin/env python3
"""
ESOFEED catalog fetcher.

Pulls the COMPLETE back catalog for every source into data/catalog.json:

  * YouTube channels  -> full upload list via yt-dlp (no API key)
  * Esoterica         -> every curated playlist + its members
  * SHWEP podcast     -> RSS feed (stdlib)

YouTube's RSS feed only returns the latest ~15 videos, which is why we use
yt-dlp here. yt-dlp scrapes the channel pages directly, so it needs a network
that can reach youtube.com (some networks / datacenter IPs are blocked).

This is the SLOW, network-bound half of the pipeline. Run it locally where
YouTube is reachable; it writes a committed data/catalog.json that build.py
renders offline. Re-run it to refresh the catalog, then commit + push.

    python fetch_catalog.py            # fetch everything, write data/catalog.json
    python fetch_catalog.py --cache    # reuse data/raw/*.json, only re-assemble

Raw per-source dumps are cached under data/raw/ so a failure partway through
doesn't lose completed work.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import build  # reuse parse_rss / _clean_summary / fetch

try:
    import yt_dlp
except ImportError:
    sys.exit("yt-dlp is required:  python -m pip install --upgrade yt-dlp")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CATALOG = DATA / "catalog.json"

YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "skip_download": True,
    "extractor_args": {"youtubetab": {"approximate_date": ["1"]}},
}


def ydl_json(url: str) -> dict:
    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        return ydl.sanitize_info(ydl.extract_info(url, download=False))


def iso(ts) -> str:
    if not ts:
        return ""
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()


def entry_to_item(e: dict, source: dict) -> dict:
    vid = e.get("id", "")
    return {
        "source": source["id"],
        "source_name": source["name"],
        "kind": "youtube",
        "title": (e.get("title") or "").strip(),
        "url": e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else ""),
        "video_id": vid,
        "published_iso": iso(e.get("timestamp")),
        "summary": "",  # flat extraction has no description; titles drive tagging
        "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else "",
        "duration": int(e["duration"]) if e.get("duration") else None,
    }


def fetch_youtube_channel(source: dict, use_cache: bool) -> list[dict]:
    cache = RAW / f"yt_{source['id']}.json"
    if use_cache and cache.exists():
        raw = json.loads(cache.read_text(encoding="utf-8"))
    else:
        url = f"https://www.youtube.com/channel/{source['channel_id']}/videos"
        print(f"  [yt-dlp] {source['name']} uploads ...", flush=True)
        raw = ydl_json(url)
        cache.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    entries = [e for e in raw.get("entries", []) if e.get("id")]
    items = [entry_to_item(e, source) for e in entries]
    items = [i for i in items if i["title"] and i["url"]]
    print(f"           -> {len(items)} videos")
    return items


def fetch_playlists(source: dict, use_cache: bool) -> list[dict]:
    """Return [{id,title,url,source,video_ids:[...]}] for a channel's playlists."""
    idx_cache = RAW / f"pl_index_{source['id']}.json"
    if use_cache and idx_cache.exists():
        idx = json.loads(idx_cache.read_text(encoding="utf-8"))
    else:
        url = f"https://www.youtube.com/channel/{source['channel_id']}/playlists"
        print(f"  [yt-dlp] {source['name']} playlist index ...", flush=True)
        idx = ydl_json(url)
        idx_cache.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")

    playlists = []
    for ple in idx.get("entries", []):
        pid = ple.get("id")
        if not pid:
            continue
        pcache = RAW / f"pl_{pid}.json"
        if use_cache and pcache.exists():
            praw = json.loads(pcache.read_text(encoding="utf-8"))
        else:
            print(f"  [yt-dlp] playlist: {ple.get('title')} ...", flush=True)
            praw = ydl_json(f"https://www.youtube.com/playlist?list={pid}")
            pcache.write_text(json.dumps(praw, ensure_ascii=False), encoding="utf-8")
        vids = []
        for e in praw.get("entries", []):
            if not e.get("id"):
                continue
            vids.append({
                "id": e["id"],
                "title": (e.get("title") or "").strip(),
                "url": e.get("url") or f"https://www.youtube.com/watch?v={e['id']}",
            })
        playlists.append({
            "id": pid,
            "title": (praw.get("title") or ple.get("title") or "").strip(),
            "url": f"https://www.youtube.com/playlist?list={pid}",
            "source": source["id"],
            "videos": vids,
            "video_ids": [v["id"] for v in vids],
        })
        print(f"           -> {len(vids)} videos")
    return playlists


def fetch_shwep(source: dict, use_cache: bool) -> list[dict]:
    cache = RAW / f"rss_{source['id']}.xml"
    if use_cache and cache.exists():
        data = cache.read_bytes()
    else:
        print(f"  [rss]   {source['name']} ...", flush=True)
        data = build.fetch(source["feed"])
        cache.write_bytes(data)
    items = build.parse_rss(data, source)
    out = []
    for it in items:
        out.append({
            "source": it["source"], "source_name": it["source_name"], "kind": "podcast",
            "title": it["title"], "url": it["url"], "video_id": "",
            "published_iso": it["published"].isoformat() if it["published"] else "",
            "summary": it.get("summary", ""), "thumb": it.get("thumb", ""),
            "audio": it.get("audio", ""), "duration": None,
        })
    print(f"           -> {len(out)} episodes")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", action="store_true",
                    help="reuse data/raw/* dumps instead of re-fetching")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))

    all_items: list[dict] = []
    all_playlists: list[dict] = []
    print("Fetching full catalog (this is the slow, network half)\n")
    for src in cfg["sources"]:
        if src["kind"] == "youtube":
            all_items += fetch_youtube_channel(src, args.cache)
            if src.get("fetch_playlists"):
                all_playlists += fetch_playlists(src, args.cache)
        else:
            all_items += fetch_shwep(src, args.cache)

    # de-dup by url, keep the richest (longest summary) copy
    by_url: dict[str, dict] = {}
    for it in all_items:
        prev = by_url.get(it["url"])
        if not prev or len(it.get("summary", "")) > len(prev.get("summary", "")):
            by_url[it["url"]] = it
    items = sorted(by_url.values(), key=lambda x: x["published_iso"], reverse=True)

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    CATALOG.write_text(json.dumps({
        "generated": now,
        "count": len(items),
        "playlist_count": len(all_playlists),
        "items": items,
        "playlists": all_playlists,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {CATALOG}  ({len(items)} items, {len(all_playlists)} playlists)")


if __name__ == "__main__":
    main()
