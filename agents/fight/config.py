"""Fight & Court Intelligence settings. Research and recommendations only:
this code never places bets, never logs into a sportsbook and holds no sportsbook credentials."""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.environ.get("FIGHT_DATA") or os.path.join(ROOT, "data", "fight")

# Only Omar's two apps. No other book is requested, read, compared or shown. Bet365 is excluded everywhere.
BOOKS = {"fanduel": "FanDuel", "draftkings": "DraftKings"}
BANNED = re.compile(r"bet\s*-?\s*365", re.I)
assert not any(BANNED.search(k) or BANNED.search(v) for k, v in BOOKS.items())

NBA_KEY, UFC_KEY = "basketball_nba", "mma_mixed_martial_arts"
NBA_MAIN = ["h2h", "spreads", "totals"]                  # one call for all games
NBA_PROPS = ["player_points", "player_rebounds", "player_assists", "player_threes", "player_points_alternate"]  # per game; alternate = "20+ Points" milestones
UFC_MAIN = ["h2h", "totals"]                              # The Odds API: fight winner + total rounds (some books). No method/strikes/takedowns.

# Odds API credits. 2 bookmakers = 1 region, so a call costs [markets returned] credits.
ODDS_BASE = "https://api.the-odds-api.com/v4"
PLAN_CREDITS = int(os.environ.get("ODDS_PLAN_CREDITS", "500"))   # set to 20000 after upgrading
CREDIT_RESERVE = 25

# Slip targets (decimal odds windows). NBA slips are SAME-GAME parlays: all legs from one game, on one app.
# The app prices an SGP itself (correlation adjustment), so our total is an estimate = legs multiplied.
TARGETS = [("+100", 1.85, 2.45), ("+500", 5.2, 7.2), ("+1000", 9.5, 13.5)]
MAX_LEGS = 6          # multi-fight UFC parlays
SGP_LEGS = (2, 5)      # NBA same-game parlays
MODEL_WEIGHT = 0.5      # our chance = market fair chance moved halfway toward the research estimate
MAX_ABS_ODDS = 800      # ignore legs longer than +800 / shorter than -800 (no -2000 filler legs)
DOG_MIN_CHANCE = 0.22   # an underdog needs at least this chance (after blending) to be listed

FORBIDDEN = re.compile(r"\b(basically guaranteed|locks?|lock of the \w+|guaranteed?|guarantee|sure thing|can'?t lose|free money|easy money|max bet|bet the house|safest)\b", re.I)
