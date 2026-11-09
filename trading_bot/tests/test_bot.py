"""Offline tests: fake Alpaca + fake Gemini/TradingAgents. Run: python -m pytest trading_bot/tests -q"""
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ALPACA_API_KEY", "x"); os.environ.setdefault("ALPACA_SECRET_KEY", "y")

from trading_bot import util, config as C


@pytest.fixture(autouse=True)
def tmpdirs(tmp_path, monkeypatch):
    import trading_bot.bot as B, trading_bot.halal as H, trading_bot.report as R
    monkeypatch.setattr(util, "DATA", tmp_path / "data"); monkeypatch.setattr(util, "LOCAL", tmp_path / "local")
    monkeypatch.setattr(B, "LEDGER", tmp_path / "data" / "ledger.json"); monkeypatch.setattr(B, "STATE", tmp_path / "local" / "state.json")
    monkeypatch.setattr(B, "DATA", tmp_path / "data"); monkeypatch.setattr(R, "DATA", tmp_path / "data")
    monkeypatch.setattr(H, "UNIVERSE_FILE", tmp_path / "data" / "universe.json")
    yield tmp_path


def T(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


NOW = datetime.now(timezone.utc)


def bars_spike(price=100.0, days=10, tf_min=5, spike_mult=4, move=0.01, news_at=None):
    """Flat price/volume history, then a volume spike and a +move after news_at."""
    out, t = [], NOW - timedelta(days=days + 1)
    while t <= NOW:
        after = news_at and t >= news_at
        p = price * (1 + move) if after else price
        v = 1000 * (spike_mult if after else 1)
        out.append({"t": T(t), "o": p, "h": p * 1.001, "l": p * 0.999, "c": p, "v": v})
        t += timedelta(minutes=tf_min)
    return out


class FakeAlpaca:
    def __init__(self):
        self.equity, self.last_equity, self.cash = 100000.0, 100000.0, 100000.0
        self.pos, self.orders_, self.placed = [], {}, []
        self.is_open = True
        self.news_at = NOW - timedelta(minutes=40)

    def account(self):
        return {"equity": str(self.equity), "last_equity": str(self.last_equity), "cash": str(self.cash)}

    def clock(self):
        return {"is_open": self.is_open, "next_close": T(NOW + timedelta(hours=3))}

    def positions(self): return list(self.pos)
    def orders(self, status="open", symbols=None, limit=200): return []
    def order(self, oid): return self.orders_[oid]
    def cancel(self, oid): pass
    def asset(self, s): return {"tradable": True, "status": "active"}
    def calendar(self, a, b): return []
    def latest_price(self, s): return 101.0 if s != "SPY" else 500.0

    def stock_bars(self, syms, tf, start, end=None, limit=None):
        return {s: bars_spike(news_at=self.news_at) for s in syms}

    def crypto_bars(self, syms, tf, start, end=None, limit=None):
        return {s: bars_spike(days=7, tf_min=15, news_at=self.news_at) for s in syms}

    def buy_stock_bracket(self, sym, qty, stop, target, cid):
        oid = f"o{len(self.placed)}"
        self.placed.append(("bracket", sym, qty, stop, target))
        self.orders_[oid] = {"id": oid, "status": "filled", "filled_avg_price": "101", "filled_qty": str(qty),
                             "legs": [{"type": "limit", "limit_price": str(target), "status": "new"},
                                      {"type": "stop", "stop_price": str(stop), "status": "new"}]}
        return {"id": oid}

    def buy_crypto(self, sym, notional, cid):
        oid = f"o{len(self.placed)}"; self.placed.append(("crypto", sym, notional))
        self.orders_[oid] = {"id": oid, "status": "filled", "filled_avg_price": "101", "filled_qty": "49"}
        return {"id": oid}

    def crypto_stop(self, sym, qty, stop, cid):
        self.placed.append(("stop", sym, qty, stop)); self.orders_["s1"] = {"id": "s1", "status": "new", "type": "stop_limit"}
        return {"id": "s1"}

    def sell_all(self, sym):
        self.placed.append(("sell", sym)); self.pos = [p for p in self.pos if p["symbol"] != sym.replace("/", "")]

    def cancel_all_and_flatten(self): self.placed.append(("flatten",)); self.pos = []


UNIVERSE = {"builtAt": T(NOW), "stocks": {"XOM": {"theme": "oil_gas"}, "NVDA": {"theme": "tech_growth"}},
            "crypto": {"BTC/USD": {"theme": "crypto"}}}


def news_items():
    from trading_bot.news import item
    t = T(NOW - timedelta(minutes=40))
    return [item("Reuters", "news", "Drone strike hits major Saudi oil facility", "", "https://r/1", t),
            item("CNBC", "news", "Oil jumps after attack on Saudi facility", "", "https://c/1", t),
            item("X", "social", "@DeItaone: SAUDI OIL FACILITY HIT", "", "https://x/1", t)]


def wire(monkeypatch, fake, assets, ta_rating="Buy", calls=None):
    import trading_bot.bot as B, trading_bot.halal as H, trading_bot.news as N, trading_bot.triage as TR, trading_bot.deep as D
    monkeypatch.setattr("trading_bot.alpaca.Alpaca", lambda *a, **k: fake)
    monkeypatch.setattr(H, "build_universe", lambda a, force=False: UNIVERSE)
    items = news_items()
    monkeypatch.setattr(N, "collect", lambda a, s, include_social: items)
    reply = {"events": [{"key": "saudi-oil-attack", "is_market_news": True, "category": "oil_supply",
                         "summary": "Drone strike on Saudi oil facility", "item_ids": [i["id"] for i in items],
                         "assets": assets, "meme_coins": []}]}
    monkeypatch.setattr(TR.gemini, "generate", lambda *a, **k: (json.dumps(reply), []))
    def fake_deep(sym, trade_date=None, context=""):
        if calls is not None: calls.append(sym)
        return {"approved": ta_rating in C.DEEP["approve_ratings"], "rating": ta_rating, "summary": "ok", "error": None}
    monkeypatch.setattr(D, "run", fake_deep)
    monkeypatch.setattr("trading_bot.risk.stock_entry_window_open", lambda clock, now=None: (True, ""))
    return B


def test_full_cycle_buys_with_bracket(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "supply shock"}])
    b = B.Bot(); b.cycle()
    kind, sym, qty, stop, target = fake.placed[0]
    assert (kind, sym) == ("bracket", "XOM")
    assert qty == int(5000 // 101)                      # 5% of 100k, whole shares
    assert stop == pytest.approx(101 * 0.97, abs=0.01) and target == pytest.approx(101 * 1.06, abs=0.01)
    t = b.ledger["trades"][0]
    assert t["news"]["sources"] and t["reason"]["tradingAgents"] == "Buy"
    assert "Reuters" in t["reason"]["publishers"]


def test_halal_universe_blocks_unscreened_symbol(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "LMT", "direction": "up", "confidence": 0.9, "why": "defense"}])
    b = B.Bot(); b.cycle()
    assert not fake.placed                     # LMT not in the halal universe -> triage drops it


