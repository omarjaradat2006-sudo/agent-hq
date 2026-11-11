"""Omar's rules, in code. PAPER TRADING ONLY.

The numbers in RISK and HALAL are hard limits: the AI layers (Gemini triage, TradingAgents)
can only say "no" or pick from what these rules allow; nothing they return can raise a
limit, pick a blocked asset or switch to a live account.
"""
from types import MappingProxyType as _frozen

# ---------------------------------------------------------------- broker (paper only)
ALPACA_TRADING_URL = "https://paper-api.alpaca.markets"   # never the live URL
ALPACA_DATA_URL = "https://data.alpaca.markets"

# ---------------------------------------------------------------- risk limits (hard)
RISK = _frozen({
    "max_pct_per_trade": 0.05,        # 5% of account equity per trade
    "max_open_positions": 5,
    "stop_loss_pct": 0.03,            # -3%, placed on Alpaca's side when the trade opens
    "take_profit_pct": 0.06,          # +6%
    "stock_max_hold_trading_days": 3,
    "stock_no_new_trades_before_close_min": 30,
    "stock_first_entry_after_open_min": 10,   # let opening auction noise settle
    "crypto_max_hold_hours": 48,
    "daily_loss_halt_pct": 0.03,      # down 3% on the day -> no new trades today
    "total_loss_kill_pct": 0.10,      # down 10% from the start -> sell all, lock, alert
})

# ---------------------------------------------------------------- confirmation
CONFIRM = _frozen({
    "min_publishers": 2,              # 2 different publishers...
    "min_news_publishers": 1,         # ...at least one a real news outlet (X/Reddit alone = rumour)
    "min_confidence": 0.60,           # Gemini triage confidence
    "min_rvol": 1.5,                  # volume at least 1.5x normal
    "min_move_pct": 0.003,            # moved at least +0.3% the expected way
    "max_move_pct": 0.03,             # but not more than +3% (half the profit target): too late
    "event_fresh_hours": 6,           # news older than this is stale
    "sell_min_confidence": 0.60,      # bad news on a holding: 1 credible source is enough to exit
})

# Entry-rule modes (switch with `tb rules strict|loose|any`, saved as TRADING_RULES in ~/.trading-bot.env).
# Only the ENTRY filters change. Stop-loss, 5%/trade, 5 positions, -3% day halt, -10% kill switch never change.
RULE_MODES = {
    "strict": {},                                                   # 2 publishers, volume 1.5x (the original)
    "loose": {"min_rvol": 1.2, "single_source": "reputable"},       # 1 reputable outlet is enough when price+volume confirm
    "any": {"min_rvol": 1.2, "single_source": "any_news"},          # 1 news outlet of any kind (not X/Reddit alone)
    # aggressive: 1 news outlet, NO volume rule (the free IEX feed sees ~2-3% of volume and the bot often reads
    # the news after the volume burst), price must still be moving the right way (+0.3% to +3%), and news that
    # breaks while the market is closed stays tradable until 12:00 PM New York the next trading day
    "aggressive": {"min_rvol": 0.0, "single_source": "any_news", "carry_overnight": True},
}
REPUTABLE = {
    "benzinga", "reuters", "bloomberg", "associated press", "ap", "cnbc", "the wall street journal", "wsj",
    "financial times", "marketwatch", "barron's", "dow jones", "yahoo finance", "investor's business daily",
    "sec filing", "the new york times", "cnn business", "fox business", "axios", "nikkei", "coindesk", "the block",
}


def rules_mode():
    import os
    m = (os.environ.get("TRADING_RULES") or "strict").strip().lower()
    return m if m in RULE_MODES else "strict"


def confirm_rules(mode=None):
    r = dict(CONFIRM)
    r.update(RULE_MODES[mode or rules_mode()])
    r["mode"] = mode or rules_mode()
    return r


def sources_ok(pubs, news_pubs, rules):
    """(ok, label). 2+ publishers incl. 1 news outlet always passes; loose/any also accept a single outlet."""
    if len(pubs) >= rules["min_publishers"] and len(news_pubs) >= rules["min_news_publishers"]:
        return True, f"{len(pubs)} sources"
    one = rules.get("single_source")
    if one == "any_news" and news_pubs:
        return True, "1 news source"
    if one == "reputable" and any(p.lower() in REPUTABLE for p in news_pubs):
        return True, "1 reputable source"
    return False, None


