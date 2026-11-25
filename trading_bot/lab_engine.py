"""Research Lab test engine: turns a trading idea into exact rules and replays them on real daily prices.

A rule is a small JSON recipe (the Lab's Gemini reader writes these from videos, books and papers):
  {"name": "...", "universe": "stocks|crypto|both", "max_positions": 5, "regime": "none|spy_above_200|spy_above_50",
   "entry": [ {"f": "close_above_sma", "n": 50}, ... ],          # ALL must be true at a day's close
   "rank": "momentum_126|momentum_63|rsi_low|volume_surge",       # which candidates first when slots are short
   "exit": {"stop_pct": 8, "trail_pct": null, "atr_stop": null, "target_pct": null,
            "exit_below_sma": null, "max_days": null}}
Long only, cash only (halal: no shorting, no margin). Decide on a close, buy at the NEXT open (no peeking),
stops fill at the stop or a worse opening gap, 0.05% cost per side.
"""
import json, hashlib, math

CONDITIONS = {
    "close_above_sma": {"n": (5, 300)},
    "close_below_sma": {"n": (5, 300)},
    "sma_above_sma": {"a": (5, 300), "b": (10, 400)},
    "return_above": {"days": (2, 260), "pct": (-50, 200)},
    "return_below": {"days": (2, 260), "pct": (-80, 50)},
    "near_high": {"days": (20, 260), "within_pct": (0.5, 40)},
    "breakout": {"days": (5, 260)},
    "rsi_below": {"n": (2, 30), "value": (5, 60)},
    "rsi_above": {"n": (2, 30), "value": (40, 95)},
    "pullback_to_sma": {"n": (5, 200), "within_pct": (0.5, 10)},
    "volume_surge": {"days": (10, 100), "mult": (1.1, 10)},
    "gap_up": {"pct": (0.5, 30)},
    "down_days": {"n": (2, 10)},
    "volatility_contraction": {"short": (3, 30), "long": (20, 120), "ratio": (0.2, 0.95)},
    "top_momentum": {"days": (20, 260), "top": (1, 30)},
}
EXITS = {"stop_pct": (0.5, 50), "trail_pct": (0.5, 50), "atr_stop": (0.5, 6), "target_pct": (1, 500),
         "exit_below_sma": (5, 300), "max_days": (1, 400)}
RANKS = ("momentum_126", "momentum_63", "momentum_252", "rsi_low", "volume_surge")
REGIMES = ("none", "spy_above_200", "spy_above_50")
COST = 0.0005
BENCH = "SPY"


def validate(rule):
    """Clean a rule from Gemini: unknown conditions dropped, numbers clamped. Returns the rule or None."""
    if not isinstance(rule, dict):
        return None
    ent = []
    for c in rule.get("entry") or []:
        if not isinstance(c, dict) or c.get("f") not in CONDITIONS:
            continue
        spec, out = CONDITIONS[c["f"]], {"f": c["f"]}
        try:
            for k, (lo, hi) in spec.items():
                v = float(c[k])
                out[k] = max(lo, min(hi, v))
                if k in ("n", "a", "b", "days", "short", "long", "top"):
                    out[k] = int(round(out[k]))
        except (KeyError, TypeError, ValueError):
            continue
        ent.append(out)
    if not ent:
        return None
    ex = {}
    for k, (lo, hi) in EXITS.items():
        v = (rule.get("exit") or {}).get(k)
        try:
            if v is not None:
                ex[k] = max(lo, min(hi, float(v)))
                if k in ("exit_below_sma", "max_days"):
                    ex[k] = int(round(ex[k]))
        except (TypeError, ValueError):
            pass
    if not any(k in ex for k in ("stop_pct", "trail_pct", "atr_stop", "exit_below_sma", "max_days", "target_pct")):
        ex["max_days"] = 20                      # every rule needs a way out
    uni = rule.get("universe") if rule.get("universe") in ("stocks", "crypto", "both") else "stocks"
    try:
        mp = int(max(1, min(20, float(rule.get("max_positions") or 5))))
    except (TypeError, ValueError):
        mp = 5
    return {"name": str(rule.get("name") or "unnamed")[:80], "universe": uni, "max_positions": mp,
            "regime": rule.get("regime") if rule.get("regime") in REGIMES else "none",
            "entry": ent, "rank": rule.get("rank") if rule.get("rank") in RANKS else "momentum_126", "exit": ex}


