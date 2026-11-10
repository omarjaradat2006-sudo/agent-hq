"""Legs written the way the FanDuel / DraftKings apps word them, plus where to find them in the app."""
import oddsmath as M

STAT = {"player_points": "Points", "player_rebounds": "Rebounds", "player_assists": "Assists", "player_threes": "Made Threes"}


def base(mk):
    return mk.replace("_alternate", "")
TAB = {
    "fanduel": {"h2h": "Popular / Game Lines", "spreads": "Popular / Game Lines", "totals": "Popular / Game Lines",
                "team_totals": "Team Props", "player_points": "Player Points", "player_rebounds": "Player Rebounds",
                "player_assists": "Player Assists", "player_threes": "Player Threes"},
    "draftkings": {"h2h": "Game Lines", "spreads": "Game Lines", "totals": "Game Lines", "team_totals": "Team Props",
                   "player_points": "Player Points", "player_rebounds": "Player Rebounds", "player_assists": "Player Assists",
                   "player_threes": "Player Threes"},
}
UFC_TAB = {"h2h": "Fight Lines / Moneyline", "totals": "Total Rounds"}


def short(team):
    """'Los Angeles Lakers' -> 'Lakers', 'Portland Trail Blazers' -> 'Trail Blazers'."""
    if not team:
        return ""
    if team.endswith("Trail Blazers"):
        return "Trail Blazers"
    return team.split()[-1]


def game(c):
    if c["sport"] == "ufc":
        return f"{c['away']} vs {c['home']}"
    return f"{short(c['away'])} vs {short(c['home'])}"


def num(p):
    return f"{p:g}"


def leg_text(c, book, with_game=True):
    g, mk, side, pt = game(c), c["market"], c["side"], c.get("point")
    if not with_game:
        return leg_text(c, book).split(": ", 1)[1]
    if mk == "h2h":
        return f"{g}: {side} to Win" if c["sport"] == "ufc" else f"{g}: {short(side)} Moneyline"
    if mk == "spreads":
        return f"{g}: {short(side)} {pt:+g}"
    if mk == "totals":
        return f"{g}: {side} {num(pt)} Total {'Rounds' if c['sport'] == 'ufc' else 'Points'}"
    if mk == "team_totals":
        return f"{g}: {short(c['team'])} Team Total {side} {num(pt)}"
    stat = STAT.get(base(mk), mk)
    if base(mk) == "player_threes" and book == "draftkings":
        stat = "Threes"
    if mk.endswith("_alternate") and side == "Over":   # milestone: Over 19.5 = "20+ Points"
        return f"{g}: {c['player']} {int(pt + 0.5)}+ {stat}"
    return f"{g}: {c['player']} {side} {num(pt)} {stat}"


def where(c, book):
    if c["sport"] == "ufc":
        return f"{c['away']} vs {c['home']} > {UFC_TAB.get(c['market'], 'Fight Lines')}"
    tab = TAB[book].get(base(c["market"]), "Game Lines")
    if c["market"].endswith("_alternate"):
        tab += " (milestones, e.g. 20+)"
    return f"{short(c['away'])} @ {short(c['home'])} > {tab}"


def american(d):
    return M.fmt_american(d)
