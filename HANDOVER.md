# Esoteric Beat News — Handover & Strategy Document

## Project Summary

**Esoteric Beat News** is a static-generated news aggregator for esoteric studies media. It pulls from 23+ podcast and YouTube sources (2,813 episodes), auto-tags by 20 topics, and serves as a discovery platform for scholarly content in Western esotericism.

**Live:** https://t3dy.github.io/EsotericBeatNews/  
**Code:** https://github.com/t3dy/EsotericBeatNews  
**Deploy:** GitHub Pages (automatic on push)

---

## Current State (as of 2026-06-13)

### Features Shipped
- **News feed** (47 pages, 60 items/page) — all episodes newest-first with "emanations" framing
- **Horizontal-scroll toolbars** (mobile-optimized at 375px) — Featured Podcasts, Featured Scholars, 20 curated Topics
- **Full-text search** with source/topic filters
- **Browse by date** with sort controls  
- **23 source landing pages** — each podcast/channel with dedicated episode listing
- **20 topic curations** — cross-channel themed collections (Alchemy, Neoplatonism, Grimoires, etc.)
- **5 Featured Scholars** — Newman, Principe, Forshaw, Hutton, Yates with aggregated episodes
- **5 Featured Podcasts** — Esoterica, Modern Hermeticist, Ted Hand, Religion for Breakfast, Seekers of Unity
- **Cache-busted CSS** — versioned stylesheet links prevent stale-CSS issues after deploy
- **Responsive layout** — mobile (375px), tablet (820px), desktop (1280px)
- **291 alchemy episodes** — newly tagged Matteo Martelli videos (5 added this session) + 10 existing

### Architecture
```
C:\Dev\EsotericBeatNews/   # git clone of github.com/t3dy/EsotericBeatNews
├── sources.json          # Source metadata, topics, scholars
├── fetch_catalog.py      # yt-dlp + RSS → data/catalog.json
├── build.py              # Jinja-free static renderer
├── data/
│   └── catalog.json      # ~3,000 episodes (refresh by re-running the fetcher)
├── assets/
│   ├── style.css         # SHWEP design system (dark academic theme)
│   └── aggregator.css    # Toolbars, cards, mobile breakpoints
├── .github/workflows/    # rebuild.yml — CI renders site/ + deploys to Pages
└── site/                 # Built output (gitignored; CI regenerates it, NOT committed)
```

**Catalog refresh:** Manual `python fetch_catalog.py` (yt-dlp scrape, ~15 min) → commits `data/catalog.json` → GitHub Actions rebuilds site.

---

## What Changed This Session

### Added
1. **Matteo Martelli as featured scholar** (alchemy specialist)
   - 5 new alchemy/chemistry videos (64–102 min each)
   - Extracted all 15 chapters from "Art of Alchemy Colloquium" title
   - Added "martelli", "chymistry", "mercury" to alchemy topic keywords

2. **Mobile optimization**
   - Horizontal-scroll toolbars (no wrapping, 40–50px tall)
   - Pinned bar labels with matching backgrounds
   - Compact cards (116px thumbs on 375px viewport)
   - 2-line excerpt clamping
   - Larger tap targets (35–39px, up from ~24px)
   - Header height: 590px → 211px on mobile

3. **Featured Scholars toolbar** (matching Podcasts design)
   - 5 individual scholar pages (`scholars/[id].html`)
   - Aggregation page showing all 5 with their episodes in sections
   - Same sticky-label + horizontal-scroll pattern

4. **Cache-busting via content hash**
   - CSS links now carry version tokens (`?v=c821c0fc`)
   - On every build, stylesheet hash is computed and baked into HTML
   - Returning visitors always fetch fresh CSS (solves stale-sheet issue)

### Fixed
- None critical; mostly additive work

---

## Improvement Opportunities (Priority Order)

### 🔴 High Priority (User Experience)

