# Esoteric Beat News — Strategy & Roadmap

**Last updated:** 2026-06-13  
**Maintainer:** Ted Hand (`ted.hand@gmail.com`)  
**Status:** ~50–100 weekly visitors; basic monetization live (donate buttons)

---

## Current State

### Site Features ✓
- **Live:** https://t3dy.github.io/EsotericBeatNews/
- **Episodes:** 3,070 items from 25 sources (podcasts, YouTube channels)
- **Topics:** 20 curated cross-channel collections (Alchemy, Neoplatonism, Grimoires, …)
- **Sources:** SHWEP, Esoterica, Modern Hermeticist, Seekers of Unity, + 21 others
- **Featured Scholars:** Hutton, Yates, Forshaw, Newman, Principe, Dzwiza
- **Mobile-optimized:** 375px, 820px, 1280px breakpoints
- **Search:** Full-text search with source/topic filters
- **Browse by date:** Episode grid with sort controls
- **Playlists:** 28 Esoterica thematic playlists
- **No dependencies:** Python stdlib + yt-dlp (fetch only)
- **CI/CD:** GitHub Actions auto-deploy on push

### Monetization Live
- **Donate buttons** (top of every page):
  - Patreon: `patreon.com/esotericbeatnews`
  - PayPal: `paypal.me/tedhand` → `ted.hand@gmail.com`
- **No ads, no tracking, no paywalls yet**

### Tech Stack
- **Fetch:** `yt-dlp` + Python `urllib` (no API keys)
- **Data:** `data/catalog.json` (committed snapshot, 3,070 episodes)
- **Build:** `build.py` (offline, stdlib only)
- **Deploy:** GitHub Pages + GitHub Actions
- **CSS:** Hand-written (SHWEP design system, dark academic)
- **Search:** Client-side JavaScript (site/data.json)

---

## Improvement Opportunities (Priority Order)

### 🔴 High Priority (6–12 weeks)

#### 1. Email Newsletter
**Problem:** Users have no way to stay updated without visiting weekly.  
**Solution:** Weekly digest of top 5 new episodes per topic, opt-in mailing list.  
**Effort:** 6–8 hours  
**Impact:** HIGH — habit-forming, drives recurring visits.  
**Tech:** SendGrid/Mailchimp API + GitHub Actions workflow (runs every Sunday)  
**Revenue:** Modest (builds audience for later sponsors/affiliate revenue)

#### 2. Transcript Search
**Problem:** YouTube auto-transcripts exist but aren't searchable. Can't find episodes by scholar names mentioned in audio.  
**Solution:** Use yt-dlp to fetch transcripts for YouTube videos, build full-text index, integrate with search.  
**Effort:** 10–12 hours  
**Impact:** VERY HIGH — transforms discoverability ("find all mentions of Paracelsus")  
**Tech:** yt-dlp transcript fetch → `.vtt` parsing → add to `catalog.json` → search indexing  
**Revenue:** None, but huge engagement boost

#### 3. Patron Dashboard (Tier 2 Patreon)
**Problem:** Can't see who your patrons are or send them personal thanks.  
**Solution:** Sync patron list via Patreon API daily, show "Supporter" badges on site, send thank-you emails.  
**Effort:** 6–8 hours  
**Impact:** MEDIUM — shows patrons they matter, builds community feel.  
**Tech:** Python script + `patrons.json` (see PATREON.md for full guide)  
**Revenue:** +$50–150/month (retention via recognition)

#### 4. Episode Landing Pages (Social Sharing)
**Problem:** Each episode is just a card; no dedicated page for social shares.  
**Solution:** Generate `episodes/[id].html` with full metadata, og:image/og:description, "related episodes" sidebar.  
**Effort:** 6–8 hours  
**Impact:** MEDIUM — increases referral traffic via Reddit/Discord/Twitter shares.  
**Tech:** Add to `build.py` render loop, generate 3,070 individual pages.

---

### 🟡 Medium Priority (3–6 months)

#### 5. Content Filtering (By Duration & Source Mix)
**Problem:** Spiritus Mundi (Newman channel) has 131 alchemy videos out of ~150 total. Users scroll past non-alchemy noise.  
**Solution:** Add duration filter to search (`< 20 min`, `20–60 min`, `> 60 min`); create "Bite-sized" topic page for short episodes.  
**Effort:** 4–6 hours  
**Impact:** MEDIUM — reduces friction, useful for commute listening.

