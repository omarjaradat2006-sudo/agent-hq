"""Offline tests: fake odds + fake Gemini. Run: python3 agents/fight/tests/test_fight.py"""
import datetime, json, os, shutil, sys, tempfile, unittest

TMP = tempfile.mkdtemp()
os.environ["FIGHT_DATA"] = TMP
os.environ["ODDS_API_KEY"] = "test"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C, oddsmath as M, odds as O, store as S, picks as P, grade as Gr, report as R  # noqa: E402

UTC = datetime.timezone.utc
iso = lambda h: (datetime.datetime.now(UTC) + datetime.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")


def bk(key, markets):
    return {"key": key, "title": key, "markets": [{"key": k, "outcomes": v} for k, v in markets.items()]}


def h2h(a, pa, b, pb):
    return [{"name": a, "price": pa}, {"name": b, "price": pb}]


def nba_events(start=5):
    g1 = {"id": "g1", "commence_time": iso(start), "home_team": "Boston Celtics", "away_team": "New York Knicks", "bookmakers": [
        bk("betmgm", {"h2h": h2h("Boston Celtics", 1.60, "New York Knicks", 2.45),
                      "spreads": [{"name": "Boston Celtics", "price": 1.91, "point": -4.5}, {"name": "New York Knicks", "price": 1.91, "point": 4.5}],
                      "totals": [{"name": "Over", "price": 1.91, "point": 225.5}, {"name": "Under", "price": 1.91, "point": 225.5}]}),
        bk("fanduel", {"h2h": h2h("Boston Celtics", 1.62, "New York Knicks", 2.40),
                       "spreads": [{"name": "Boston Celtics", "price": 1.95, "point": -4.5}, {"name": "New York Knicks", "price": 1.87, "point": 4.5}],
                       "totals": [{"name": "Over", "price": 1.90, "point": 225.5}, {"name": "Under", "price": 1.92, "point": 225.5}]}),
        bk("pinnacle", {"h2h": h2h("Boston Celtics", 1.63, "New York Knicks", 2.42),
                        "spreads": [{"name": "Boston Celtics", "price": 1.95, "point": -5.0}, {"name": "New York Knicks", "price": 1.90, "point": 5.0}],
                        "totals": [{"name": "Over", "price": 1.93, "point": 225.5}, {"name": "Under", "price": 1.93, "point": 225.5}]}),
        {"key": "bet365", "title": "Bet365", "markets": [{"key": "h2h", "outcomes": h2h("Boston Celtics", 1.30, "New York Knicks", 3.50)}]},
    ]}
    g2 = {"id": "g2", "commence_time": iso(start + 1), "home_team": "Los Angeles Lakers", "away_team": "Phoenix Suns", "bookmakers": [
        bk("betmgm", {"h2h": h2h("Los Angeles Lakers", 1.80, "Phoenix Suns", 2.05)}),
        bk("draftkings", {"h2h": h2h("Los Angeles Lakers", 1.83, "Phoenix Suns", 2.02)}),
        bk("pinnacle", {"h2h": h2h("Los Angeles Lakers", 1.85, "Phoenix Suns", 2.03)})]}
    g3 = {"id": "g3", "commence_time": iso(start + 1), "home_team": "Miami Heat", "away_team": "Chicago Bulls", "bookmakers": [
        bk("betmgm", {"h2h": h2h("Miami Heat", 1.70, "Chicago Bulls", 2.20)}),
        bk("pinnacle", {"h2h": h2h("Miami Heat", 1.72, "Chicago Bulls", 2.22)})]}
    return [g1, g2, g3]


class FakeGemini:
    def __init__(self, estimates):
        self.estimates = estimates

    def __call__(self, prompt, system=None, search=False, json_out=False, **kw):
        assert "lock" in system.lower() and "bet365" in system.lower()
        if "UFC event(s)" in prompt:
            return json.dumps({"events": [{"name": "UFC 999", "date": "2026-11-14", "bouts": [["Islam Makhachev", "Arman Tsarukyan"]]}]}), [("ufc.com", "https://ufc.com/x")]
        if "official result" in prompt:
            return json.dumps({"status": "finished", "winner": "Arman Tsarukyan", "method": "decision"}), [("ufc.com", "https://ufc.com/result")]
        if search:
            return "Research notes: Celtics missing two starters. Bet365 has Knicks at +250.", [("NBA injury report", "https://nba.com/injuries")]
        return json.dumps(self.estimates), []


EST = {"events": [
    {"e": "E1", "summary": "Celtics short-handed. This is a lock.", "keyFactors": ["Two Celtics starters out"],
     "estimates": [{"market": "h2h", "side": "New York Knicks", "point": None, "prob": 0.47, "reason": "Celtics without two starters; Knicks rested. Guaranteed winner."},
                   {"market": "totals", "side": "Over", "point": 225.5, "prob": 0.50, "reason": "no edge"}]},
    {"e": "E2", "summary": "Suns healthy, Lakers on a back-to-back.", "estimates": [{"market": "h2h", "side": "Phoenix Suns", "point": None, "prob": 0.55, "reason": "Lakers on the second night of a back-to-back."}]},
    {"e": "E3", "summary": "No clear angle.", "estimates": []}], "slateNotes": "Two spots with injury and rest edges."}


class T(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
        S.save(S.STATE, {"team": "fight", "agents": [], "log": []})

    def use(self, events, est):
        O.fetch_events = lambda sport, h=36: [{"id": e["id"], "home_team": e["home_team"], "away_team": e["away_team"], "commence_time": e["commence_time"]} for e in events]
        O.fetch_odds = lambda sport, h=36, min_left=None: events
        P.G.generate = Gr.G.generate = FakeGemini(est)

    def test_math(self):
        self.assertAlmostEqual(M.american_to_decimal(150), 2.5)
        self.assertAlmostEqual(M.american_to_decimal(-200), 1.5)
        self.assertEqual(M.fmt_american(2.5), "+150"); self.assertEqual(M.fmt_american(1.5), "-200")
        self.assertAlmostEqual(sum(M.no_vig([1.91, 1.91])), 1.0)
        self.assertAlmostEqual(M.ev(0.5, 2.0), 0.0)
        self.assertEqual(M.profit_per_100("win", 2.45), 145.0)

    def test_bet365_never_used(self):
        self.assertNotIn("bet365", O.active_books())
        lines = O.build_lines(nba_events()[0])
        knicks = [o for l in lines if l["market"] == "h2h" for o in l["outcomes"] if o["name"] == "New York Knicks"][0]
        self.assertEqual(knicks["best"], ["betmgm", 2.45])      # not Bet365's 3.50
        self.assertNotIn("bet365", knicks["prices"])
        spread = [l for l in lines if l["market"] == "spreads"][0]
        self.assertEqual(spread["point"], -4.5)                   # Pinnacle's -5 line isn't mixed in
        self.assertNotIn("pinnacle", spread["outcomes"][0]["prices"])

    def test_full_day(self):
        self.use(nba_events(), EST)
        P.run("nba")
        st, lg = S.state(), S.ledger()
        card = st["cards"]["nba"]
        self.assertIsNone(card["noBet"])
        self.assertEqual([p["selection"] for p in card["picks"]], ["New York Knicks to win", "Phoenix Suns to win"])
        k = card["picks"][0]
        self.assertEqual((k["type"], k["bookName"], k["american"]), ("underdog", "BetMGM", "+145"))
        self.assertEqual(k["impliedPct"], 40.8); self.assertTrue(k["value"]); self.assertGreater(k["evPer100"], 2)
        self.assertEqual(len(card["parlays"]), 1)
        self.assertEqual(card["parlays"][0]["bookName"], "BetMGM")
        self.assertEqual(len(card["underdogs"]), 3)
        dump = json.dumps(st) + json.dumps(lg)
        for p in card["picks"]:
            for word in ("lock", "Guaranteed"):
                self.assertNotIn(word, p["reasoning"] + p["summary"])
        self.assertNotIn("Bet365 has", dump)
        self.assertNotIn("bet365", json.dumps(lg).lower())
        self.assertIn("Bet365", " ".join(st["rules"]))           # only in our own rule text
        # results: Knicks win 110-105 -> Knicks single won, Suns lost, parlay lost
        for p in lg["picks"]:
            p["commence"] = iso(-10)
            for l in p.get("legs", []):
                l["commence"] = iso(-10)
        S.save(S.LEDGER, lg)
        O.fetch_scores = lambda sport, d=3: [
            {"id": "g1", "completed": True, "home_team": "Boston Celtics", "away_team": "New York Knicks", "scores": [{"name": "Boston Celtics", "score": "105"}, {"name": "New York Knicks", "score": "110"}]},
            {"id": "g2", "completed": True, "home_team": "Los Angeles Lakers", "away_team": "Phoenix Suns", "scores": [{"name": "Los Angeles Lakers", "score": "120"}, {"name": "Phoenix Suns", "score": "101"}]}]
        Gr.run()
        rec = S.state()["record"]
        self.assertEqual((rec["all"]["won"], rec["all"]["lost"]), (1, 2))
        self.assertEqual(rec["all"]["profit"], -55.0)
        self.assertEqual(rec["all"]["profitPer100"], -18.33)
        self.assertEqual(rec["all"]["winRate"], 33.3)
        self.assertEqual(rec["byType"]["underdog"]["profit"], 45.0)
        self.assertEqual(rec["byType"]["parlay"]["lost"], 1)

    def test_no_bet(self):
        self.use(nba_events(), {"events": [{"e": "E1", "estimates": []}], "slateNotes": ""})
        P.run("nba")
        card = S.state()["cards"]["nba"]
        self.assertTrue(card["noBet"].startswith("No bet"))
        self.assertEqual(card["picks"], []); self.assertEqual(card["parlays"], [])
        self.assertEqual(S.state()["record"]["noBetDays"], 1)

    def test_ufc_filter_and_search_grading(self):
        ev = [{"id": "u1", "commence_time": iso(20), "home_team": "Islam Makhachev", "away_team": "Arman Tsarukyan",
               "bookmakers": [bk("fanduel", {"h2h": h2h("Islam Makhachev", 1.50, "Arman Tsarukyan", 2.70)}), bk("pinnacle", {"h2h": h2h("Islam Makhachev", 1.48, "Arman Tsarukyan", 2.75)})]},
              {"id": "p1", "commence_time": iso(20), "home_team": "PFL Guy", "away_team": "Other PFL Guy",
               "bookmakers": [bk("fanduel", {"h2h": h2h("PFL Guy", 1.5, "Other PFL Guy", 2.7)})]}]
        self.use(ev, {"events": [{"e": "E1", "summary": "Close fight", "estimates": [{"market": "h2h", "side": "Arman Tsarukyan", "prob": 0.45, "reason": "wrestling edge"}]}]})
        P.run("ufc")
        card = S.state()["cards"]["ufc"]
        self.assertEqual(card["games"], 1)                       # PFL bout ignored
        self.assertEqual(card["picks"][0]["side"], "Arman Tsarukyan")
        lg = S.ledger(); lg["picks"][0]["commence"] = iso(-10); S.save(S.LEDGER, lg)
        O.fetch_scores = lambda sport, d=3: []
        Gr.run()
        p = S.ledger()["picks"][0]
        self.assertEqual((p["status"], p["profit"], p["gradedBy"]), ("won", 170.0, "search with source"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
