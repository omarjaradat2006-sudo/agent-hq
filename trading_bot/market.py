"""Price/volume confirmation: is the market actually reacting the way the news says?

rvol  = volume in the last window / average volume in the SAME clock window on prior days
         (so the busy open and close don't fake a volume spike)
move  = price change since just before the news broke (previous close for overnight news)
Passes when rvol >= 1.5 and +0.3% <= move <= +3% in the expected direction.
"""
from datetime import timedelta
from . import config as C
from .util import iso, now_utc, parse_time, ET


def _window_stats(bars, now, window, days_back):
    """Return (vol_now, avg_vol_same_window_prior_days)."""
    bars = [(parse_time(b["t"]), b) for b in bars]
    start = now - window
    vol_now = sum(b["v"] for t, b in bars if start < t <= now)
    prior = []
    for d in range(1, days_back + 1):
        s, e = start - timedelta(days=d), now - timedelta(days=d)
        vs = [b["v"] for t, b in bars if s < t <= e]
        if vs:
            prior.append(sum(vs))
    avg = sum(prior) / len(prior) if prior else 0
    return vol_now, avg


def _price_at(bars, when):
    """Close of the last bar that started before `when`."""
    best = None
    for b in bars:
        if parse_time(b["t"]) < when:
            best = b
        else:
            break
    return float(best["c"]) if best else None


def confirm(alpaca, symbol, direction, first_seen, now=None, bars=None, rules=None):
    R = rules or C.confirm_rules()
    now = now or now_utc()
    first_seen = parse_time(first_seen)
    crypto = "/" in symbol
    if crypto:
        window, days, tf = timedelta(hours=1), 7, "15Min"
    else:
        window, days, tf = timedelta(minutes=30), 10, "5Min"
    if bars is None:
        start = iso(now - timedelta(days=days + (1 if crypto else 5)))
        fetch = alpaca.crypto_bars if crypto else alpaca.stock_bars
        bars = fetch([symbol], tf, start, iso(now)).get(symbol, [])
    bars = sorted(bars, key=lambda b: b["t"])
    res = {"symbol": symbol, "direction": direction, "at": iso(now), "passed": False}
    if len(bars) < 10:
        res["reason"] = "not enough price data"
        return res
    last = float(bars[-1]["c"])
    ref = _price_at(bars, first_seen)
    if not crypto:
        today_open = now.astimezone(ET).replace(hour=9, minute=30, second=0, microsecond=0)
        if first_seen.astimezone(ET) < today_open:            # overnight / pre-market news
            prev = [b for b in bars if parse_time(b["t"]).astimezone(ET) < today_open]
            ref = float(prev[-1]["c"]) if prev else ref
    if not ref:
        res["reason"] = "no price from before the news"
        return res
    vol_now, vol_avg = _window_stats(bars, now, window, days)
    rvol = (vol_now / vol_avg) if vol_avg else 0.0
    move = (last - ref) / ref * (1 if direction == "up" else -1)
    res.update({"price": last, "refPrice": ref, "movePct": round(move * 100, 2), "rvol": round(rvol, 2)})
    if rvol < R["min_rvol"]:
        res["reason"] = f"volume only {rvol:.1f}x normal (need {R['min_rvol']}x)"
    elif move < R["min_move_pct"]:
        res["reason"] = f"price hasn't moved the expected way yet ({move:+.2%})"
    elif move > R["max_move_pct"]:
        res["reason"] = f"already moved {move:+.2%}, too late (max {R['max_move_pct']:.0%})"
    else:
        res["passed"] = True
        res["reason"] = f"volume {rvol:.1f}x normal, price {move:+.2%} since the news"
    return res