#### 6. Podcast App Integration (RSS Feeds)
**Problem:** Users can't subscribe to "Alchemy" topic as a podcast in Apple Podcasts/Spotify.  
**Solution:** Generate per-topic RSS feeds, submit to podcast directories.  
**Effort:** 4–6 hours  
**Impact:** HIGH — huge growth vector (podcast app search brings discovery).  
**Revenue:** None direct, but massive reach.

#### 7. Community Submissions
**Problem:** Only 25 sources. Users can't suggest new podcasts.  
**Solution:** "Suggest a Source" form → GitHub issue workflow → monthly review for new sources.  
**Effort:** 4–6 hours  
**Impact:** MEDIUM — enables user-driven growth, high engagement.

#### 8. Advanced Analytics
**Problem:** No insight into traffic, bounce rate, which topics/sources are popular.  
**Solution:** Google Analytics 4 (free, privacy-friendly) with conversion tracking for Patreon.  
**Effort:** 2–3 hours  
**Impact:** MEDIUM — informs future strategy (which content to promote).

---

### 🟢 Lower Priority (Polish & Monetization)

#### 9. Sponsored Content / Affiliate Links
**Problem:** No revenue beyond Patreon.  
**Solution:** Partner with esoteric bookstores, tarot decks, courses. Add affiliate links on topic/scholar pages.  
**Effort:** 4–8 hours (deal negotiation, link integration)  
**Impact:** MEDIUM — $200–500/month at scale (2–5% referral traffic)  
**Revenue:** 2–5% commission on referred sales

#### 10. Sponsorships (Premium)
**Problem:** No way for brands to reach your niche audience.  
**Solution:** Sponsor a topic page or newsletter section (e.g. "This Neoplatonism roundup brought to you by [Tarot Deck Co]").  
**Effort:** 4–6 hours (sponsor page template, outreach)  
**Impact:** MEDIUM-HIGH — $500–2,000/month per sponsor at 300+ weekly visitors  
**Revenue:** $1,000–3,000/month (2–3 sponsors)

