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

## Moving to the Oracle server
1. On the server: `git clone https://github.com/omarjaradat2006-sudo/agent-hq && cd agent-hq && bash trading_bot/server/install.sh`
2. Copy `trading_bot/.env` (and optionally `trading_bot/local/state.json`) from the laptop.
3. On the laptop: run `remove_autostart.bat` and close the bot window, so only one copy trades.
Trade history and the kill switch live in `data/trading/ledger.json`, which is already in git, so the server picks up where the laptop stopped.