def rule_id(rule):
    core = {k: rule[k] for k in ("universe", "max_positions", "regime", "entry", "rank", "exit")}
    core["entry"] = sorted(core["entry"], key=lambda c: json.dumps(c, sort_keys=True))
    return hashlib.sha1(json.dumps(core, sort_keys=True).encode()).hexdigest()[:10]


# ---------------------------------------------------------------- indicators (cached per symbol)
class Series:
    def __init__(self, bars):
        bars = sorted(bars, key=lambda b: b["t"])
        self.d = [b["t"][:10] for b in bars]
        self.o = [float(b["o"]) for b in bars]
        self.h = [float(b["h"]) for b in bars]
        self.l = [float(b["l"]) for b in bars]
        self.c = [float(b["c"]) for b in bars]
        self.v = [float(b.get("v") or 0) for b in bars]
        self.ix = {d: i for i, d in enumerate(self.d)}
        self._cache = {}

    def _get(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def sma(self, n, src="c"):
        def f():
            xs, out, s = getattr(self, src), [], 0.0
            for i, x in enumerate(xs):
                s += x
                if i >= n:
                    s -= xs[i - n]
                out.append(s / n if i >= n - 1 else None)
            return out
        return self._get(("sma", n, src), f)

    def rsi(self, n):
        def f():
            out, ag, al = [None] * len(self.c), 0.0, 0.0
            for i in range(1, len(self.c)):
                ch = self.c[i] - self.c[i - 1]
                g, lo = max(ch, 0), max(-ch, 0)
                if i <= n:
                    ag += g / n; al += lo / n
                else:
                    ag = (ag * (n - 1) + g) / n; al = (al * (n - 1) + lo) / n
                if i >= n:
                    out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
            return out
        return self._get(("rsi", n), f)

    def atr(self, n=14):
        def f():
            tr = [self.h[0] - self.l[0]] + [max(self.h[i] - self.l[i], abs(self.h[i] - self.c[i - 1]), abs(self.l[i] - self.c[i - 1]))
                                             for i in range(1, len(self.c))]
            out, s = [], 0.0
            for i, x in enumerate(tr):
                s += x
                if i >= n:
                    s -= tr[i - n]
                out.append(s / n if i >= n - 1 else None)
            return out
        return self._get(("atr", n), f)

    def maxc(self, n):
        """Highest close of the n days BEFORE day i."""
        def f():
            from collections import deque
            out, dq = [], deque()
            for i in range(len(self.c)):
                while dq and dq[0] < i - n:
                    dq.popleft()
                out.append(self.c[dq[0]] if dq and i >= n else None)
                while dq and self.c[dq[-1]] <= self.c[i]:
                    dq.pop()
                dq.append(i)
            return out
        return self._get(("maxc", n), f)

    def stdret(self, n):
        def f():
            r = [0.0] + [self.c[i] / self.c[i - 1] - 1 if self.c[i - 1] else 0.0 for i in range(1, len(self.c))]
            out = []
            for i in range(len(r)):
                if i < n:
                    out.append(None); continue
                w = r[i - n + 1:i + 1]; m = sum(w) / n
                out.append(math.sqrt(sum((x - m) ** 2 for x in w) / max(1, n - 1)))
            return out
        return self._get(("std", n), f)

    def ret(self, i, days):
        return self.c[i] / self.c[i - days] - 1 if i >= days and self.c[i - days] else None


def cond(s, c, i, ctx):
    f = c["f"]
    if f == "close_above_sma":
        m = s.sma(c["n"])[i]; return m is not None and s.c[i] > m
    if f == "close_below_sma":
        m = s.sma(c["n"])[i]; return m is not None and s.c[i] < m
    if f == "sma_above_sma":
        a, b = s.sma(c["a"])[i], s.sma(c["b"])[i]; return a is not None and b is not None and a > b
    if f == "return_above":
        r = s.ret(i, c["days"]); return r is not None and r * 100 > c["pct"]
    if f == "return_below":
        r = s.ret(i, c["days"]); return r is not None and r * 100 < c["pct"]
    if f == "near_high":
        if i < c["days"]:
            return False
        hi = max(s.c[i - c["days"] + 1:i + 1]); return s.c[i] >= hi * (1 - c["within_pct"] / 100)
    if f == "breakout":
        m = s.maxc(c["days"])[i]; return m is not None and s.c[i] > m
    if f == "rsi_below":
        r = s.rsi(c["n"])[i]; return r is not None and r < c["value"]
    if f == "rsi_above":
        r = s.rsi(c["n"])[i]; return r is not None and r > c["value"]
    if f == "pullback_to_sma":
        m = s.sma(c["n"])[i]; return m is not None and m <= s.c[i] <= m * (1 + c["within_pct"] / 100)
    if f == "volume_surge":
        m = s.sma(c["days"], "v")[i - 1] if i else None; return bool(m) and s.v[i] > m * c["mult"]
    if f == "gap_up":
        return i > 0 and s.o[i] > s.c[i - 1] * (1 + c["pct"] / 100)
    if f == "down_days":
        return i >= c["n"] and all(s.c[j] < s.c[j - 1] for j in range(i - c["n"] + 1, i + 1))
    if f == "volatility_contraction":
        a, b = s.stdret(c["short"])[i], s.stdret(c["long"])[i]; return a is not None and b and a / b < c["ratio"]
    if f == "top_momentum":
        return s.sym in ctx.get(("top", c["days"], c["top"]), ())
    return False


def load_series(bars):
    out = {}
    for sym, bs in bars.items():
        if len(bs) >= 30:
            out[sym] = Series(bs)
            out[sym].sym = sym
    return out


def simulate(rule, data, start, end):
    """Replay one rule from date `start` to `end` (YYYY-MM-DD). data = load_series(...). Returns stats."""
    spy = data.get(BENCH)
    if not spy:
        return {"error": "no SPY"}
    dates = [d for d in spy.d if start <= d <= end]
    syms = [s for s in data if s != BENCH and (rule["universe"] == "both" or (rule["universe"] == "crypto") == ("/" in s))]
    ex, mp = rule["exit"], rule["max_positions"]
    tops = [c for c in rule["entry"] if c["f"] == "top_momentum"]
    cash, pos, trades, curve = 1.0, {}, [], []
    buys, sells = [], set()
    for d in dates:
        # 1. yesterday's decisions at today's open
        for sym in list(sells):
            p, s = pos.get(sym), data[sym]
            i = s.ix.get(d)
            if p and i is not None:
                _close(pos, trades, sym, s.o[i], d, p.get("why", "rule exit")); cash += trades[-1]["value"]
        sells = set()
        if buys:
            value = cash + sum(p["qty"] * data[k].c[p["last"]] for k, p in pos.items())
            for sym in buys:
                s = data[sym]; i = s.ix.get(d)
                if i is None or sym in pos or len(pos) >= mp:
                    continue
                spend = min(value / mp, cash)
                if spend < value * 0.01:
                    continue
                px = s.o[i]; cash -= spend
                atr = s.atr()[i - 1] if i else None
                stop = None
                if ex.get("stop_pct"):
                    stop = px * (1 - ex["stop_pct"] / 100)
                if ex.get("atr_stop") and atr:
                    st2 = px - ex["atr_stop"] * atr
                    stop = max(stop, st2) if stop else st2
                pos[sym] = {"qty": spend * (1 - COST) / px, "entry": px, "date": d, "high": px, "stop": stop,
                            "target": px * (1 + ex["target_pct"] / 100) if ex.get("target_pct") else None,
                            "last": i, "days": 0}
        buys = []
        # 2. intraday: stops / targets on today's bar
        for sym in list(pos):
            p, s = pos[sym], data[sym]
            i = s.ix.get(d)
            if i is None:
                continue
            p["last"] = i
            if p["date"] != d:
                p["days"] += 1
            stop = p["stop"]
            if ex.get("trail_pct"):
                tr = p["high"] * (1 - ex["trail_pct"] / 100)
                stop = max(stop, tr) if stop else tr
            if stop and s.l[i] <= stop:          # bought at the open, so the day's low came after the buy
                _close(pos, trades, sym, min(s.o[i], stop), d, "stop"); cash += trades[-1]["value"]; continue
            if p["target"] and s.h[i] >= p["target"]:
                _close(pos, trades, sym, max(s.o[i], p["target"]), d, "target"); cash += trades[-1]["value"]; continue
            p["high"] = max(p["high"], s.h[i])
            if ex.get("exit_below_sma"):
                m = s.sma(ex["exit_below_sma"])[i]
                if m and s.c[i] < m:
                    sells.add(sym); p["why"] = "closed under its average"
            if ex.get("max_days") and p["days"] >= ex["max_days"]:
                sells.add(sym); p["why"] = "time limit"
        value = cash + sum(p["qty"] * data[k].c[p["last"]] for k, p in pos.items())
        curve.append(value)
        # 3. today's close: new signals
        si = spy.ix[d]
        if rule["regime"] == "spy_above_200" and not cond(spy, {"f": "close_above_sma", "n": 200}, si, {}):
            continue
        if rule["regime"] == "spy_above_50" and not cond(spy, {"f": "close_above_sma", "n": 50}, si, {}):
            continue
        free = mp - len(pos) + len(sells)
        if free <= 0:
            continue
        ctx = {}
        for c in tops:
            rs = []
            for sym in syms:
                s = data[sym]; i = s.ix.get(d)
                r = s.ret(i, c["days"]) if i is not None else None
                if r is not None:
                    rs.append((r, sym))
            ctx[("top", c["days"], c["top"])] = {x for _, x in sorted(rs, reverse=True)[:c["top"]]}
        cands = []
        for sym in syms:
            if sym in pos:
                continue
            s = data[sym]; i = s.ix.get(d)
            if i is None or i < 20:
                continue
            if all(cond(s, c, i, ctx) for c in rule["entry"]):
                cands.append((_rank(rule["rank"], s, i), sym))
        buys = [sym for _, sym in sorted(cands, reverse=True)[:free]]
    for sym in list(pos):                         # mark open positions at the last close
        s = data[sym]; p = pos[sym]
        _close(pos, trades, sym, s.c[p["last"]], dates[-1] if dates else end, "still open"); cash += trades[-1]["value"]
    return stats(curve, trades, spy, dates)


def _rank(how, s, i):
    if how.startswith("momentum_"):
        return s.ret(i, int(how.split("_")[1])) or -9
    if how == "rsi_low":
        r = s.rsi(14)[i]; return -(r if r is not None else 50)
    if how == "volume_surge":
        m = s.sma(50, "v")[i]; return s.v[i] / m if m else 0
    return 0


def _close(pos, trades, sym, px, d, why):
    p = pos.pop(sym)
    trades.append({"symbol": sym, "in": p["date"], "out": d, "pct": round((px / p["entry"] - 1) * 100, 2),
                   "why": why, "value": p["qty"] * px * (1 - COST)})


def max_dd(xs):
    peak, dd = 0, 0
    for v in xs:
        peak = max(peak, v); dd = min(dd, v / peak - 1 if peak else 0)
    return dd


def stats(curve, trades, spy, dates):
    if not curve:
        return {"error": "no days"}
    real = [t for t in trades if t["why"] != "still open"] or trades
    wins = [t for t in real if t["pct"] > 0]
    gains = sum(t["pct"] for t in wins); losses = -sum(t["pct"] for t in real if t["pct"] <= 0)
    sc = [spy.c[spy.ix[d]] for d in dates]
    xs = [t["pct"] for t in real]
    if len(xs) > 2:
        m = sum(xs) / len(xs); sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
        tstat = round(m / (sd / math.sqrt(len(xs))), 2) if sd else 0.0
    else:
        tstat = 0.0
    ret, dd = curve[-1] - 1, max_dd(curve)
    sret, sdd = sc[-1] / sc[0] - 1, max_dd(sc)
    return {"returnPct": round(ret * 100, 2), "maxDrawdownPct": round(dd * 100, 2), "trades": len(real),
            "winRatePct": round(len(wins) / len(real) * 100, 1) if real else None,
            "avgWinPct": round(gains / len(wins), 2) if wins else None,
            "avgLossPct": round(-losses / (len(real) - len(wins)), 2) if len(real) > len(wins) else None,
            "profitFactor": round(gains / losses, 2) if losses else (99.0 if gains else None),
            "tStat": tstat, "spyReturnPct": round(sret * 100, 2), "spyMaxDrawdownPct": round(sdd * 100, 2),
            "mar": round(ret / abs(dd), 2) if dd else round(ret * 10, 2),
            "spyMar": round(sret / abs(sdd), 2) if sdd else round(sret * 10, 2)}


def periods(data, years=3):
    """Full test window, its three thirds, and the most recent 60 trading days (the current drop)."""
    d = data[BENCH].d
    first = max(0, len(d) - int(years * 252))
    first = max(first, 200) if len(d) > 400 else min(first, len(d) - 1)
    full = d[first:]
    n = len(full) // 3
    out = {"full": (full[0], full[-1])}
    for k in range(3):
        seg = full[k * n:(k + 1) * n] if k < 2 else full[2 * n:]
        if seg:
            out[f"part{k + 1}"] = (seg[0], seg[-1])
    out["last60"] = (full[-60] if len(full) > 60 else full[0], full[-1])
    return out


def evaluate(rule, data, years=3):
    """Test a rule on every period and give a verdict: passed / promising / failed."""
    res = {name: simulate(rule, data, a, b) for name, (a, b) in periods(data, years).items()}
    f = res["full"]
    if f.get("error"):
        return {"verdict": "failed", "why": f["error"], "periods": res}
    parts_pos = sum(1 for k in ("part1", "part2", "part3") if (res.get(k) or {}).get("returnPct", -1) > 0)
    pf = f.get("profitFactor") or 0
    # tStat: is the average trade clearly above zero, or could it be luck? The lab tests hundreds of rules, so the bar is 2.5
    ok = f["returnPct"] > 0 and pf > 1.1 and parts_pos >= 2 and f["mar"] >= 0.8 * max(f["spyMar"], 0.3)
    if ok and f["trades"] >= 20 and f.get("tStat", 0) >= 2.5:
        v, why = "passed", "made money in most periods, beat holding SPY for the risk, and too consistent to be luck"
    elif f["returnPct"] > 0 and pf > 1.0 and parts_pos >= 2 and f.get("tStat", 0) >= 1:
        v, why = "promising", ("too few trades to trust yet" if f["trades"] < 20 else
                               "made money, but could still be luck or not better than holding SPY for the risk")
    else:
        v, why = "failed", "lost money or only worked in one period"
    return {"verdict": v, "why": why, "score": round(f["mar"] + 0.2 * parts_pos + (0.3 if v == "passed" else 0), 3),
            "periods": res}


def neighbours(rule):
    """Small changes to each number (half and one-and-a-half times). A real edge survives them; a lucky fit doesn't."""
    out = []
    for i, c in enumerate(rule["entry"]):
        for k, v in c.items():
            if k == "f":
                continue
            for m in (0.6, 1.5):
                r = json.loads(json.dumps(rule)); r["entry"][i][k] = v * m
                r = validate(r)
                if r:
                    out.append(r)
    for k, v in rule["exit"].items():
        for m in (0.6, 1.5):
            r = json.loads(json.dumps(rule)); r["exit"][k] = v * m
            r = validate(r)
            if r:
                out.append(r)
    return out[:12]


def robustness(rule, data, years=3):
    """Share of nearby versions that still make money and beat the SPY risk ratio (1.0 = very robust)."""
    ns = neighbours(rule)
    if not ns:
        return None
    full = periods(data, years)["full"]
    good = 0
    for r in ns:
        st = simulate(r, data, *full)
        if not st.get("error") and st["returnPct"] > 0 and st["mar"] >= 0.8 * max(st["spyMar"], 0.3):
            good += 1
    return round(good / len(ns), 2)
