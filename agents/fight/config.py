"""Fight & Court Intelligence settings. Research and recommendations only:
this code never places bets, never logs into a sportsbook and has no sportsbook credentials.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.environ.get("FIGHT_DATA") or os.path.join(ROOT, "data", "fight")

SPORTS = {
    "nba": {"key": "basketball_nba", "name": "NBA", "markets": ["h2h", "spreads", "totals"]},
    "ufc": {"key": "mma_mixed_martial_arts", "name": "UFC", "markets": ["h2h"]},
}

# Bet365 is excluded everywhere: never requested, dropped if it ever appears, never mentioned in text.
BANNED = re.compile(r"bet\s*-?\s*365", re.I)

# Sportsbooks licensed in Ontario (iGaming Ontario / AGCO) that The Odds API carries.
# key = The Odds API bookmaker key. "feed" = which market's prices the API returns for that brand.
# Ontario apps are ring-fenced, so the Ontario price can differ slightly: always check the app.
# "on": True = used. The weekly licence check (books.py) can switch a brand on/off, but only
# with an igamingontario.ca or agco.ca source.
BOOKS = {
    "betmgm":        {"name": "BetMGM",             "feed": "US", "on": True},
    "fanduel":       {"name": "FanDuel",            "feed": "US", "on": True},
    "draftkings":    {"name": "DraftKings",         "feed": "US", "on": True},
    "williamhill_us": {"name": "Caesars Sportsbook", "feed": "US", "on": True},
    "betrivers":     {"name": "BetRivers",          "feed": "US", "on": True},
    "betway":        {"name": "Betway",             "feed": "UK", "on": True},
    "sport888":      {"name": "888sport",           "feed": "UK", "on": True},
    "leovegas":      {"name": "LeoVegas",           "feed": "UK", "on": True},
    "pinnacle":      {"name": "Pinnacle",           "feed": "Global", "on": True},
    # Candidates: only switched on after the licence check finds them on the iGO/AGCO list.
    "unibet_uk":     {"name": "Unibet",             "feed": "UK", "on": False},
    "espnbet":       {"name": "theScore Bet (ESPN BET feed)", "feed": "US", "on": False},
    "fanatics":      {"name": "Fanatics Sportsbook", "feed": "US", "on": False},
    "betvictor":     {"name": "BetVictor",          "feed": "UK", "on": False},
}
for _k, _b in BOOKS.items():
    assert not BANNED.search(_k) and not BANNED.search(_b["name"]), "Bet365 must never be in the book list"

# Omar's own books: best price, value, parlays and "where to find it" use ONLY these.
# The other Ontario books above are still read (same credit cost) to work out the fair price.
MY_BOOKS = ["fanduel", "draftkings", "betmgm", "betrivers"]

# The Odds API: every 10 named bookmakers cost the same as 1 region. Free plan = 500 credits/month.
ODDS_BASE = "https://api.the-odds-api.com/v4"
CREDIT_RESERVE = 40          # never spend below this (keeps grading alive at month end)
CLOSE_MIN_CREDITS = 120      # skip the optional closing-line snapshot when credits are lower than this

# Value rules (applied in code, not by the model)
MODEL_WEIGHT = 0.5           # blended probability = market fair + 0.5 * (research estimate - market fair)
MIN_EDGE = 0.025             # blended prob must beat the no-vig market prob by 2.5 points
MIN_EV = 0.02                # and the best price must return at least +2% expected value
MAX_SINGLES = 4              # per sport per day; fewer (or none) is fine
MAX_PARLAYS = 2
PARLAY_LEGS = (2, 3)
MAX_ABS_ODDS = 1000          # ignore prices longer than +1000 / shorter than -1000 (thin, unreliable)

# Words the output must never use about a pick
FORBIDDEN = re.compile(r"\b(locks?|lock of the|guaranteed?|guarantee|sure thing|can'?t lose|free money|bank on it|easy money|max bet|bet the house)\b", re.I)
