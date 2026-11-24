"""Market Study: the slow, evidence-based side of the bot.

Every day it ranks every halal stock and coin on TREND + MOMENTUM + QUALITY, the rules with the longest track
record in the research (time-series momentum / moving-average trend following):
  * trend:    price above its 50-day average, and the 50-day above the 200-day (stocks); coins: above the 50-day
  * momentum: average of the 3, 6 and 12-month returns, divided by how jumpy the price is (risk-adjusted)
  * quality:  lower debt (from the SEC numbers the halal screen already pulls) ranks a little higher
  * regime:   new stock buys only while SPY is above its 200-day average; new coin buys only while BTC is above its 50-day

The bot's "trend sleeve" (off until you run `tb trend <pct>`) holds the top picks, keeps them while the trend holds,
and sells when the price closes under the 50-day average, drops out of the top list, or hits a wide trailing stop.

    python -m trading_bot.study            build today's study now (data/trading/study.json)
    python -m trading_bot.study backtest 12   test the trend rules on the last 12 months of daily prices (no orders)
"""
import math, sys
from datetime import timedelta
from . import config as C
from .util import load_env, read_json, write_json, iso, now_utc, now_et, log, DATA

STUDY_FILE = DATA / "study.json"
BACKTEST_FILE = DATA / "study_backtest.json"
REGIME = "SPY"
COIN_REGIME = "BTC/USD"


def sma(xs, n):
    return sum(xs[-n:]) / n if len(xs) >= n else None


def ret(xs, n):
    return xs[-1] / xs[-1 - n] - 1 if len(xs) > n and xs[-1 - n] else None


def vol(xs, n=63):
    """Annualised volatility of daily returns (how jumpy the price is)."""
    xs = xs[-(n + 1):]
    r = [b / a - 1 for a, b in zip(xs, xs[1:]) if a]
    if len(r) < 20:
        return None
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(252)


def score(closes, crypto=False, debt=None):
    """One symbol's study card from its daily closes (oldest first). Pure function: also used by the backtest."""
    if len(closes) < 60:
        return None
    p, m50, m200 = closes[-1], sma(closes, 50), sma(closes, 200)
    r3, r6, r12 = ret(closes, 63), ret(closes, 126), ret(closes, 252)
    rs = [x for x in (r3, r6, r12) if x is not None]
    v = vol(closes)
    if not rs or not v:
        return None
    mom = sum(rs) / len(rs)
    if crypto:
        up = p > m50 and (r3 or 0) > 0
    else:
        up = m200 is not None and p > m50 > m200 and (r6 if r6 is not None else mom) > 0
    quality = None if debt is None else max(0.0, 1 - debt / 0.33)
    s = mom / v * (0.8 + 0.4 * (quality if quality is not None else 0.5))
    return {"price": round(p, 4), "ma50": round(m50, 4), "ma200": round(m200, 4) if m200 else None,
            "r3": _pct(r3), "r6": _pct(r6), "r12": _pct(r12), "vol": round(v * 100, 1),
            "quality": None if quality is None else round(quality, 2), "uptrend": bool(up), "score": round(s, 3)}


def _pct(x):
    return None if x is None else round(x * 100, 1)


def regime_on(closes, n=200):
    m = sma(closes, n)
    return bool(m and closes[-1] > m)


def picks(cards, n_stocks, n_coins):
    """The names the trend sleeve should hold: top uptrending stocks + coins, by score."""
    st = sorted((c for c in cards if c["uptrend"] and not c["crypto"] and c["symbol"] not in C.CORE_ETFS),
                key=lambda c: -c["score"])
    co = sorted((c for c in cards if c["uptrend"] and c["crypto"]), key=lambda c: -c["score"])
    return [c["symbol"] for c in st[:n_stocks]], [c["symbol"] for c in co[:n_coins]]


