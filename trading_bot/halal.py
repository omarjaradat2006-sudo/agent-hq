"""Basic Shariah screen, in code. An approximation, not a scholar's ruling.

For each candidate stock:
  1. named blocklist (weapons of mass harm, alcohol, pork, gambling, adult, interest-based)
  2. business screen from the SEC industry (SIC) code
  3. debt screen: total interest-bearing debt / market value < 33% (AAOIFI-style), from SEC filings
A stock is only tradable if it passes all three. If a check can't be verified, it FAILS (strict).
Shariah ETFs are screened by their index provider, so only the blocklist applies to them.
Crypto: only the major coins in config.CRYPTO_ALLOWED; lending tokens blocked; meme coins watch-only.
"""
import os, re, time
from datetime import timedelta
from . import config as C
from .util import http, HttpError, read_json, write_json, iso, now_utc, parse_time, DATA, log, event

UNIVERSE_FILE = DATA / "universe.json"
# The SEC blocks (HTTP 403 "undeclared automated tool") any User-Agent without a contact email address:
# https://www.sec.gov/os/accessing-edgar-data  ->  "Company Name AdminContact@domain.com".
# Default = the public GitHub noreply address of the repo owner (not a personal inbox). Override with SEC_USER_AGENT.
SEC_UA_DEFAULT = "AgentHQ PaperTradingBot omarjaradat2006-sudo@users.noreply.github.com"
RETRY_MINUTES = 60      # if the SEC is down, try again hourly (not every 5-minute cycle)


def sec_ua():
    return os.environ.get("SEC_USER_AGENT") or SEC_UA_DEFAULT
DEBT_TAGS = ["LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtCurrent", "DebtCurrent",
             "ShortTermBorrowings", "CommercialPaper", "LongTermDebtAndCapitalLeaseObligations",
             "OperatingLeaseLiability", "FinanceLeaseLiability"]


def sic_reason(sic):
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return None
    for lo, hi, why in C.SIC_EXCLUDED:
        if lo <= s <= hi:
            return why
    return None


def _sec(url):
    time.sleep(0.15)   # SEC asks for <= 10 requests/second
    return http("GET", url, headers={"User-Agent": sec_ua(), "Accept": "application/json",
                                     "Accept-Encoding": "identity", "Host": url.split("/")[2]}, timeout=40)


def _latest(facts, tag, unit="USD"):
    """Most recent reported value of a us-gaap tag (from 10-K/10-Q)."""
    node = (facts.get("facts", {}).get("us-gaap", {}).get(tag) or {}).get("units", {}).get(unit) or []
    rows = [r for r in node if r.get("form") in ("10-K", "10-Q", "20-F", "40-F") and r.get("end")]
    if not rows:
        return None, None
    r = max(rows, key=lambda r: (r["end"], r.get("filed", "")))
    return float(r["val"]), r["end"]


def total_debt(facts):
    """Sum the latest debt figures that belong to the same reporting date."""
    vals = {t: _latest(facts, t) for t in DEBT_TAGS}
    dated = [(v, d) for v, d in vals.values() if v is not None]
    if not dated:
        return None
    latest = max(d for _, d in dated)
    got = {t: v for t, (v, d) in vals.items() if v is not None and d == latest}
    # Avoid double counting: prefer the combined tag when present.
    if "LongTermDebt" in got:
        got.pop("LongTermDebtNoncurrent", None); got.pop("LongTermDebtCurrent", None)
    if "LongTermDebtAndCapitalLeaseObligations" in got:
        got.pop("LongTermDebt", None); got.pop("LongTermDebtNoncurrent", None)
    got.pop("OperatingLeaseLiability", None)   # operating leases aren't interest-bearing loans for most screens
    return sum(got.values())