def test_tradingagents_rejection_means_no_trade(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}], ta_rating="Hold")
    b = B.Bot(); b.cycle()
    assert not fake.placed
    assert b.ledger["decisions"][0]["outcome"] == "rejected"


def test_low_confidence_and_single_source(monkeypatch):
    fake = FakeAlpaca()
    calls = []
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.4, "why": "x"}], calls=calls)
    B.Bot().cycle()
    assert not fake.placed and not calls


def test_already_moved_too_far(monkeypatch):
    fake = FakeAlpaca()
    calls = []
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}], calls=calls)
    orig = fake.stock_bars
    fake.stock_bars = lambda syms, *a, **k: {s: bars_spike(move=0.05, news_at=fake.news_at) for s in syms}
    b = B.Bot(); b.cycle()
    assert not fake.placed and not calls
    assert "too late" in b.ledger["decisions"][0]["why"]


def test_no_volume_spike(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    fake.stock_bars = lambda syms, *a, **k: {s: bars_spike(spike_mult=1, news_at=fake.news_at) for s in syms}
    B.Bot().cycle()
    assert not fake.placed


def test_max_positions(monkeypatch):
    fake = FakeAlpaca()
    fake.pos = [{"symbol": s, "qty": "1"} for s in ["AAPL", "MSFT", "AMD", "LLY", "CAT"]]
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    b = B.Bot(); b.cycle()
    assert not fake.placed and "max 5" in b.ledger["decisions"][0]["why"]


def test_daily_halt(monkeypatch):
    fake = FakeAlpaca(); fake.equity = 96900.0
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    b = B.Bot(); b.ledger["startEquity"] = 100000.0; b.cycle()
    assert not fake.placed


def test_kill_switch(monkeypatch):
    fake = FakeAlpaca(); fake.equity = 89000.0; fake.last_equity = 89500.0
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    monkeypatch.setattr(B, "alert_popup", lambda m: None)
    b = B.Bot(); b.ledger["startEquity"] = 100000.0; b.cycle()
    assert ("flatten",) in fake.placed and b.ledger["killed"]
    assert not [p for p in fake.placed if p[0] == "bracket"]


def test_crypto_buy_then_server_side_stop(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "BTC/USD", "direction": "up", "confidence": 0.8, "why": "ETF inflows"}])
    b = B.Bot(); b.cycle()
    assert fake.placed[0][:2] == ("crypto", "BTC/USD") and fake.placed[0][2] == pytest.approx(5000)
    fake.pos = [{"symbol": "BTCUSD", "qty": "49", "qty_available": "49", "current_price": "101", "unrealized_plpc": "0"}]
    b2 = B.Bot(); b2.reconcile(fake.positions())
    stop = [p for p in fake.placed if p[0] == "stop"][0]
    assert stop[3] == pytest.approx(101 * 0.97, abs=0.01)


