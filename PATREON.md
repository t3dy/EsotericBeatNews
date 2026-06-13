# Patreon Integration & Workflow Guide

## Current Setup

You've added a donate button to the top of the site that links to:
- **Patreon:** `https://patreon.com/esotericbeatnews`
- **PayPal:** `https://paypal.me/tedhand` (resolves to `ted.hand@gmail.com`)

This is a **simple, zero-friction approach** — users click and donate. No authentication, no special Patreon tooling required yet. The site doesn't gate any content or require patron login.

---

## Integration Options (Complexity Tiers)

### Tier 1: Simple Link (Current)
**What:** Just the button you have now.
- Pros: Zero setup, works immediately.
- Cons: No way to know who your patrons are, can't give them perks.
- Effort: 0 hours.
- Revenue impact: High (simple = high conversion).

### Tier 2: Patreon API + Patron List (Recommended Next Step)
**What:** Sync Patreon supporters into your system, show them a "Supporter" badge, send them thank-you emails.

**How it works:**
1. Create a Patreon app at https://www.patreon.com/portal/registration/register-as-creator → Apps & Integrations
2. Get your **Creator Access Token** (keep it secret — it identifies you)
3. Use Patreon's REST API to fetch your patron list and pledge amounts:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     https://www.patreon.com/api/oauth2/v2/campaigns?include=members \
     | python -m json.tool
   ```
4. Sync the patron list locally (e.g., once/day via a script)
5. On your site's frontend, conditionally show a `<span class="patron-badge">⭐ Supporter</span>` 
   next to a user's name (if you add usernames/accounts later)

**Effort:** 6–8 hours (API integration, local sync, frontend display)
**Revenue boost:** Modest — shows patrons they're recognized, strengthens community feel
**CLI tools:**
- `gh secret set PATREON_TOKEN -b "$YOUR_TOKEN"` (store securely in GitHub if you automate syncing)
- Python script to fetch and cache patrons locally
- (Optionally) Add a GitHub Actions workflow to sync daily

**File structure:** Consider adding:
```
patrons.json  # auto-generated list of current patrons (gitignored by default)
scripts/sync_patrons.py  # one-off script to fetch patron list
```

---

### Tier 3: Gated Content (Advanced)
**What:** Patrons get early access to new episodes, a weekly newsletter, or a private Discord invite.

**How it works:**
1. Use Patreon's `includes=members` endpoint to get pledge tiers
2. On your site, conditionally hide/show content based on patron status
3. Require Patreon login via OAuth to verify patron status

**Effort:** 12–16 hours (OAuth flow, database of patrons, frontend gating, security)
**Revenue boost:** High — exclusive content drives conversions
**Complexity:** Significantly higher; requires authentication + database

---

## Quick Setup: Tier 2 (Recommended)

If you want to add patron recognition without heavy lifting, here's the flow:

### Step 1: Get your Patreon access token
1. Go to https://www.patreon.com/portal/registration/register-as-creator
2. Sign in as a creator, click **Apps & Integrations** in your creator dashboard
3. Create a new app (name: "EsotericBeatNews")
4. Copy your **Creator Access Token** (looks like `xxx...yyy`)
5. Store it securely (never commit to git):
   ```bash
   # On your local machine, add to ~/.bashrc or ~/.zshrc
   export PATREON_TOKEN="your_token_here"
   ```

### Step 2: Fetch your patron list (Python)
Create `scripts/sync_patrons.py`:

```python
#!/usr/bin/env python3
import os, json, urllib.request
from pathlib import Path

TOKEN = os.getenv("PATREON_TOKEN")
if not TOKEN:
    raise RuntimeError("PATREON_TOKEN env var not set")

ROOT = Path(__file__).parent.parent
PATRONS_FILE = ROOT / "patrons.json"

url = "https://www.patreon.com/api/oauth2/v2/campaigns?include=members,creator"
req = urllib.request.Request(
    url,
    headers={"Authorization": f"Bearer {TOKEN}"}
)
response = json.loads(urllib.request.urlopen(req).read())

members = response.get("included", [])
patrons = [
    {
        "name": m.get("attributes", {}).get("full_name", ""),
        "tier": m.get("relationships", {}).get("currently_entitled_tiers", {}).get("data", [{}])[0].get("id", ""),
        "pledge": m.get("attributes", {}).get("lifetime_support_cents", 0) / 100,
    }
    for m in members if m.get("type") == "member"
]

PATRONS_FILE.write_text(json.dumps(patrons, indent=2), encoding="utf-8")
print(f"Synced {len(patrons)} patrons to {PATRONS_FILE}")
```

Run it once a week:
```bash
export PATREON_TOKEN="your_token"
python scripts/sync_patrons.py
```

### Step 3: Add to `.gitignore` (already there, but confirm)
```
patrons.json
scripts/
.env
```

### Step 4: Display patrons on-site (optional)
In `build.py`, load `patrons.json` and pass it to the template:
```python
patrons = []
if Path("patrons.json").exists():
    patrons = json.loads(Path("patrons.json").read_text())
```

Then in your pages, render a "Thanks to our patrons" section (requires frontend work).

---

## CLI Workflow Ideas

### Daily sync via cron (local machine)
```bash
# Add to crontab -e
0 3 * * * cd /c/Dev/EsotericBeatNews && export PATREON_TOKEN="$(cat ~/.patreon_token)" && python scripts/sync_patrons.py
```

### Or, GitHub Actions (optional)
Create `.github/workflows/sync-patrons.yml`:
```yaml
name: Sync Patrons
on:
  schedule:
    - cron: '0 3 * * *'  # Daily at 3am UTC
  workflow_dispatch: {}
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: |
          export PATREON_TOKEN="${{ secrets.PATREON_TOKEN }}"
          python scripts/sync_patrons.py
      - run: git add patrons.json && git commit -m "Auto: sync patrons" && git push || true
```

Store your token as a GitHub secret: **Settings → Secrets → New repository secret → `PATREON_TOKEN`**

---

## Patreon Links & Resources

- **Patreon Creator Dashboard:** https://www.patreon.com/portal
- **API Docs:** https://docs.patreon.com/ (REST v2)
- **OAuth Guide:** https://docs.patreon.com/#oauth
- **Webhook Guide:** https://docs.patreon.com/#webhooks (for real-time patron updates)

---

## Revenue Expectations

| Model | Setup | Subscribers | Monthly Revenue |
|---|---|---|---|
| **Just a button** (current) | <1h | 5–15 | $25–75 |
| **Button + patron list** | 6–8h | 10–30 | $50–150 |
| **Button + early access** | 12–16h | 20–50 | $100–250 |
| **Full gated membership** | 30h+ | 50–200 | $250–1000+ |

At your current scale (~50–100 weekly visitors), start with Tier 1 or Tier 2. Move to gating only when you have 300+ weekly visitors and early-adopter patrons asking for exclusive content.

---

## Recommendation

**Next step:** Set up Tier 2 (simple patron list sync). It's a low-effort win that shows patrons they matter without adding complexity. Once you have 10–20 regular patrons, consider exclusive content (Discord, newsletter) or tier-based badges.

Don't over-engineer this early. The button works; let it work.