**1. Podcast/YouTube filtering by content**
- **Problem:** Spiritus Mundi (William R. Newman channel) has 131 alchemy episodes out of ~150 total uploads. User has to scroll past many non-alchemy videos to find them.
- **Solution:** Add source-level `filter_title` logic to grab only alchemy-tagged uploads from channels that aren't pure-alchemy. Or create sub-playlists within sources.
- **Effort:** 2–3 hours (extend `_fetch_youtube_filtered` in `fetch_catalog.py`, update UI to show filtered counts)
- **Impact:** High (reduces noise, improves discovery)

**2. Episode duration filtering / "Bite-sized" curations**
- **Problem:** Mix of 2-min clips and 120-min lectures; users want to filter by time.
- **Solution:** Add duration filter to search (`< 20 min`, `20–60 min`, `> 60 min`) and create "Bite-sized" topic page for < 30 min episodes.
- **Effort:** 4–6 hours (update search UI, add filter state, add "audio-short" topic)
- **Impact:** Medium (useful for commute listening)

**3. Transcript search / full-text indexing**
- **Problem:** YouTube auto-transcripts exist but aren't searchable; can't find episodes by specific scholar names mentioned in audio.
- **Solution:** Use yt-dlp to fetch transcripts for YouTube videos, build a separate transcript index, search both title+summary and transcript content.
- **Effort:** 8–12 hours (yt-dlp transcript fetch, preprocessing, search integration, storage strategy)
- **Impact:** Very high (transforms discoverability; "find all mentions of Paracelsus" works even if title doesn't say it)

**4. Social sharing & episode pages**
- **Problem:** Each episode is just a card; no dedicated landing page. No og:image, og:description for Twitter/Facebook shares.
- **Solution:** Generate `episodes/[video_id].html` landing pages with full metadata, rich embeds, og: tags, and "related episodes" sidebar.
- **Effort:** 6–8 hours (build episode page template, generate pages for 2,813 items, add social card generation)
- **Impact:** Medium (increases referral traffic; nice for niche sharing in Reddit, Discord)

---

### 🟡 Medium Priority (Content & Growth)

**5. Community submissions / user-contributed sources**
- **Problem:** Only 23 sources; if a user finds a new esoteric podcast, they can't suggest it.
- **Solution:** Add a "Suggest a Source" form → GitHub issue or email workflow. Monthly review to add vetted sources.
- **Effort:** 4–6 hours (form validation, email integration, review SOP)
- **Impact:** Medium (slow growth, high engagement)

**6. Email newsletter**
- **Problem:** No way for users to stay updated without visiting weekly.
- **Solution:** Weekly digest of top 5 new episodes in each topic, sent to subscribers via SendGrid/Mailchimp.
- **Effort:** 6–10 hours (template design, CRON job or GitHub Actions workflow, unsubscribe tracking, list management)
- **Impact:** Medium–High (retention, habit-forming)

**7. Podcast app integration**
- **Problem:** Users can't subscribe to "Alchemy" topic as a podcast feed in Apple Podcasts, Spotify, etc.
- **Solution:** Generate `.rss` feeds for each topic → submit to Apple Podcasts, Spotify, Google Podcasts. Use `podcast:` namespace for metadata.
- **Effort:** 4–6 hours (RSS generation for dynamic topic feeds, feed validation, directory submission)
- **Impact:** High (huge growth vector; users discover via podcast app search)

**8. Playlist recommendations / "If you liked this, try..."**
- **Problem:** No serendipity; each episode is isolated. User finishes a Newman episode, no suggestion for the next.
- **Solution:** Build a simple recommendation engine based on shared topics/scholars. Show "Other episodes by [scholar]" or "If you liked [source], try [related_source]".
- **Effort:** 2–4 hours (collaborative filtering, sidebar rendering)
- **Impact:** Medium (increases engagement, session time)

---

### 🟢 Lower Priority (Polish & Monetization)

**9. Dark mode / color scheme toggle**
- **Problem:** Site is dark by default (good for night reading), but some users prefer light mode.
- **Solution:** Add a theme toggle in header → persist in localStorage.
- **Effort:** 2–3 hours (CSS variables, localStorage, button)
- **Impact:** Low (nice-to-have, doesn't drive revenue)

**10. Pagination improvements**
- **Problem:** 47 pages of feed is overwhelming; users rarely go to page 2.
- **Solution:** Add "infinite scroll" (lazy-load page 2 as user scrolls bottom) or improve pagination UX with "jump to page" dialog.
- **Effort:** 3–4 hours (scroll event listener, fetch next page, append to DOM)
- **Impact:** Low–Medium (reduces friction, slight engagement boost)

---

## Monetization Strategies

### 🎯 Recommended (Aligned with Mission)

**1. Patreon / Membership (Primary Revenue)**
- **Model:** Free tier (all features) + $3/month "Supporter" tier (ad-free, member badge, early newsletter)
- **Why:** Aligns with academic/niche audience; low-friction Patreon integration. Expect 2–5% conversion at launch.
- **Effort:** 2–3 hours (Patreon OAuth, gated content conditional, button)
- **Revenue Potential:** At 500 subscribers × $3/mo = $1,500/mo (achievable in 12 months with modest promotion)
- **Implementation:**
  ```
  1. Set up Patreon account (public funding page at patreon.com/esotericbeatnews)
  2. Add Patreon button in site footer
  3. (Optional) hide ads for patron-tier users
  4. Monthly thank-you email to supporters
  ```

**2. Affiliates for Books/Courses**
- **Model:** When an episode mentions a book, add an Amazon affiliate link in the episode page footnotes. Also link to recommended esoteric courses/tools.
- **Why:** Non-intrusive, high relevance. Users are already seeking knowledge; lower friction than ads.
- **Effort:** 4–6 hours (scrape ISBN from episode metadata, build affiliate link manager, add footnotes to episode pages)
- **Revenue Potential:** 2–5% of referral traffic → $200–500/mo at scale
- **Implementation:**
  1. Register with Amazon Associates, Audible, Skillshare affiliates
  2. Build a "recommended resources" section on scholar/topic pages
  3. Extract ISBNs from episode transcripts or manually curate a "must-read" list per topic

**3. Sponsorships (Premium Positioning)**
- **Model:** Esoteric-friendly brands (tarot decks, crystal shops, esoteric bookstores, online courses) sponsor a topic page or appear in newsletter.
- **Why:** Targeted audience, high intent. $500–2,000/month per sponsor at modest traffic.
- **Effort:** 4–8 hours (sponsor page template, deck setup, outreach)
- **Revenue Potential:** 2–3 sponsors @ $1,000/mo = $2,000–3,000/mo (achievable in 6–12 months)
- **Implementation:**
  1. Create a "Sponsor" page explaining rates and ad placements
  2. Reach out to 20 relevant brands (tarot, crystals, esoteric courses)
  3. Monthly reporting dashboard for sponsors

### 🟡 Possible (Lower Priority)

**4. Premium Content / Ad-Free Tier**
- **Model:** $5/month for ad-free experience + priority support.
- **Why:** Simple, proven model.
- **Caveats:** Currently no ads; would need to introduce them first, which users may dislike. Not recommended unless traffic justifies it.

**5. Marketplace / Event Hosting**
- **Model:** Curate and promote esoteric conferences, online courses, retreats.
- **Why:** Users are already seeking education; become a distributor.
- **Caveats:** High operational overhead; better as a Phase 2 after $2k/mo baseline revenue.

---

## Next 12 Weeks Roadmap

### Week 1–2: Quick Wins
- [ ] Add transcript search (yt-dlp integration) — high impact, medium effort
- [ ] Create 5 episode landing pages as prototypes — test social sharing
- [ ] Add "Suggest a Source" form + email workflow

### Week 3–4: Monetization Setup
- [ ] Launch Patreon account, integrate into site
- [ ] Research & reach out to 5 book affiliate programs (Amazon, Audible)
- [ ] Draft sponsor prospectus (1 page)

### Week 5–8: Content Growth
- [ ] Manual audit: are there 5–10 esoteric podcasts we're missing? Add them.
- [ ] Partner with 1–2 esoteric communities (Reddit /r/occult, Discord servers) for cross-promotion
- [ ] Launch weekly newsletter (top 5 new episodes per topic)

### Week 9–12: Polish & Metrics
- [ ] Generate RSS feeds for each topic, submit to Spotify/Apple Podcasts
- [ ] Add Google Analytics 4; set up Patreon conversion tracking
- [ ] Build sponsor dashboard (monthly traffic, demographic stats)

---

## Technical Debt & Maintenance

### Watch These
1. **Catalog freshness:** `fetch_catalog.py` runs on-demand; should move to nightly CRON (GitHub Actions) so catalog is always fresh.
2. ~~**NSF extraction boilerplate:** The `extraction/` folder is legacy from NSFRIPPER.~~ ✅ Done — the `extraction/` folder has been removed; no NSFRIPPER code remains.
3. **CSS asset versioning:** Currently uses content hash. If you update CSS, manually trigger rebuild or CI should handle it.
4. **YouTube API limits:** yt-dlp scrapes, no API key needed. But YouTube's IP bans can disrupt scrapes. Monitor fetch logs.

### Scripting Habits
- Always commit `data/catalog.json` after `fetch_catalog.py` runs
- Always run `python build.py` after editing `sources.json` (schema changes)
- Test topic pages visually after adding new keywords to topics

---

## Quick Start for Next Developer

```bash
# Clone and set up
git clone https://github.com/t3dy/EsotericBeatNews.git
cd EsotericBeatNews
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install yt-dlp

# Refresh catalog (pulls all videos from sources)
python fetch_catalog.py

# Build site locally
python build.py

# Serve & preview (http://localhost:8099)
python -m http.server --directory site 8099

# Deploy (GitHub Pages)
git add data/catalog.json sources.json && git commit -m "..." && git push
# CI (.github/workflows/rebuild.yml) runs build.py and deploys site/ to Pages.
# site/ is gitignored — do NOT commit it; CI regenerates it on every push.
```

---

## Key Files & Their Purposes

| File | Purpose | Edit When |
|------|---------|-----------|
| `sources.json` | Source metadata, topic keywords, scholar profiles | Adding/removing sources, changing topic keywords |
| `fetch_catalog.py` | yt-dlp + RSS scraping logic | Adding new source types (e.g., SoundCloud, Substack) |
| `build.py` | Static site renderer (3500+ LOC) | Adding new page types, changing layout logic |
| `assets/style.css` | SHWEP design system variables | Changing color scheme, typography |
| `assets/aggregator.css` | Toolbars, cards, mobile breakpoints | Tweaking responsive behavior |
| `data/catalog.json` | Authoritative episode database | (Auto-generated; don't edit) |
| `/site/*` | Generated HTML output | (Auto-generated; commit to GH Pages) |

---

## Parting Thoughts

This is a **niche but high-intent audience**. Esoteric studies learners are:
- Willing to pay for quality content ($5–20/mo)
- Enthusiastic about discovery (strong referral potential)
- Often buying related books, courses, tools (affiliate upside)
- Community-oriented (newsletter, Discord/Reddit engagement)

**Focus on retention first.** At launch, you likely have ~50–100 weekly visitors. Get them to return every 2 weeks by making the site indispensable:
1. Email newsletter (easy to set up, high ROI)
2. Transcript search (transforms discoverability)
3. Patreon (simple funding)

Once you have 300+ weekly visitors and 2–3% Patreon conversion, sponsorships become realistic.

**Good luck! This is genuinely useful work.** 🔮

---

*Document generated: 2026-06-13*  
*Project: Esoteric Beat News*  
*Live: https://t3dy.github.io/EsotericBeatNews/*
