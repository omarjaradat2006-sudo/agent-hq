# Agent HQ setup

Your sites: https://omarjaradat2006-sudo.github.io/agent-hq/

Keys and tokens go into **GitHub Secrets** only (repo → Settings → Secrets and variables → Actions → New repository secret). Secrets stay hidden even though the repo is public. Never paste them into a file, a commit, an issue, or a chat.

After adding secrets, go to the **Actions** tab → **Data collectors** → **Run workflow** to test right away instead of waiting for the hour.

---

## 1. YouTube public data (trending + outliers) — about 10 minutes

1. Go to https://console.cloud.google.com and create a project called `agent-hq`.
2. **APIs & Services → Library**: enable **YouTube Data API v3** and **YouTube Analytics API**.
3. **APIs & Services → Credentials → Create credentials → API key**. Edit it, under *API restrictions* pick **YouTube Data API v3**, save.
4. Add it to GitHub as secret **`YT_API_KEY`**.

This powers "Trending now" on both the YouTube and TikTok sites. Each video gets an outlier score: its views compared to that channel's normal average.

## 2. Your YouTube analytics (both channels) — about 10 minutes

1. Same Google project → **OAuth consent screen**: choose *External*, app name `Agent HQ`, your email. Add yourself as a test user.
2. Then press **Publish app** (status "In production"). If you skip this, Google kills the connection every 7 days. Google will show an "unverified app" warning when you sign in. That's expected because it's your own app: click *Advanced → Go to Agent HQ*.
3. **Credentials → Create credentials → OAuth client ID → Desktop app**. Copy the Client ID and Client Secret.
4. Add them as secrets **`YT_CLIENT_ID`** and **`YT_CLIENT_SECRET`**.
5. On your laptop, download `scripts/google_connect.py` from this repo and run `python3 google_connect.py`. Sign in and pick **Bounce Theory**. Copy the printed token into secret **`YT_REFRESH_TOKEN_1`**.
6. Run it again, pick **Ambient Escape**, save as **`YT_REFRESH_TOKEN_2`**.

## 3. Your TikTok stats — setup 15 minutes, then TikTok may need to review

1. Go to https://developers.tiktok.com, log in with your TikTok account, and create an app.
2. Add **Login Kit** and request the scopes `user.info.basic`, `user.info.stats`, `video.list`.
3. Set the redirect URI to exactly:
   `https://omarjaradat2006-sudo.github.io/agent-hq/auth/tiktok.html`
4. Use the app's **Sandbox** and add your own TikTok account as a target user so you can connect without waiting for review. If TikTok requires review for your app, submit it and say it's a personal dashboard that only reads your own account's stats.
5. Add the Client Key and Client Secret as secrets **`TT_CLIENT_KEY`** and **`TT_CLIENT_SECRET`**.
6. On your laptop run `python3 scripts/tiktok_connect.py`, approve in TikTok, paste the code from the Agent HQ page, and save the printed token as **`TT_REFRESH_TOKEN`**. It lasts about a year.

TikTok doesn't offer retention graphs or audience demographics through its API. For those, screenshot TikTok Studio and send them to Claude.

## 4. Free stock footage for Ambient Escape (2 minutes)

1. Sign up free at https://pixabay.com , then open https://pixabay.com/api/docs/ while logged in.
2. Your key is shown in green next to `key` in the Parameters section. Add it to GitHub Secrets as **`PIXABAY_API_KEY`**.
3. Pexels has paused new API keys. If they reopen, a key saved as **`PEXELS_API_KEY`** is used first.

Every morning the YouTube team lists the clips its lineup needs. The **Footage fetcher** workflow then downloads them and attaches them to that day's GitHub Release, so your batch has them ready. You never film anything.

## What runs when

| What | Where | When |
|---|---|---|
| Data collectors (your stats, niche trends) | GitHub Actions | Every hour (trend scan every 6 hours to stay inside YouTube's free quota) |
| Footage fetcher (free Pexels/Pixabay clips) | GitHub Actions | Right after the YouTube team plans the day |
| TikTok team (Analyst, Strategist, Copywriter) | Claude scheduled task | Daily ~9:40 AM |
| Chief of Staff brief | Claude scheduled task | Daily ~11:40 AM |

## Approving ideas

On a team site, press **Approve**, **Pass** or **Mark filmed**. It opens a GitHub issue that's already filled in. Press **Submit new issue**. The next agent run reads it, updates the site, and closes the issue.

## Editing what gets researched

Change the search topics in `collectors/niches.json`.
