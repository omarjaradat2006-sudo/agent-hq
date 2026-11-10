# Trading Desk: Omar's news-driven PAPER-trading bot

Fake money only (Alpaca paper account). The bot refuses to talk to Alpaca's live URL.

## How a trade happens
1. **News Scout** reads Alpaca news (Benzinga), CNBC, Google News (Reuters, AP and more), and, when Agent Reach is set up,
   key X accounts + r/wallstreetbets, r/stocks, r/CryptoCurrency, r/worldnews using your **secondary** accounts.
2. **News Analyst (Gemini)** groups headlines into stories and applies your playbook: real news or not, which **halal-screened**
   assets, up or down, how confident.
3. **Confirmation Checker**: 2+ different publishers (at least one real news outlet), confidence at least 60%, volume at least 1.5x normal
   for that time of day, price moved +0.3% to +3% the expected way (more than that = too late), news less than 6h old.
4. **Deep Analyst (TradingAgents on Gemini)**: max 5 a day. Must say Buy or Overweight. Any error = no trade.
5. **Risk Officer** (hard-coded): 5% per trade, max 5 positions, cash only, -3% stop and +6% target set at entry,
   stocks out after 3 trading days, no new stock trades in the last 30 min, crypto out after 48h,
   -3% day = no new trades that day, -10% from start = sell everything, lock, pop-up + red banner.
6. **Trader** places the order. Stocks: a bracket order (stop + target both live on Alpaca's servers).
   Crypto: the stop-loss lives on Alpaca's servers; the +6% target and 48h limit are checked by the bot.
7. Bad news on something it holds = sell. Meme/celebrity coins = **watch mode only**, never traded.

All limits are in `config.py`. The AI can only say no; it can't change a limit.

## Files
| | |
|---|---|
| `windows/setup.bat` | one-time setup (asks for everything up front, then installs) |
| `windows/start_trading_bot.bat` | double-click to run; restarts itself if it crashes |
| `windows/install_autostart.bat` / `remove_autostart.bat` | Task Scheduler entry: starts 1 min after you log in |
| `windows/run_backtest.bat` | rules over the last 30 days of past news + prices |
| `windows/check.bat` | tests keys and connections, trades nothing |
| `.env` | your keys (stays on the laptop, git-ignored) |
| `local/` | private working memory + logs (git-ignored) |
| `../data/trading/` | what the Trading Desk shows: saved to GitHub a few times a day |

Commands (from the repo folder): `python -m trading_bot.bot run | once | check | universe | publish | unlock`

## On the Oracle server ("openclaw"): where it runs now (Nov 2026)
Runs 24/7 as a systemd service, PAPER only, in its own copy of the repo (`~/agent-hq-trading`), so the Gemini
team runner's hourly `git reset --hard` in `~/agent-hq` can never wipe unsaved trade history.

| | |
|---|---|
| `server/install.sh` | one-time install: own clone, Python packages, systemd units (does not start the bot) |
| `server/set_keys.sh` | type the Alpaca PAPER keys hidden (`read -s`) into `~/.trading-bot.env` (chmod 600, outside git). Refuses live `AK...` keys |
| `server/tb` | `tb check / start / stop / status / logs / report / backtest 365 / backtest-log / update` |
| `agenthq-trading.service` | the bot. `Restart=always`, starts at boot, refuses to start unless it points at the paper URL |
| `agenthq-trading-report.timer` | builds the 7-day report every evening (4:45 PM New York) |

The Gemini key is read from `~/.agent-hq.env` (same file the agent teams use). Never run the laptop copy at
the same time: two bots on one paper account would double-trade.

**7-day report** (`python -m trading_bot.weekly`): trades, win rate, P&L, max drawdown, every risk-rule trigger
and every error for the first 7 days, from `data/trading/ledger.json` + `local/events.jsonl`. Written to
`data/trading/report_7d.json` (Trading tab: "7-day test") and `data/trading/report_7d.md`.

**Long backtest** (`tb backtest 365`): news cached per month, Gemini triage cached per day and capped at 150 calls a
run (`--max-calls`), so it can take a few runs on the free tier and always continues where it stopped.