#### 11. Dark Mode Toggle
**Problem:** Some users prefer light mode (though site defaults to dark).  
**Solution:** Add theme toggle in header, persist in localStorage.  
**Effort:** 2–3 hours  
**Impact:** LOW (nice-to-have, doesn't drive revenue)

#### 12. Infinite Scroll
**Problem:** 52 pages of feed feels overwhelming.  
**Solution:** Lazy-load next page as user scrolls bottom (or improve pagination UX).  
**Effort:** 3–4 hours  
**Impact:** LOW–MEDIUM (reduces friction, slight engagement boost)

---

## 12-Week Roadmap

### Weeks 1–2: Quick Wins
- [ ] Set up Google Analytics 4 and Patreon conversion tracking
- [ ] Deploy Tier 2 Patreon integration (patron list sync)
- [ ] Manual audit: are there 5–10 esoteric podcasts we're missing? Add them.

### Weeks 3–4: Newsletter Launch
- [ ] Choose email service (SendGrid free tier or Mailchimp)
- [ ] Design weekly digest template (top 5 episodes per topic)
- [ ] Set up GitHub Actions workflow (runs every Sunday 8am UTC)
- [ ] Add "Subscribe to newsletter" section on About page

### Weeks 5–8: Discoverability
- [ ] Add transcript search (yt-dlp integration)
- [ ] Generate episode landing pages (social-friendly)
- [ ] Prototype "Bite-sized" duration filter (< 30 min topic page)

### Weeks 9–12: Growth
- [ ] Generate RSS feeds for each topic, submit to Spotify/Apple Podcasts
- [ ] Create "Suggest a Source" form + GitHub issue workflow
- [ ] Reach out to 2 esoteric communities (Reddit /r/occult, Discord) for cross-promotion
- [ ] Review sponsorship prospects; draft 1-page pitch

---

## Monetization Strategy

### Primary Revenue (Patreon)
- **Model:** Free site + Patreon for supporters
- **Tiers:**
  - **Free:** All features, no ads
  - **$3/mo Supporter:** Early access to newsletter, patron badge on site
  - **$10/mo Researcher:** Early newsletter + monthly "deep dive" on a scholar/topic
  - **$25/mo Patron:** Above + private Discord, direct message access
- **Projection:** 50 subs @ $3 (median) = $150/mo → $1,800/year. Achievable in 12 months with modest promotion.

### Secondary Revenue (Affiliates & Sponsors)
- **Affiliates:** Amazon Associates (books), Audible, Skillshare ($200–500/mo @ scale)
- **Sponsors:** 2–3 brands @ $1,000–2,000/mo = $2,000–6,000/mo (achievable in 18 months)
- **Newsletter sponsorships:** Premium sponsor in weekly digest (50% more premium than site sponsor)

### Tertiary Revenue (Events & Education)
- **Webinars:** Monthly "office hours" on Patreon (20 mins Q&A with you)
- **Courses:** Curated deep-dives sold via Patreon or separately ($25–50)
- **Merchandise:** Limited-edition tarot decks or enamel pins (partner with supplier, 30% margin)

### What NOT to do
- ❌ Invasive ads (breaks the vibe)
- ❌ Tracking / data sale (betrays trust)
- ❌ Paywalling the search / topic pages (free features are your moat)
- ❌ Cryptocurrency / NFTs (alienates your serious audience)

---

## Key Metrics to Watch

| Metric | Current | Target (6mo) | Target (12mo) |
|---|---|---|---|
| Weekly visitors | 50–100 | 200–300 | 500–1000 |
| Newsletter subscribers | 0 | 50–100 | 200–300 |
| Patreon supporters | 0 | 5–10 | 20–50 |
| Monthly Patreon revenue | $0 | $50–100 | $150–300 |
| Top traffic source | Direct | Newsletter | Podcast app / Reddit |
| Bounce rate | (unknown) | <60% | <50% |

---

## Guardrails & Non-Negotiables

1. **No tracking / data sale.** Your audience is privacy-conscious. Keep it that way.
2. **Free search always.** Never paywall the core discovery features.
3. **Authors own their content.** This is a fan index, not a re-host. Link back always.
4. **Manual catalog refresh.** Keep `data/catalog.json` human-reviewed; don't auto-ingest everything.
5. **Minimal dependencies.** Stdlib-only render = zero maintenance debt.

---

## Workflow & Governance

### Catalog Refresh (Monthly)
```bash
python fetch_catalog.py    # pulls latest episodes (local machine, ~15 min)
python build.py            # renders site (local, offline)
git add data/catalog.json && git commit -m "Refresh catalog (March 2026)" && git push
# CI auto-deploys within 2 minutes
```

### Content Moderation
- **New source:** Human review before adding to `sources.json`
- **Tagging disputes:** Adjust `sources.json` `keywords` or add to `tags.json`
- **Spam/low-effort sources:** Remove; update the "why we curate" doc

### Patreon Sync (Weekly, Automated)
```bash
# Via cron or GitHub Actions:
python scripts/sync_patrons.py
git add patrons.json && git commit -m "Auto: sync patrons" && git push || true
```

### Newsletter Send (Weekly, Automated)
```bash
# Sunday 8am UTC, via GitHub Actions:
python scripts/digest.py | sendgrid_api send
# Fetch top 5 new episodes per topic, email to subscriber list
```

---

## Exit Strategy (Optional)

If you ever want to pass this on or step back:
- **Repo is public.** Anyone can fork and run locally.
- **No custom database or secrets in code.** Patreon token is env var, not committed.
- **Documentation is in `CLAUDE.md` and this file.** Next maintainer has a clear roadmap.
- **CI is automated.** Future owner just needs to `git push` to deploy.

---

## Questions & Next Steps

**For the next session:** Pick 1–2 items from the High Priority list and build them. Recommend:
1. **Newsletter** — biggest bang for effort (6–8 hours, habit-forming)
2. **Transcript search** — highest discoverability boost (10–12 hours, but transformative)

Start with whichever excites you most. Both will compound growth.

---

*Document: 2026-06-13*  
*Esoteric Beat News strategy and roadmap*  
*Maintainer: Ted Hand*