def fetch_closes(a, stocks, coins, days):
    start = iso(now_utc() - timedelta(days=days))
    bars = {}
    for i in range(0, len(stocks), 50):
        bars.update(a.stock_bars(stocks[i:i + 50], "1Day", start, adjustment="all"))
    if coins:
        bars.update(a.crypto_bars(coins, "1Day", start))
    return bars


def build(a, universe):
    """Rank everything and save the study the bot + Trading tab read."""
    stocks = sorted(set((universe.get("stocks") or {})) | {REGIME})
    coins = sorted(set((universe.get("crypto") or {})) | {COIN_REGIME})
    bars = fetch_closes(a, stocks, coins, 420)
    cards = []
    for sym, bs in bars.items():
        if sym == REGIME:
            continue
        info = (universe.get("stocks") or {}).get(sym) or {}
        c = score([float(b["c"]) for b in bs], crypto="/" in sym, debt=info.get("debtToMarketCap"))
        if c:
            cards.append({"symbol": sym, "crypto": "/" in sym, "theme": info.get("theme"), **c})
    cards.sort(key=lambda c: -c["score"])
    spy = [float(b["c"]) for b in bars.get(REGIME) or []]
    btc = [float(b["c"]) for b in bars.get(COIN_REGIME) or []]
    n_s, n_c = C.TREND["stocks"], C.TREND["coins"]
    ps, pc = picks(cards, n_s, n_c)
    st = {"builtAt": iso(), "date": now_et().date().isoformat(),
          "regime": {"stocks": regime_on(spy, 200) if spy else None, "coins": regime_on(btc, 50) if btc else None,
                     "spy": spy[-1] if spy else None, "spy200": round(sma(spy, 200), 2) if sma(spy, 200) else None,
                     "btc": btc[-1] if btc else None, "btc50": round(sma(btc, 50), 2) if sma(btc, 50) else None},
          "picks": {"stocks": ps, "coins": pc}, "ranked": cards[:40], "counted": len(cards),
          "uptrends": sum(1 for c in cards if c["uptrend"]),
          "rules": "Trend: price over 50-day avg over 200-day avg (coins: over 50-day). Momentum: avg 3/6/12-month "
                   "return / volatility. Quality: lower debt ranks higher. New stock buys only while SPY is over its "
                   "200-day avg; coins only while BTC is over its 50-day.",
          "plain": plain(cards, ps, pc, spy, btc)}
    write_json(STUDY_FILE, st)
    log(f"Market study: {st['uptrends']} of {len(cards)} names in uptrends; picks {', '.join(ps + pc) or 'none'}; "
        f"{st['plain']['regime']}", "Market Study")
    return st


def plain(cards, ps, pc, spy, btc):
    on = regime_on(spy, 200) if spy else None
    con = regime_on(btc, 50) if btc else None
    reg = ("Stock market is in an uptrend (SPY over its 200-day average)" if on else
           "Stock market is in a downtrend (SPY under its 200-day average): no new trend buys in stocks" if on is False
           else "Stock market trend unknown")
    reg += "; coins " + ("in an uptrend" if con else "in a downtrend, no new coin buys" if con is False else "unknown")
    by = {c["symbol"]: c for c in cards}
    lines = [f"{s}: up {by[s]['r6']:+.0f}% in 6 months, above its averages" if by[s].get("r6") is not None
             else f"{s}: above its averages" for s in ps + pc]
    return {"regime": reg, "picks": lines}


def load():
    return read_json(STUDY_FILE, {}) or {}


# ---------------------------------------------------------------- backtest (daily bars, no orders)
def backtest(a, universe, months=12):
    """Replays the trend rules day by day. Decide on a day's close, trade at the NEXT day's open (no peeking).
    Weekly entries (first trading day of the week), daily exits on trend breaks or the trailing stop.
    0.05% cost per buy/sell. Honest limits: today's halal list (survivorship bias), IEX daily prices."""
    stocks = sorted(set((universe.get("stocks") or {})) - set(C.CORE_ETFS) | {REGIME, "SPUS"})
    coins = sorted(set((universe.get("crypto") or {})) | {COIN_REGIME})
    days = months * 31 + 420
    bars = fetch_closes(a, stocks, coins, days)
    return simulate(bars, universe, months)