DEEP = _frozen({
    "max_per_day": 5,                 # TradingAgents runs per day (Gemini free tier)
    "approve_ratings": ("Buy", "Overweight"),
    "timeout_min": 20,
})

# ---------------------------------------------------------------- halal rules (hard)
HALAL = _frozen({
    "no_margin": True, "no_short": True, "no_options": True, "no_futures": True, "no_leverage": True,
    "max_debt_to_market_cap": 0.33,   # AAOIFI-style ratio
    "allow_conventional_defense": True,  # defense tech without weapons of mass harm (PLTR, AVAV, KTOS)
})

# SEC industry (SIC) codes that fail the business screen.
SIC_EXCLUDED = [
    (6000, 6799, "banks, lenders, insurance, finance"),
    (2080, 2085, "alcohol"), (5180, 5182, "alcohol wholesale"), (5921, 5921, "liquor stores"),
    (2100, 2199, "tobacco"),
    (7990, 7999, "gambling / casinos"), (7011, 7011, "hotels and casinos"),
    (2011, 2013, "meat packing (pork)"),
    (3480, 3489, "ordnance / weapons"), (3760, 3769, "guided missiles"), (3795, 3795, "tanks"),
]

# Named companies that fail even if their industry code looks fine.
BLOCKLIST = {
    # weapons of mass harm: nuclear weapons, ICBMs, missiles
    "LMT": "nuclear weapons / missiles", "NOC": "nuclear ICBMs", "GD": "nuclear submarines",
    "RTX": "missiles", "BA": "ICBMs / military", "HII": "nuclear submarines", "LHX": "missiles",
    "BWXT": "naval nuclear", "HON": "manages a nuclear weapons plant", "LDOS": "nuclear weapons work",
    # alcohol / pork / gambling / adult
    "BUD": "alcohol", "STZ": "alcohol", "TAP": "alcohol", "DEO": "alcohol", "SAM": "alcohol", "BF.B": "alcohol",
    "TSN": "pork", "HRL": "pork", "LVS": "casinos", "WYNN": "casinos", "MGM": "casinos", "CZR": "casinos",
    "DKNG": "gambling", "PENN": "gambling", "RCI": "adult",
    # interest-based
    "COIN": "large interest income (USDC reserves)", "SOFI": "lender", "PYPL": "lending/credit",
    "UNH": "conventional insurance",
}
CONVENTIONAL_DEFENSE = {"PLTR", "AVAV", "KTOS"}

# ---------------------------------------------------------------- what it can trade
# Candidate universe by theme. The weekly halal screen removes anything that fails.
THEMES = {
    "oil_gas": ["XOM", "CVX", "COP", "OXY", "EOG", "DVN", "FANG", "SLB", "HAL", "BKR", "VLO", "PSX", "MPC", "APA", "CTRA"],
    "gold_miners": ["NEM", "AEM", "B", "KGC", "AU", "FNV", "WPM", "RGLD"],
    "defense_tech": sorted(CONVENTIONAL_DEFENSE),
    "tech_growth": ["AAPL", "MSFT", "NVDA", "AMD", "AVGO", "GOOGL", "META", "AMZN", "TSLA", "CRM", "ADBE",
                     "QCOM", "MU", "INTC", "AMAT", "LRCX", "KLAC", "NOW", "PANW", "CRWD", "SNOW", "SHOP", "ANET", "SMCI"],
    "healthcare": ["LLY", "JNJ", "ABBV", "MRK", "PFE", "TMO", "ISRG", "VRTX", "REGN", "ABT", "MDT"],
    "industrials": ["CAT", "DE", "GE", "ETN", "UNP", "FDX", "UPS"],
    "consumer": ["COST", "NKE", "HD", "LOW", "PG", "KO", "PEP", "SBUX", "TJX"],
    "crypto_miners": ["MARA", "RIOT", "CLSK"],
    "materials": ["FCX", "LIN", "NUE", "SCCO"],
    # Shariah ETFs (already screened by their index; no debt check needed)
    "shariah_etfs": ["SPUS", "HLAL", "UMMA", "SPTE", "SPWO"],
}
SHARIAH_ETFS = set(THEMES["shariah_etfs"])

