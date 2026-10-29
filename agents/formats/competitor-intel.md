> **Weekly deep dive (Omar's rule):** this team now runs once a week, so every run goes to the max. Use 30-40 searches/fetches. Cover each competitor's current ads (Meta Ad Library, TikTok Creative Center, Google Ads Transparency Center where reachable), their best-performing content and view counts, pricing and offer changes, review complaints, and recent launches. End with three clear lists in the brief's notes and in the ideas: **Copy** (what works for them that we should use now), **Beat** (where they're weak and how we win: features, price, angle), and **Improve** (concrete changes to our own product, store listing or landing page). Only real findings, never invented numbers.

# Competitor Watch: content, ads and growth

Goal: for each main competitor, find out what they post, how many views it gets, how they advertise, and how they grew, and what Omar should copy.

## Pick competitors
Keep 4-6 named competitors in `competitors` (reuse last run's list and refresh 2-3 of them each run; add a new one when you find a fast riser).

## For each competitor, search for:
1. **Their content + views**: their TikTok, Instagram Reels, YouTube Shorts and LinkedIn accounts. Find their top recent posts with view counts (search "<name> tiktok", "<name> site:tiktok.com", their YouTube channel, fetch the pages you can). Note the hook, the format (founder talking head, UGC creator, screen recording, meme) and what made it work.
2. **Ads**: Meta Ad Library (facebook.com/ads/library, search the brand), TikTok Creative Center Top Ads (ads.tiktok.com/business/creativecenter), LinkedIn Ad Library (linkedin.com/ad-library), Google Ads Transparency Center. Record which ads are running, how long they've run (long-running = profitable), hooks, offers, landing pages. If a library isn't reachable from your tools, say so and use articles/teardowns instead.
3. **How they grew**: Product Hunt launch, founder interviews/podcasts, Indie Hackers or Starter Story posts, Reddit threads, affiliate/UGC programs, SEO pages, Chrome Web Store user counts and rating history (LinkedAI), pricing changes.

Only real findings. Never invent views, ads, revenue or links. If you couldn't find a number, leave it out.

## Output: `competitors` and `competitorsUpdated` in data/<team>/state.json
```
"competitors": [{
  "name", "url", "oneLiner": "what they are, who for", "price": "e.g. $9/mo",
  "channels": ["TikTok @x", "YouTube", ...],
  "topContent": [{"platform","title","url","views","date","whyItWorked"}],
  "contentStrategy": "1-2 sentences",
  "ads": [{"platform","hook","url","running":"since Aug 2026 / 40+ days","notes"}],
  "adStrategy": "1-2 sentences",
  "howTheyGrew": "2-3 sentences with the real levers",
  "lessonForUs": "one concrete thing Omar should copy or counter this week"
}]
```
At least one of the Copywriter's ideas each run must directly use a competitor lesson (say which in its `why`).
