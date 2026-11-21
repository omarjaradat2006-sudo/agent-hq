"""The Coach: the bot learns from its own trades and from the trades it skipped.

Runs every weekday evening after the close (and with `tb coach`). It looks at:
  - every closed trade of the last 30 days: what won, what lost, by confidence, by news source, by stock
  - every story it SKIPPED: what the price did the next trading day (missed winners / dodged losers)
and nudges its own settings a small step at a time, always inside fixed safe ranges:
  - aggression      0.5x - 2x   how big each trade is (inside Omar's max-invested budget)
  - min_confidence  0.50 - 0.80 how sure the AI must be before a buy
  - max_move_pct    2% - 6%     how far a stock may already have run before it's "too late"
  - source trust    0.5x - 1.5x bigger trades on news sources that have paid off, smaller on ones that haven't
  - avoid list      a stock that lost 3+ times in a row is skipped for 14 days
It NEVER changes Omar's limits: max invested, daily -3% halt, -10% kill switch, halal rules, paper/live.
Every change is written to data/trading/coach.json and shown on the Trading tab. `tb coach reset` undoes all of it.
"""
import json, sys
from datetime import timedelta
from . import util
from .util import read_json, write_json, iso, now_utc, parse_time, log, ET


def _coach_file():
    return util.DATA / "coach.json"


def _decisions_file():
    return util.LOCAL / "decisions.jsonl"
LIMITS = {"aggression": (0.5, 2.0), "min_confidence": (0.5, 0.8), "max_move_pct": (0.02, 0.06)}
DEFAULTS = {"aggression": 1.0, "min_confidence": 0.6, "max_move_pct": 0.03}


def load():
    return read_json(_coach_file(), {}) or {}


def clamp(k, v):
    lo, hi = LIMITS[k]
    return round(max(lo, min(hi, v)), 4)