def simulate(bars, universe, months, n_s=None, n_c=None, trail=None, cost=0.0005):
    n_s, n_c = n_s or C.TREND["stocks"], n_c or C.TREND["coins"]
    trail = trail if trail is not None else C.TREND["trail_pct"]
    day = lambda b: b["t"][:10]
    spy = bars.get(REGIME) or []
    if len(spy) < 260:
        return {"error": "not enough SPY history"}
    dates = [day(b) for b in spy]
    first = max(0, len(dates) - int(months * 21))
    first = max(first, 210)
    series = {s: {day(b): b for b in bs} for s, bs in bars.items()}
    hist = {s: [] for s in bars}             # closes up to the current day
    idx = {s: 0 for s in bars}
    ordered = {s: sorted(bs, key=day) for s, bs in bars.items()}
    debt = {s: (v or {}).get("debtToMarketCap") for s, v in (universe.get("stocks") or {}).items()}

    def advance(d):
        for s, bs in ordered.items():
            i = idx[s]
            while i < len(bs) and day(bs[i]) <= d:
                hist[s].append(float(bs[i]["c"]))
                i += 1
            idx[s] = i

    cash, pos, trades, curve = 1.0, {}, [], []
    pending_buys, pending_sells = [], []
    for k, d in enumerate(dates):
        advance(d)
        if k < first:
            continue
        # execute yesterday's decisions at today's open
        for s, why in pending_sells:
            if s in pos and d in series[s]:
                px = float(series[s][d]["o"])
                p = pos.pop(s)
                cash += p["qty"] * px * (1 - cost)
                trades.append({"symbol": s, "in": p["date"], "out": d, "pct": round((px / p["price"] - 1) * 100, 2), "why": why})
        pending_sells = []
        if pending_buys:
            value = cash + sum(p["qty"] * hist[s][-1] for s, p in pos.items())
            slot = value / (n_s + n_c)
            for s in pending_buys:
                if s in pos or s not in series or d not in series[s]:
                    continue
                px = float(series[s][d]["o"])
                spend = min(slot, cash)
                if spend < value * 0.01:
                    continue
                cash -= spend
                pos[s] = {"qty": spend * (1 - cost) / px, "price": px, "high": px, "date": d}
        pending_buys = []
        # mark to market, trailing stops, trend breaks (decided on today's close)
        for s, p in pos.items():
            c = hist[s][-1]
            p["high"] = max(p["high"], c)
            crypto = "/" in s
            m50 = sma(hist[s], 50)
            if trail and c <= p["high"] * (1 - trail / 100):
                pending_sells.append((s, f"trailing stop {trail:g}%"))
            elif m50 and c < m50:
                pending_sells.append((s, "closed under 50-day average"))
        value = cash + sum(p["qty"] * hist[s][-1] for s, p in pos.items())
        curve.append({"date": d, "value": round(value, 5)})
        # weekly entries: first trading day of a new week
        if k + 1 < len(dates) and _week(dates[k + 1]) != _week(d):
            cards = []
            for s, h in hist.items():
                if s in (REGIME, "SPUS"):
                    continue
                c = score(h, crypto="/" in s, debt=debt.get(s))
                if c:
                    cards.append({"symbol": s, "crypto": "/" in s, **c})
            ps, pc = picks(cards, n_s, n_c)
            if not regime_on(hist[REGIME], 200):
                ps = []
            if hist.get(COIN_REGIME) and not regime_on(hist[COIN_REGIME], 50):
                pc = []
            keep = set(ps + pc) | {c["symbol"] for c in sorted(cards, key=lambda c: -c["score"])[:2 * (n_s + n_c)] if c["uptrend"]}
            leaving = {s for s, _ in pending_sells}
            for s in list(pos):
                if s not in keep and s not in leaving:
                    pending_sells.append((s, "dropped out of the top list"))
            held_after = len(pos) - len({s for s, _ in pending_sells})
            room = (n_s + n_c) - held_after
            pending_buys = [s for s in ps + pc if s not in pos][:max(0, room)]

    def bh(sym):
        h = [float(series[sym][d]["c"]) for d in dates[first:] if d in series.get(sym, {})]
        return round((h[-1] / h[0] - 1) * 100, 2) if len(h) > 1 else None

    vals = [c["value"] for c in curve]
    peak, mdd = 0, 0
    for v in vals:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    spy_c = [float(series[REGIME][d]["c"]) for d in dates[first:]]
    spk, smdd = 0, 0
    for v in spy_c:
        spk = max(spk, v)
        smdd = min(smdd, v / spk - 1)
    wins = [t for t in trades if t["pct"] > 0]
    out = {"builtAt": iso(), "months": months, "from": dates[first], "to": dates[-1],
           "settings": {"stocks": n_s, "coins": n_c, "trailPct": trail, "costPct": cost * 100},
           "returnPct": round((vals[-1] - 1) * 100, 2) if vals else None, "maxDrawdownPct": round(mdd * 100, 2),
           "spyReturnPct": bh(REGIME), "spyMaxDrawdownPct": round(smdd * 100, 2), "spusReturnPct": bh("SPUS"),
           "trades": len(trades), "winRatePct": round(len(wins) / len(trades) * 100, 1) if trades else None,
           "avgWinPct": round(sum(t["pct"] for t in wins) / len(wins), 2) if wins else None,
           "avgLossPct": round(sum(t["pct"] for t in trades if t["pct"] <= 0) / max(1, len(trades) - len(wins)), 2) if trades else None,
           "holdingNow": sorted(pos), "lastTrades": trades[-25:], "curve": curve[::max(1, len(curve) // 120)],
           "note": "Hypothetical. Uses today's halal list (stocks that later failed the screen are missing) and "
                   "IEX daily prices; trades at the next day's open with 0.05% cost. Not a promise of future results."}
    return out


def _week(d):
    from datetime import date
    y, m, dd = map(int, d.split("-"))
    return date(y, m, dd).isocalendar()[:2]


def main(argv):
    load_env()
    from .alpaca import Alpaca
    from . import halal
    a = Alpaca()
    uni = halal.build_universe(a)
    if argv[:1] == ["backtest"]:
        months = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 12
        print(f"Testing the trend rules on the last {months} months of daily prices (no orders)...")
        r = backtest(a, uni, months)
        write_json(BACKTEST_FILE, r)
        if r.get("error"):
            print("Could not run:", r["error"])
            return
        print(f"{r['from']} to {r['to']}")
        print(f"Trend rules: {r['returnPct']:+.1f}%  (worst drop {r['maxDrawdownPct']:.1f}%)  {r['trades']} trades, "
              f"{r['winRatePct'] or 0:.0f}% winners, avg win {r['avgWinPct'] or 0:+.1f}%, avg loss {r['avgLossPct'] or 0:+.1f}%")
        print(f"SPY just holding: {r['spyReturnPct']:+.1f}%  (worst drop {r['spyMaxDrawdownPct']:.1f}%)")
        if r.get("spusReturnPct") is not None:
            print(f"SPUS just holding: {r['spusReturnPct']:+.1f}%")
        print("Holding at the end:", ", ".join(r["holdingNow"]) or "nothing (cash)")
        print("Saved to the Trading tab. Hypothetical results, not a promise.")
        return
    st = build(a, uni)
    print(st["plain"]["regime"])
    print(f"{st['uptrends']} of {st['counted']} names in uptrends. Top picks:")
    for line in st["plain"]["picks"]:
        print("  " + line)


if __name__ == "__main__":
    main(sys.argv[1:])