def shares_out(facts):
    node = (facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding") or {}).get("units", {}).get("shares") or []
    if not node:
        v, _ = _latest(facts, "WeightedAverageNumberOfDilutedSharesOutstanding", "shares")
        return v
    return float(max(node, key=lambda r: (r.get("end", ""), r.get("filed", "")))["val"])


def screen_stock(sym, cik_map, price):
    """Returns (passed: bool, reason: str, detail: dict)."""
    if sym in C.BLOCKLIST:
        return False, C.BLOCKLIST[sym], {}
    if sym in C.CONVENTIONAL_DEFENSE and not C.HALAL["allow_conventional_defense"]:
        return False, "defense (switched off in settings)", {}
    if sym in C.SHARIAH_ETFS:
        return True, "Shariah-index ETF", {}
    cik = cik_map.get(sym) or cik_map.get(sym.replace(".", "-"))
    if not cik:
        return False, "not found in SEC filings (can't verify)", {}
    sub = _sec(f"https://data.sec.gov/submissions/CIK{cik:010d}.json")
    why = sic_reason(sub.get("sic"))
    if why:
        return False, f"business screen: {why}", {"sic": sub.get("sic")}
    facts = _sec(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")
    debt, shares = total_debt(facts), shares_out(facts)
    if debt is None or not shares or not price:
        return False, "debt ratio can't be verified", {"sic": sub.get("sic")}
    mcap = shares * price
    ratio = debt / mcap
    detail = {"sic": sub.get("sic"), "industry": sub.get("sicDescription"), "debtToMarketCap": round(ratio, 3)}
    if ratio >= C.HALAL["max_debt_to_market_cap"]:
        return False, f"debt is {ratio:.0%} of market value (limit 33%)", detail
    return True, f"passes (debt {ratio:.0%} of market value)", detail


def _short(e):
    """HttpError text without the HTML page the SEC sends back."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>|<!DOCTYPE.*", "", str(e).split(": <")[0])).strip()[:160]


def no_sec_fallback(alpaca):
    """What can be traded without the SEC: Shariah-index ETFs (screened by their index) + the major coins."""
    stocks = {}
    for s in sorted(C.SHARIAH_ETFS):
        try:
            a = alpaca.asset(s)
            if a and a.get("tradable") and a.get("status") == "active" and s not in C.BLOCKLIST:
                stocks[s] = {"theme": "shariah_etfs", "why": "Shariah-index ETF"}
        except HttpError:
            pass
    return stocks


def crypto_list(alpaca):
    crypto = {}
    for c in C.CRYPTO_ALLOWED:
        try:
            a = alpaca.asset(c)
            if a and a.get("tradable"):
                crypto[c] = {"theme": "crypto", "why": "major established coin"}
        except HttpError:
            pass
    return crypto


def build_universe(alpaca, force=False):
    """Weekly: screen every candidate, keep only what passes and Alpaca can trade.
    If the SEC can't be reached, the coins and Shariah ETFs still trade (they don't need SEC data),
    company stocks stay blocked (strict: unverified = not halal), and the screen retries every hour."""
    old = read_json(UNIVERSE_FILE, {}) or {}
    age = (now_utc() - parse_time(old["builtAt"])).days if old.get("builtAt") else 999
    if not force and old.get("stocks") is not None:
        if old.get("partial"):
            if now_utc() < (parse_time(old.get("retryAt")) or now_utc()):
                return old
        elif age < 7 and old.get("stocks"):
            return old
    log("Re-running the weekly halal screen", "Halal Screener")
    try:
        tick = _sec("https://www.sec.gov/files/company_tickers.json")
        cik_map = {v["ticker"].upper(): int(v["cik_str"]) for v in tick.values()}
    except HttpError as e:
        msg = _short(e)
        event("error", "sec_unreachable", msg)
        if old.get("stocks") and not old.get("partial"):
            log(f"SEC unreachable ({msg}); keeping last week's list, retrying in an hour", "Halal Screener")
            old["retryNote"] = msg
            return old
        uni = {"builtAt": old.get("builtAt"), "partial": True, "retryAt": iso(now_utc() + timedelta(minutes=RETRY_MINUTES)),
               "problem": f"SEC unreachable: {msg}", "stocks": no_sec_fallback(alpaca), "crypto": crypto_list(alpaca),
               "rejected": {}, "note": "SEC data missing: only coins + Shariah ETFs are tradable until the screen completes."}
        write_json(UNIVERSE_FILE, uni)
        log(f"SEC unreachable ({msg}). Trading only {len(uni['crypto'])} coins + {len(uni['stocks'])} Shariah ETFs "
            f"until it works; retrying in {RETRY_MINUTES} min", "Halal Screener")
        return uni
    theme_of = {s: th for th, syms in C.THEMES.items() for s in syms}
    cands = sorted(theme_of)
    prices = {}
    for i in range(0, len(cands), 50):
        chunk = cands[i:i + 50]
        try:
            r = alpaca.get("/v2/stocks/trades/latest", {"symbols": ",".join(chunk), "feed": "iex"}, data=True) or {}
            prices.update({s: float(t["p"]) for s, t in (r.get("trades") or {}).items()})
        except HttpError as e:
            log(f"price lookup failed: {e}", "Halal Screener")
    stocks, rejected = {}, {}
    for s in cands:
        try:
            a = alpaca.asset(s)
            if not a or not a.get("tradable") or a.get("status") != "active":
                rejected[s] = "not tradable on Alpaca"
                continue
            ok, why, detail = screen_stock(s, cik_map, prices.get(s))
        except HttpError as e:
            ok, why, detail = False, f"check failed ({e.code})", {}
        (stocks if ok else rejected)[s] = {"theme": theme_of[s], "why": why, **detail} if ok else why
    crypto = crypto_list(alpaca)
    uni = {"builtAt": iso(), "stocks": stocks, "crypto": crypto, "rejected": rejected,
           "note": "Basic screen: business type (SEC industry code) + debt under 33% of market value + blocklist. Not a fatwa."}
    checked = [v for v in rejected.values() if not str(v).startswith(("check failed", "not tradable"))]
    if not checked and not [s for s in stocks if s not in C.SHARIAH_ETFS]:
        # every SEC lookup failed: treat like "SEC unreachable" instead of saving an empty list for a week
        uni.update({"builtAt": old.get("builtAt"), "partial": True, "retryAt": iso(now_utc() + timedelta(minutes=RETRY_MINUTES)),
                    "problem": "every SEC lookup failed"})
        if old.get("stocks") and not old.get("partial"):
            return old
        write_json(UNIVERSE_FILE, uni)
        log("Every SEC lookup failed; coins + Shariah ETFs only, retrying in an hour", "Halal Screener")
        event("error", "sec_lookups_failed", "every SEC lookup failed")
        return uni
    write_json(UNIVERSE_FILE, uni)
    log(f"Halal screen done: {len(stocks)} stocks + {len(crypto)} coins pass, {len(rejected)} rejected", "Halal Screener")
    return uni


def allowed(sym, universe):
    """Final gate before any order. Crypto meme coins and anything unscreened -> False."""
    if sym.split("/")[0] in C.MEME_COINS or sym in C.CRYPTO_BLOCKED or sym == C.BENCHMARK:
        return False
    if "/" in sym:
        return sym in (universe.get("crypto") or {})
    return sym in (universe.get("stocks") or {}) and sym not in C.BLOCKLIST
