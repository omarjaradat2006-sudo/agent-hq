"""Offline tests with fake odds, fake Gemini and fake box scores. Run: python3 agents/fight/tests/test_fight.py"""
import datetime, json, os, re, shutil, sys, tempfile, unittest

TMP = tempfile.mkdtemp()
os.environ["FIGHT_DATA"] = TMP
os.environ["ODDS_API_KEY"] = "test"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C, oddsmath as M, odds as O, store as S, analyst as A, cards as K, grade as Gr, builder as B, wording as W  # noqa

UTC = datetime.timezone.utc
iso = lambda h: (datetime.datetime.now(UTC) + datetime.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
TEAMS = [("New York Knicks", "Boston Celtics"), ("Phoenix Suns", "Los Angeles Lakers"), ("Chicago Bulls", "Miami Heat"),
         ("Utah Jazz", "Denver Nuggets"), ("Portland Trail Blazers", "Golden State Warriors"), ("Orlando Magic", "Atlanta Hawks")]


def mk(key, outs):
    return {"key": key, "outcomes": outs}


def book(key, markets, title=None):
    return {"key": key, "title": title or key, "markets": markets}


def nba_game(i, away, home, start):
    fav = 1.45 + 0.05 * i
    dog = round(1 / (1.05 - 1 / fav), 2)
    main = lambda adj: [mk("h2h", [{"name": home, "price": fav + adj}, {"name": away, "price": dog + adj}]),
                        mk("spreads", [{"name": home, "price": 1.91, "point": -5.5}, {"name": away, "price": 1.91, "point": 5.5}]),
                        mk("totals", [{"name": "Over", "price": 1.91, "point": 224.5}, {"name": "Under", "price": 1.91, "point": 224.5}])]
    return {"id": f"g{i}", "commence_time": iso(start + i * 0.5), "home_team": home, "away_team": away,
            "bookmakers": [book("fanduel", main(0)), book("draftkings", main(0.02)),
                           book("betmgm", main(0.5)), book("bet365", main(1.0), "Bet365")]}


def props(i, away, home):
    p1, p2 = f"Star{i} Guy", f"Big{i} Man"
    m = [mk("player_points", [{"name": "Over", "description": p1, "price": 1.87, "point": 24.5}, {"name": "Under", "description": p1, "price": 1.95, "point": 24.5}]),
         mk("player_rebounds", [{"name": "Over", "description": p2, "price": 1.90, "point": 10.5}, {"name": "Under", "description": p2, "price": 1.90, "point": 10.5}]),
         mk("player_threes", [{"name": "Over", "description": p1, "price": 2.10, "point": 2.5}, {"name": "Under", "description": p1, "price": 1.72, "point": 2.5}])]
    return {"id": f"g{i}", "commence_time": iso(5 + i * 0.5), "home_team": home, "away_team": away,
            "bookmakers": [book("fanduel", m), book("draftkings", m[:2]), book("bet365", m, "bet365")]}


class FakeGemini:
    def __init__(self, ufc_event=True):
        self.ufc_event = ufc_event

    def __call__(self, prompt, system=None, search=False, json_out=False, **kw):
        assert "lock" in system.lower() and "bet365" in system.lower()
        src = [("source", "https://example.com/s")]
        if "Is there a UFC event" in prompt:
            ev = {"event": {"name": "UFC 999", "date": "2026-11-14", "bouts": [["Islam Makhachev", "Arman Tsarukyan"], ["Sean Strickland", "Dricus Du Plessis"], ["Max Holloway", "Ilia Topuria"]]}} if self.ufc_event else {"event": None}
            return json.dumps(ev), src
        if "official result of the UFC fight" in prompt:
            return json.dumps({"status": "finished", "winner": "Arman Tsarukyan", "method": "KO/TKO", "round": 2, "time": "3:10", "rounds": 5}), src
        if "GENUINE path" in prompt:
            names = re.findall(r"^- (.+?) \(vs", prompt, re.M)
            return json.dumps({"underdogs": [{"fighter": n, "genuine": i == 0, "prob": 0.42, "path": "KO/TKO", "oneLine": "Heavy hands and the favourite gets hit a lot. A lock!",
                                              "breakdown": {"style": "orthodox striker", "weighIn": "made weight easily"}} for i, n in enumerate(names)]}), []
        if "ONE short plain sentence" in prompt:
            n = len(re.findall(r"^P\d+:", prompt, re.M))
            return json.dumps({"why": {f"P{i}": "Built on injury news and matchups; this is guaranteed." for i in range(n)}}), []
        if json_out:  # estimates: favour the first side of every line by 8 points
            picks = []
            for lid, side, fair in re.findall(r"^(L\d+) \| [^|]+ \| [^|]+ \| ([^\[]+?) \[[^\]]*\] fair (\d+)%", prompt, re.M):
                picks.append({"id": lid, "side": side.strip(), "prob": min(0.9, int(fair) / 100 + 0.08), "why": f"Specific reason for {side.strip()}."})
            return json.dumps({"picks": picks}), []
        if search:
            return "Notes: two starters out. Bet365 has a better price.\nPROP_GAMES: Knicks @ Celtics; Suns @ Lakers", src
        return "{}", []


class T(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(TMP, ignore_errors=True); os.makedirs(TMP)
        S.save(S.STATE, {"team": "fight", "agents": [], "log": []})
        A.G.generate = FakeGemini()
        games = [nba_game(i, a, h, 5) for i, (a, h) in enumerate(TEAMS)]
        O.fetch_events = lambda key, h=36: [] if key == C.UFC_KEY and not getattr(self, "ufc", True) else (games if key == C.NBA_KEY else self.ufc_events())
        O.fetch_odds = lambda key, markets, h=36: games if key == C.NBA_KEY else self.ufc_events()
        O.fetch_event_odds = lambda key, eid, m: props(int(eid[1:]), *TEAMS[int(eid[1:])])
        O.daily_prop_budget = lambda *a, **k: 2

    def ufc_events(self):
        f = lambda i, a, b, pa, pb: {"id": f"u{i}", "commence_time": iso(26 + i), "home_team": a, "away_team": b, "bookmakers": [
            book("fanduel", [mk("h2h", [{"name": a, "price": pa}, {"name": b, "price": pb}]), mk("totals", [{"name": "Over", "price": 1.8, "point": 2.5}, {"name": "Under", "price": 2.0, "point": 2.5}])]),
            book("draftkings", [mk("h2h", [{"name": a, "price": pa + 0.03}, {"name": b, "price": pb - 0.05}])]),
            book("bet365", [mk("h2h", [{"name": a, "price": 3}, {"name": b, "price": 9}])], "Bet365")]}
        return [f(0, "Islam Makhachev", "Arman Tsarukyan", 1.40, 3.10), f(1, "Dricus Du Plessis", "Sean Strickland", 1.65, 2.30),
                f(2, "Ilia Topuria", "Max Holloway", 1.30, 3.70), f(3, "PFL Guy", "Other Guy", 1.5, 2.6)]

    def test_math_and_wording(self):
        self.assertEqual(M.fmt_american(2.5), "+150"); self.assertEqual(M.fmt_american(1.5), "-200")
        c = {"sport": "nba", "home": "Boston Celtics", "away": "Los Angeles Lakers", "market": "player_points", "side": "Over", "point": 24.5, "player": "LeBron James"}
        self.assertEqual(W.leg_text(c, "fanduel"), "Lakers vs Celtics: LeBron James Over 24.5 Points")
        self.assertEqual(W.leg_text({**c, "market": "player_threes"}, "draftkings"), "Lakers vs Celtics: LeBron James Over 24.5 Threes")
        self.assertEqual(W.leg_text({**c, "market": "spreads", "side": "Boston Celtics", "point": -5.5}, "fanduel"), "Lakers vs Celtics: Celtics -5.5")
        self.assertEqual(W.short("Portland Trail Blazers"), "Trail Blazers")

    def test_only_fanduel_draftkings(self):
        cs = O.candidates(nba_game(0, *TEAMS[0], 5), "nba")
        self.assertTrue(all(set(c["prices"]) <= {"fanduel", "draftkings"} for c in cs))
        self.assertEqual(len(cs), 6)

    def test_nba_three_placeable_parlays(self):
        K.run_nba()
        st, lg = S.state(), S.ledger()
        ps = st["cards"]["nba"]["parlays"]
        self.assertEqual([p["tier"] for p in ps], ["+100", "+500", "+1000"])
        for p, (_, lo, hi) in zip(ps, C.TARGETS):
            self.assertIn(p["bookName"], ("FanDuel", "DraftKings"))
            self.assertEqual(len({l["eventId"] for l in p["legs"]}), len(p["legs"]))       # one leg per game
            self.assertGreaterEqual(len(p["legs"]), 2)
            self.assertAlmostEqual(p["dec"], M.parlay_decimal([l["dec"] for l in p["legs"]]), places=2)
            self.assertTrue(lo * 0.85 <= p["dec"] <= hi * 1.25)
            self.assertIn(p["strength"], ("Strong", "Medium", "Long shot"))
            self.assertNotIn("guaranteed", p["why"].lower())
        dump = json.dumps(st) + json.dumps(lg)
        for bad in ("bet365", "betmgm", "BetMGM"):
            self.assertNotIn(bad, json.dumps(lg).replace("[excluded book]", ""))
        self.assertNotIn("Bet365 has", dump)
        self.assertTrue(any(":" in l["text"] and ("Points" in l["text"] or "Moneyline" in l["text"] or "Total" in l["text"] or "Rebounds" in l["text"] or "Threes" in l["text"] or re.search(r"[+-]\d", l["text"])) for p in ps for l in p["legs"]))
        self.assertEqual(len(lg["bets"]), 3)

    def test_ufc_no_event(self):
        A.G.generate = FakeGemini(ufc_event=False)
        K.run_ufc()
        c = S.state()["cards"]["ufc"]
        self.assertEqual(c["message"], "No UFC event this week")
        self.assertEqual((c["parlays"], c["underdogs"]), ([], []))

    def test_ufc_card_dogs_and_grading(self):
        K.run_ufc()
        c = S.state()["cards"]["ufc"]
        self.assertEqual(c["fights"], 3)                                         # PFL bout ignored
        self.assertEqual(len(c["underdogs"]), 1)                                 # only the genuine one
        d = c["underdogs"][0]
        self.assertEqual((d["risk"], d["path"], d["bookName"]), ("High risk", "KO/TKO", "FanDuel"))
        self.assertIn("to Win", d["betText"]); self.assertNotIn("lock", d["why"].lower())
        self.assertTrue(d["pathNote"])
        self.assertGreaterEqual(len(c["parlays"]), 1)
        lg = S.ledger()
        for b in lg["bets"]:
            for l in b["legs"]:
                l["commence"] = iso(-10)
        S.save(S.LEDGER, lg)
        Gr.run()
        lg = S.ledger()
        dog = next(b for b in lg["bets"] if b["kind"] == "ufc_dog")
        self.assertEqual(dog["status"], "won" if dog["legs"][0]["side"] == "Arman Tsarukyan" else "lost")
        rec = S.state()["record"]
        self.assertTrue(rec["lines"][2].startswith("UFC underdog picks: "))

    def test_nba_grading_props_and_void(self):
        K.run_nba()
        lg = S.ledger()
        for b in lg["bets"]:
            for l in b["legs"]:
                l["commence"] = iso(-10)
        S.save(S.LEDGER, lg)
        Gr.espn_game = lambda leg: {"id": leg["eventId"], "completed": True, "postponed": False, "home": 110, "away": 100}
        Gr.espn_box = lambda gid: {"Star0 Guy": {"played": True, "PTS": 30, "REB": 5, "AST": 4, "3PT": 4}, "Big0 Man": {"played": False},
                                   "Star1 Guy": {"played": True, "PTS": 10, "REB": 2, "AST": 1, "3PT": 0}, "Big1 Man": {"played": True, "PTS": 8, "REB": 14, "AST": 1, "3PT": 0}}
        Gr.run()
        lg = S.ledger()
        self.assertTrue(all(b["status"] in ("won", "lost", "push") for b in lg["bets"]))
        legs = [l for b in lg["bets"] for l in b["legs"]]
        for l in legs:
            if l["market"] == "h2h":
                self.assertEqual(l["status"], "won" if l["side"] == l["home"] else "lost")
            if l.get("player") == "Big0 Man":
                self.assertEqual(l["status"], "void")
        lines = S.state()["record"]["lines"]
        self.assertTrue(re.match(r"NBA parlays: \d+ won, \d+ lost.*(up|down) \$\d+\.\d\d per \$100", lines[0]), lines[0])

    def test_sanitize(self):
        self.assertEqual(S.sanitize("This is basically guaranteed, a lock."), "This is likely, a lean.")


if __name__ == "__main__":
    unittest.main(verbosity=1)