# Major, established coins only. Lending/interest tokens are excluded on purpose.
CRYPTO_ALLOWED = ["BTC/USD", "ETH/USD", "SOL/USD", "LTC/USD", "LINK/USD", "AVAX/USD", "XRP/USD", "BCH/USD", "DOT/USD"]
CRYPTO_BLOCKED = {"AAVE/USD": "interest-based lending", "COMP/USD": "interest-based lending", "MKR/USD": "interest-based lending"}

# Meme coins and brand-new celebrity coins: WATCH MODE ONLY, never traded, not even on paper.
MEME_COINS = {"DOGE", "SHIB", "PEPE", "TRUMP", "MELANIA", "BONK", "WIF", "FLOKI", "BRETT", "POPCAT", "MOG", "TURBO", "PENGU"}

BENCHMARK = "SPY"   # comparison only, never traded

# ---------------------------------------------------------------- playbook (given to Gemini)
PLAYBOOK = """
- War / conflict escalation, attacks on oil supply, OPEC cuts -> oil & gas company stocks UP, defense tech UP, gold miners UP; broad tech often DOWN.
- Peace deal / ceasefire / de-escalation -> the reverse: those war plays DOWN (take profits).
- Fed / central-bank rate CUT or dovish surprise -> tech/growth UP, crypto UP, gold miners UP. Rate HIKE or hawkish surprise -> the reverse.
- Hot inflation (CPI/PCE above expectations) -> treat like hawkish. Cool inflation -> treat like dovish.
- Company earnings beat with raised guidance, or a major contract / partnership -> that stock UP (and named close suppliers UP).
- Earnings miss, guidance cut, scandal, lawsuit, fraud, recall, CEO exit, downgrade -> that stock DOWN.
- Tariffs / trade-war escalation -> affected importers and chip stocks DOWN; tariff relief -> UP.
- Major crypto news: spot ETF approvals / big inflows, large adoption (a country, a mega-corp treasury), clear friendly regulation -> BTC/ETH/SOL UP. Hacks, bans, hostile regulation, exchange collapse -> DOWN.
- Big oil supply increase / demand collapse -> oil & gas DOWN.
- Opinion pieces, recaps of old moves, price-target tweaks, rumours with no source, and general market commentary are NOT market-moving news.
- When unsure -> no trade. No trade is a valid decision.
"""

# ---------------------------------------------------------------- news sources
GOOGLE_NEWS_QUERIES = [
    "site:reuters.com when:1h", "site:apnews.com when:1h",
    "oil OR OPEC OR crude when:1h", "Federal Reserve OR rate cut OR rate hike when:1h",
    "war OR missile OR ceasefire OR attack when:1h", "earnings beat OR guidance when:1h",
    "bitcoin OR ethereum OR crypto ETF when:1h", "tariff OR sanctions when:1h",
]
CNBC_FEEDS = {
    "CNBC Top News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "CNBC World": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362",
    "CNBC Finance": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "CNBC Earnings": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135",
}
# X accounts read through Agent Reach (Omar's SECONDARY X account).
X_ACCOUNTS = ["realDonaldTrump", "WhiteHouse", "federalreserve", "SECGov", "elonmusk", "Reuters", "AP", "CNBC",
              "DeItaone", "FirstSquawk", "OPECSecretariat", "business"]
SUBREDDITS = ["wallstreetbets", "stocks", "CryptoCurrency", "worldnews"]
SOCIAL_PUBLISHERS = {"X", "Reddit"}

# ---------------------------------------------------------------- loop timing (laptop / server)
LOOP = _frozen({
    "market_minutes": 5,       # one cycle every 5 min while the US market is open
    "offhours_minutes": 15,    # crypto + watch mode the rest of the time
    "social_minutes": 15,      # X/Reddit through Agent Reach (secondary accounts)
    # Results are saved to GitHub only a few times a day (Toronto/New York time):
    "publish_times_et": ["09:50", "12:00", "14:00", "16:10", "20:00"],
})