def test_stock_stop_hit_is_recorded(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    b = B.Bot(); b.cycle()
    fake.pos = []                                            # bracket stop fired on Alpaca's side
    o = fake.orders_["o0"]; o["legs"][1].update({"status": "filled", "filled_avg_price": "97.97"})
    b2 = B.Bot(); b2.reconcile([])
    t = b2.ledger["trades"][0]
    assert t["status"] == "closed" and "stop" in t["exitReason"] and t["pnl"] < 0


def test_bad_news_sells_holding(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    b = B.Bot(); b.cycle()
    b.ledger["trades"][0]["openedAt"] = T(NOW - timedelta(hours=2))
    b.s["events"]["xom-lawsuit"] = {"key": "xom-lawsuit", "summary": "XOM hit with huge lawsuit", "category": "company_bad_news",
                                     "firstSeen": T(NOW), "items": [{"id": "1", "publisher": "Reuters", "kind": "news", "title": "", "url": ""}],
                                     "assets": {"XOM": {"direction": "down", "confidence": 0.8, "why": ""}}, "memes": []}
    fake.pos = [{"symbol": "XOM", "qty": "49", "current_price": "101", "unrealized_plpc": "0"}]
    b.reconcile(fake.positions()); b.bad_news_exits()
    assert ("sell", "XOM") in fake.placed and b.ledger["trades"][0]["exitReason"].startswith("bad news")


def test_meme_coins_never_traded(monkeypatch):
    from trading_bot import halal
    assert not halal.allowed("DOGE/USD", {"crypto": {"DOGE/USD": {}}})
    assert not halal.allowed("SPY", {"stocks": {"SPY": {}}})
    assert not halal.allowed("AAVE/USD", {"crypto": {"AAVE/USD": {}}})
    assert halal.allowed("BTC/USD", UNIVERSE)


def test_watch_mode(monkeypatch):
    from trading_bot import watch
    prices = iter([1.0, 1.07])
    monkeypatch.setattr(watch, "_cg_id", lambda t, n, c: "dogecoin")
    monkeypatch.setattr(watch, "_prices", lambda ids: {"dogecoin": next(prices)})
    s = {}
    ev = {"k": {"key": "k", "summary": "Celebrity pumps DOGE", "memes": [{"ticker": "DOGE", "direction": "up"}]}}
    watch.update(s, ev); watch.update(s, ev)
    w = s["watch"][0]
    assert w["status"] == "closed" and w["exitReason"] == "target +6%" and w["pnlPct"] == 6.0


def test_halal_screen_rules():
    from trading_bot import halal
    assert halal.sic_reason(6021) and halal.sic_reason(2082) and halal.sic_reason(3761)
    assert halal.sic_reason(1311) is None and halal.sic_reason(3674) is None
    ok, why, _ = halal.screen_stock("LMT", {}, 400)
    assert not ok and "nuclear" in why
    facts = {"facts": {"us-gaap": {"LongTermDebt": {"units": {"USD": [{"val": 50e9, "end": "2026-06-30", "form": "10-Q", "filed": "x"}]}}},
                       "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"val": 1e9, "end": "2026-07-01"}]}}}}}
    assert halal.total_debt(facts) == 50e9 and halal.shares_out(facts) == 1e9


def test_rss_parsing():
    from trading_bot.news import parse_rss
    xml = """<rss><channel><item><title>Fed cuts rates by half a point - Reuters</title><link>https://news.google.com/x</link>
             <pubDate>Mon, 09 Nov 2026 14:00:00 GMT</pubDate><source url="https://www.reuters.com">Reuters</source></item></channel></rss>"""
    it = parse_rss(xml, "Google News")[0]
    assert it["publisher"] == "Reuters" and it["title"] == "Fed cuts rates by half a point"


def test_report_and_publish_schedule(monkeypatch):
    fake = FakeAlpaca()
    B = wire(monkeypatch, fake, [{"symbol": "XOM", "direction": "up", "confidence": 0.8, "why": "x"}])
    from trading_bot import report, publish
    b = B.Bot(); b.universe = UNIVERSE; b.cycle()
    st = report.write(b)
    assert st["team"] == "trading" and st["account"]["equity"] == 100000.0 and st["positions"]
    assert publish.due({"publishNow": True})
    assert not publish.due({"publishNow": True, "lastPublish": util.iso()})


def test_paper_only_guard():
    from trading_bot.alpaca import Alpaca
    with pytest.raises(SystemExit):
        Alpaca(key="a", secret="b", trading_url="https://api.alpaca.markets")


def test_backtest_exit_logic():
    from trading_bot.backtest import exit_for, stats
    t0 = NOW - timedelta(days=2)
    bars = [{"t": T(t0 + timedelta(minutes=5 * i)), "o": 100, "h": 100.5 + i * 0.5, "l": 99.5, "c": 100} for i in range(20)]
    ex = exit_for({"t": T(t0), "symbol": "BTC/USD", "entry": 100.0}, bars, [])
    assert ex["exitReason"] == "target +6%" and ex["exit"] == pytest.approx(106)
    s = stats([{"pnl": 300, "pnlPct": 6, "exitT": T(NOW), "exitReason": "target +6%"}])
    assert s["winRate"] == 100 and s["totalPct"] == 0.3
