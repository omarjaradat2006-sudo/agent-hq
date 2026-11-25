import json
import pytest
from trading_bot import lab_engine as E
from trading_bot import lab as L


def daily(prices, start="2023-01-02", lows=None):
    from datetime import date, timedelta
    d0, out, d = date.fromisoformat(start), [], 0
    for k, p in enumerate(prices):
        day = d0 + timedelta(days=d)
        while day.weekday() >= 5:
            d += 1; day = d0 + timedelta(days=d)
        lo = lows[k] if lows else p * 0.995
        out.append({"t": f"{day.isoformat()}T05:00:00Z", "o": p, "h": p * 1.005, "l": lo, "c": p, "v": 1000 + (k % 7) * 100})
        d += 1
    return out


def market(n=800):
    rise = [100 * (1.0015 ** i) * (1 + 0.01 * ((-1) ** i)) for i in range(n)]
    chop = [100 * (1 + 0.04 * ((-1) ** (i // 3))) * (0.9995 ** i) for i in range(n)]
    return E.load_series({"SPY": daily(rise), "UP": daily([p * 1.3 for p in rise]), "CHOP": daily(chop)})


def test_validate_cleans_and_clamps():
    r = E.validate({"name": "x", "entry": [{"f": "close_above_sma", "n": 9999}, {"f": "bogus"}, {"f": "rsi_below", "n": 2}],
                    "exit": {"stop_pct": "8"}, "max_positions": 99, "regime": "weird"})
    assert r["entry"] == [{"f": "close_above_sma", "n": 300}]          # clamped; unknown + incomplete dropped
    assert r["exit"] == {"stop_pct": 8.0} and r["max_positions"] == 20 and r["regime"] == "none"
    assert E.validate({"entry": []}) is None
    assert E.validate({"entry": [{"f": "breakout", "days": 20}]})["exit"] == {"max_days": 20}   # always a way out
    a = E.validate({"entry": [{"f": "breakout", "days": 20}, {"f": "close_above_sma", "n": 50}]})
    b = E.validate({"entry": [{"f": "close_above_sma", "n": 50}, {"f": "breakout", "days": 20}]})
    assert E.rule_id(a) == E.rule_id(b)                                   # same rule, same id


def test_trend_rule_makes_money_in_uptrend_and_stops_fill_realistically():
    data = market()
    rule = E.validate({"name": "trend", "universe": "stocks", "max_positions": 2,
                       "entry": [{"f": "close_above_sma", "n": 50}], "exit": {"exit_below_sma": 50}})
    p = E.periods(data)
    st = E.simulate(rule, data, *p["full"])
    assert st["returnPct"] > 0 and st["trades"] >= 1
    # a gap below the stop fills at the (worse) open, not at the stop
    prices = [100.0] * 60 + [80.0] * 30
    s = E.load_series({"SPY": daily([100.0] * 90), "X": daily(prices)})
    r = E.validate({"name": "t", "max_positions": 1, "entry": [{"f": "return_above", "days": 2, "pct": -1}], "exit": {"stop_pct": 5}})
    st2 = E.simulate(r, s, s["SPY"].d[30], s["SPY"].d[-1])
    stops = [t for t in st2.get("trades", [])] if isinstance(st2.get("trades"), list) else None
    assert st2["avgLossPct"] is not None and st2["avgLossPct"] <= -19   # gapped from 100 to 80: lost ~20%, not 5%


def test_evaluate_and_robustness_give_verdicts():
    data = market()
    good = E.validate({"name": "trend", "max_positions": 2, "entry": [{"f": "close_above_sma", "n": 50}],
                       "exit": {"exit_below_sma": 50}})
    ev = E.evaluate(good, data)
    assert ev["verdict"] in ("passed", "promising", "failed") and set(ev["periods"]) >= {"full", "part1", "part2", "part3", "last60"}
    rob = E.robustness(good, data)
    assert rob is not None and 0 <= rob <= 1


def test_youtube_ids_and_lessons_and_consensus():
    assert L.youtube_ids("see https://www.youtube.com/watch?v=abcdefghijk and youtu.be/ABCDEFGHIJK, again "
                         "https://youtube.com/watch?v=abcdefghijk") == ["abcdefghijk", "ABCDEFGHIJK"]
    st = L.fresh_state(7)
    j = {"person": "Trader A", "style": "swing", "lessons": [
        {"theme": "cut_losses_fast", "lesson": "Sell losers at -7 to -8%", "evidence": "track record",
         "rule": {"name": "a", "entry": [{"f": "breakout", "days": 20}], "exit": {"stop_pct": 8}}},
        {"theme": "nonsense", "lesson": "x"}], "mentions": ["Book B"]}
    assert L.add_lessons(st, {"url": "u1", "about": "Trader A"}, j) == 2
    L.add_lessons(st, {"url": "u2", "about": "Trader C"}, {"person": "Trader C", "lessons": [{"theme": "cut_losses_fast", "lesson": "small losses"}]})
    assert len(st["rules"]) == 1 and st["lessons"][1]["theme"] == "other"
    top = L.consensus(st)[0]
    assert top["theme"] == "cut_losses_fast" and top["people"] == 2


def test_brain_rotates_keys_and_rests_on_daily_quota(monkeypatch):
    import io, urllib.error
    monkeypatch.setenv("LAB_GEMINI_KEYS", "k1,k2"); monkeypatch.setenv("GEMINI_API_KEY", "shared")
    monkeypatch.setattr(L, "PAUSE", 0)
    st = {}
    b = L.Brain(st)
    assert [k for k, _, _ in b.keys] == ["k1", "k2", "shared"]
    b.models = {"strong": ["flash"], "lite": ["lite"]}
    used = []

    def fake_req(method, path, body=None, timeout=0):
        used.append(L.gemini.KEY)
        if L.gemini.KEY == "k1":
            raise urllib.error.HTTPError("u", 429, "quota", {}, io.BytesIO(b"GenerateRequestsPerDayPerProjectPerModel"))
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": 1})}]}}]}
    monkeypatch.setattr(L.gemini, "_req", fake_req)
    out, _ = b.ask([{"text": "hi"}])
    assert out == {"ok": 1} and used == ["k1", "k2"]
    out, _ = b.ask([{"text": "hi"}])
    assert used[-1] == "k2"                                # k1 rests for the rest of the (Pacific) day
    for k in ("k2", "shared"):
        b._slot(k)["done"] = True
    with pytest.raises(L.OutOfQuota):
        b.ask([{"text": "hi"}])


def test_next_task_round_robin_and_second_pass():
    st = L.fresh_state(1)
    st["queue"] = []
    st["pendingSources"] = [{"id": 1, "about": "A"}, {"id": 2, "about": "A"}, {"id": 3, "about": "B"}]
    st["lastAbout"] = "A"
    assert L.next_task(st)[1]["about"] == "B"
    st["pendingSources"] = []
    st["mentions"] = ["Reminiscences of a Stock Operator", "Reminiscences of a Stock Operator", "Some New Trader"]
    st["lessons"] = [{"theme": "cut_losses_fast"}]
    kind, task = L.next_task(st)
    assert kind == "find" and st["pass"] == 2