def log_decision(d):
    """Every decision is kept (the dashboard only keeps the last 150) so the Coach can check skipped stories later."""
    try:
        util.LOCAL.mkdir(parents=True, exist_ok=True)
        with open(_decisions_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _decisions(since):
    out = []
    try:
        with open(_decisions_file(), encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if parse_time(d.get("t")) and parse_time(d["t"]) >= since:
                    out.append(d)
    except FileNotFoundError:
        pass
    return out


def _next_day_returns(alpaca, rows):
    """% change from the close of the day a story was skipped to the close of the next trading day."""
    syms = sorted({r["symbol"] for r in rows if "/" not in r["symbol"]})
    if not syms:
        return {}
    start = iso(min(parse_time(r["t"]) for r in rows) - timedelta(days=5))
    bars = {}
    for i in range(0, len(syms), 50):
        try:
            bars.update(alpaca.stock_bars(syms[i:i + 50], "1Day", start))
        except Exception:  # noqa: BLE001
            pass
    out = {}
    for r in rows:
        b = bars.get(r["symbol"]) or []
        day = parse_time(r["t"]).astimezone(ET).date().isoformat()
        idx = [i for i, x in enumerate(b) if parse_time(x["t"]).astimezone(ET).date().isoformat() >= day]
        if len(idx) >= 1 and idx[0] + 1 < len(b):
            c0, c1 = float(b[idx[0]]["c"]), float(b[idx[0] + 1]["c"])
            out[id(r)] = (c1 - c0) / c0 * 100
    return out


def _avg(xs):
    return sum(xs) / len(xs) if xs else None


def run(alpaca, ledger, now=None):
    now = now or now_utc()
    old = load()
    knobs = {**DEFAULTS, **(old.get("knobs") or {})}
    before = dict(knobs)
    lessons, changes = [], []
    since = now - timedelta(days=30)

    closed = [t for t in ledger.get("trades", []) if t.get("status") == "closed" and parse_time(t.get("closedAt"))
              and parse_time(t["closedAt"]) >= since and t.get("pnlPct") is not None]
    recent = sorted(closed, key=lambda t: t["closedAt"])[-20:]

    # 1. aggression: bigger trades when it's working, smaller when it isn't
    if len(recent) >= 5:
        wins = sum(1 for t in recent if t["pnl"] > 0)
        avg = _avg([t["pnlPct"] for t in recent])
        total = sum(t["pnl"] for t in recent)
        if total > 0 and wins / len(recent) >= 0.5:
            knobs["aggression"] = clamp("aggression", knobs["aggression"] * 1.1)
            lessons.append(f"Last {len(recent)} trades made ${total:,.2f} ({wins} won): trading a bit bigger.")
        elif avg is not None and avg < -0.5:
            knobs["aggression"] = clamp("aggression", knobs["aggression"] * 0.9)
            lessons.append(f"Last {len(recent)} trades averaged {avg:+.2f}%: trading a bit smaller until it improves.")
        else:
            lessons.append(f"Last {len(recent)} trades: {wins} won, average {avg:+.2f}%. Size unchanged.")
    else:
        lessons.append(f"Only {len(recent)} closed trades so far: needs 5+ before changing trade size.")

    # 2. confidence floor: are the low-confidence buys losing?
    lo = [t["pnlPct"] for t in closed if (t.get("reason") or {}).get("confidence", 1) < 0.7]
    hi = [t["pnlPct"] for t in closed if (t.get("reason") or {}).get("confidence", 0) >= 0.7]
    if len(lo) >= 5 and _avg(lo) < -0.5 and (not hi or _avg(hi) > _avg(lo)):
        knobs["min_confidence"] = clamp("min_confidence", knobs["min_confidence"] + 0.05)
        lessons.append(f"Low-confidence buys averaged {_avg(lo):+.2f}% ({len(lo)} trades): now needs more confidence to buy.")
    elif len(lo) >= 5 and _avg(lo) > 0.5:
        knobs["min_confidence"] = clamp("min_confidence", knobs["min_confidence"] - 0.03)
        lessons.append(f"Low-confidence buys still made {_avg(lo):+.2f}% on average: accepting slightly weaker signals.")

    # 3. news sources that pay off get bigger trades
    by_pub = {}
    for t in closed:
        for p in (t.get("reason") or {}).get("publishers") or []:
            by_pub.setdefault(p, []).append(t["pnlPct"])
    trust = dict(old.get("trust") or {})
    for p, xs in by_pub.items():
        if len(xs) >= 4:
            new = round(max(0.5, min(1.5, 1 + _avg(xs) / 5)), 2)
            if abs(new - trust.get(p, 1.0)) >= 0.05:
                lessons.append(f"{p}: {len(xs)} trades averaging {_avg(xs):+.2f}%, trust {trust.get(p, 1.0):.2f} -> {new:.2f}.")
            trust[p] = new

    # 4. stocks that keep losing go on a 14-day avoid list
    avoid = {k: v for k, v in (old.get("avoid") or {}).items() if parse_time(v) and parse_time(v) > now}
    by_sym = {}
    for t in sorted(closed, key=lambda t: t["closedAt"]):
        by_sym.setdefault(t["symbol"], []).append(t["pnl"])
    for s, ps in by_sym.items():
        if len(ps) >= 3 and all(p <= 0 for p in ps[-3:]) and s not in avoid:
            avoid[s] = iso(now + timedelta(days=14))
            lessons.append(f"{s} lost its last 3 trades: skipping it for 14 days.")

    # 5. missed opportunities: what did the skipped stories do the next day?
    seen = {(d["symbol"], d["t"]) for d in _decisions(since)}
    older = [d for d in ledger.get("decisions", []) if (d.get("symbol"), d.get("t")) not in seen
             and parse_time(d.get("t")) and parse_time(d["t"]) >= since]                # history from before the Coach
    skipped = [d for d in _decisions(since) + older if d.get("outcome") in ("waiting", "skipped")
               and parse_time(d["t"]) <= now - timedelta(days=1)]
    uniq = {}
    for d in skipped:
        uniq.setdefault((d["symbol"], d.get("event", ""), d["t"][:10]), d)
    rows = list(uniq.values())
    rets = _next_day_returns(alpaca, rows) if rows else {}
    late = [rets[id(r)] for r in rows if id(r) in rets and ("too late" in r["why"] or "already" in r["why"] or "too much" in r["why"])]
    if len(late) >= 5:
        a = _avg(late)
        if a >= 1.0:
            knobs["max_move_pct"] = clamp("max_move_pct", knobs["max_move_pct"] + 0.005)
            lessons.append(f"Stocks skipped as 'already moved too much' kept rising (+{a:.2f}% next day, {len(late)} cases): allowing a bigger move before buying.")
        elif a <= -1.0:
            knobs["max_move_pct"] = clamp("max_move_pct", knobs["max_move_pct"] - 0.005)
            lessons.append(f"Stocks skipped as 'already moved too much' fell {a:.2f}% next day: good skips, tightening a little.")
    graded = sorted([(rets[id(r)], r) for r in rows if id(r) in rets], key=lambda x: -x[0])
    missed = [{"symbol": r["symbol"], "t": r["t"], "nextDayPct": round(x, 2), "why": r["why"][:90],
               "event": r.get("event", "")[:90]} for x, r in graded[:5] if x > 1.0]
    dodged = [{"symbol": r["symbol"], "t": r["t"], "nextDayPct": round(x, 2), "why": r["why"][:90]}
              for x, r in graded[::-1][:5] if x < -1.0]
    if graded:
        good = sum(1 for x, _ in graded if x <= 0)
        lessons.append(f"Checked {len(graded)} skipped stories: {good} would have lost or gone nowhere, "
                       f"{len(graded) - good} would have gained the next day.")
    if missed:
        lessons.append("Biggest misses: " + ", ".join(f"{m['symbol']} {m['nextDayPct']:+.1f}%" for m in missed[:3]) + ".")

    for k in knobs:
        if knobs[k] != before.get(k):
            changes.append({"t": iso(now), "setting": k, "from": before.get(k), "to": knobs[k]})
    out = {"updatedAt": iso(now), "knobs": knobs, "trust": trust, "avoid": avoid, "lessons": lessons,
           "missed": missed, "dodged": dodged,
           "stats": {"closedTrades30d": len(closed), "skippedChecked": len(graded)},
           "history": ((old.get("history") or []) + changes)[-60:], "limits": {k: list(v) for k, v in LIMITS.items()}}
    write_json(_coach_file(), out)
    log("Coach: " + (" | ".join(lessons[:3]) or "nothing to change yet"), "Coach")
    return out


def reset():
    c = load()
    c.update({"knobs": dict(DEFAULTS), "trust": {}, "avoid": {}, "updatedAt": iso(),
              "lessons": ["Reset by Omar: back to the starting settings."]})
    write_json(_coach_file(), c)
    return c


if __name__ == "__main__":
    from .util import load_env
    load_env()
    if sys.argv[1:2] == ["reset"]:
        reset()
        print("Coach reset: back to the starting settings.")
    else:
        from .alpaca import Alpaca
        r = run(Alpaca(), read_json(util.DATA / "ledger.json", {}) or {})
        print("\n".join(["What the bot learned:"] + [" - " + x for x in r["lessons"]] +
                         [f"Settings now: {json.dumps(r['knobs'])}"]))
        from . import publish
        publish.push("Trading bot: Coach review")
