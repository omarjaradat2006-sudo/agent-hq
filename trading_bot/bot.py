"""Agent HQ paper-trading bot: news -> Gemini triage -> 2-source + price/volume confirmation
-> TradingAgents approval -> hard risk rules -> Alpaca PAPER order with the stop-loss on Alpaca's side.

    python -m trading_bot.bot run        keep running (laptop / server)
    python -m trading_bot.bot once       one cycle, then exit
    python -m trading_bot.bot check      test keys and connections, trade nothing
    python -m trading_bot.bot universe   re-run the halal screen now
    python -m trading_bot.bot publish    save results to GitHub now
    python -m trading_bot.bot unlock     clear the 10% kill switch (after you've reviewed)
"""
import sys, time, traceback
from datetime import timedelta
from . import config as C
from .util import (load_env, read_json, write_json, iso, now_utc, now_et, parse_time, log, event, DATA, LOCAL,
                   SingleInstance, HttpError, round_price)

LEDGER = DATA / "ledger.json"          # committed: start equity, kill switch, every trade, equity curve
STATE = LOCAL / "state.json"           # private working memory: seen news, events, counters


class Bot:
    def __init__(self):
        from .alpaca import Alpaca
        self.a = Alpaca()
        self.ledger = read_json(LEDGER, {}) or {}
        self.s = read_json(STATE, {}) or {}
        self.ledger.setdefault("trades", [])
        self.ledger.setdefault("equity", [])
        self.ledger.setdefault("decisions", [])
        self.s.setdefault("events", {})
        self.s.setdefault("decided", {})
        self.universe = {}

    # ------------------------------------------------------------ helpers
    def save(self):
        write_json(STATE, self.s)
        write_json(LEDGER, self.ledger)

    def open_trades(self):
        return [t for t in self.ledger["trades"] if t["status"] in ("open", "pending")]

    def decide(self, key, sym, outcome, why, event=None, final=True):
        if final:
            self.s["decided"][key] = outcome
        d = {"t": iso(), "symbol": sym, "outcome": outcome, "why": why}
        if event:
            d["event"] = event["summary"]
        last = self.ledger["decisions"][0] if self.ledger["decisions"] else {}
        if (last.get("symbol"), last.get("outcome"), last.get("why")) != (sym, outcome, why):
            self.ledger["decisions"].insert(0, d)
            del self.ledger["decisions"][150:]
            from . import coach
            coach.log_decision(d)

    def today_count(self, name):
        day = now_et().date().isoformat()
        c = self.s.setdefault("counters", {})
        if c.get("day") != day:
            self.s["counters"] = c = {"day": day}
        return c, c.get(name, 0)

    # ------------------------------------------------------------ cycle
    def cycle(self, social=False):
        from . import halal, news, triage, watch, risk
        acct, clock = self.a.account(), self.a.clock()
        positions = self.a.positions()
        eq = float(acct["equity"])
        if not self.ledger.get("startEquity"):
            spy = self.a.latest_price(C.BENCHMARK)
            self.ledger.update({"startEquity": eq, "startedAt": iso(), "spyStart": spy})
            log(f"First run. Paper account starts at ${eq:,.2f}; SPY at {spy}", "Risk Officer")

        # 1. kill switch / daily halt
        if not self.ledger.get("killed") and risk.kill_switch_hit(acct, self.ledger["startEquity"]):
            self.kill(acct)
        if risk.daily_halt_hit(acct) and self.s.get("haltedDate") != now_et().date().isoformat():
            self.s["haltedDate"] = now_et().date().isoformat()
            log(f"Down {risk.day_change(acct):.1%} today: no new trades until tomorrow", "Risk Officer")
            event("risk", "daily_loss_halt", f"down {risk.day_change(acct):.2%} today: no new trades until tomorrow")

        # 2. keep the trade book in sync with Alpaca, enforce time limits + crypto target
        self.reconcile(positions)
        self.time_and_target_exits(clock)
        positions = self.a.positions()

        # 3. read the news, triage it, fold into running stories
        self.universe = halal.build_universe(self.a)
        c, _ = self.today_count("scans")
        c["scans"] = c.get("scans", 0) + 1
        c["lastScan"] = iso()
        items = news.collect(self.a, self.s, include_social=social,
                             symbols=sorted((self.universe or {}).get("stocks") or {}))
        if items:
            held = [t["symbol"] for t in self.open_trades()]
            tri = triage.triage(items, self.s["events"], self.universe, held)
            if triage.FAILED_IDS:       # Gemini was overloaded: un-see those headlines so the next scan reads them
                bad = set(triage.FAILED_IDS)
                self.s["seenNews"] = [i for i in self.s.get("seenNews") or [] if i not in bad]
            triage.merge(self.s["events"], tri, {i["id"]: i for i in items})
            n_real = sum(1 for e in tri if e.get("assets"))
            log(f"Read {len(items)} new headlines/posts, {n_real} market-moving stories", "News Scout")
            c, _ = self.today_count("headlines")
            c["headlines"] = c.get("headlines", 0) + len(items)
            c["stories"] = c.get("stories", 0) + n_real

        # 4. bad news on something we hold -> sell
        self.bad_news_exits()
        # 5. meme coins: watch only
        watch.update(self.s, self.s["events"])
        # 6. new trades
        self.market_study(clock)
        if not self.ledger.get("killed"):
            self.core_buys(acct, clock)        # budget order: core first, then the trend sleeve, then news trades
            self.trend_sleeve(acct, clock)
            self.entries(acct, clock)
            self.dip_buys(acct, clock)
        self.coach_review()
        self.track_equity(acct)
        self.save()

    def coach_review(self):
        """Once every weekday evening after the close: learn from the trades and the skipped stories."""
        now, today = now_et(), now_et().date().isoformat()
        if now.weekday() >= 5 or (now.hour, now.minute) < (16, 30) or self.s.get("coachDate") == today:
            return
        self.s["coachDate"] = today
        try:
            from . import coach
            coach.run(self.a, self.ledger)
            self.s["publishNow"] = True
        except Exception as ex:  # noqa: BLE001  never let the review stop trading
            log(f"Coach review failed: {str(ex)[:150]}", "Coach")
            event("error", "coach", ex)

    def core_buys(self, acct, clock):
        """Keep CORE_PCT of the invested budget in the halal market ETFs (SPUS, HLAL). Tops up when below 80% of
        target, at most once a day. No stop-loss or time limit: it rides the market; only the -10% kill switch sells it."""
        from . import risk
        share, today = C.core_share(), now_et().date().isoformat()
        ok, _ = risk.stock_entry_window_open(clock)
        if share <= 0 or not ok or self.s.get("coreDate") == today or risk.daily_halt_hit(acct):
            return
        etfs = [s for s in C.CORE_ETFS if s in ((self.universe or {}).get("stocks") or {})]
        if not etfs:
            return
        eq, cash = float(acct["equity"]), float(acct["cash"])
        _, cap = C.sizing()
        target = C.invest_base(eq, self.ledger.get("startEquity")) * cap * share
        have = sum((t.get("lastPrice") or t["entryPrice"]) * (t.get("qty") or 0)
                   for t in self.open_trades() if t.get("strategy") == "core")
        self.s["coreDate"] = today
        if have >= target * 0.8:
            return
        pending = sum(t["cost"] for t in self.open_trades() if t["status"] == "pending")
        need = min(target - have, cash - pending, base_room := C.invest_base(eq, self.ledger.get("startEquity")) * cap - (eq - cash) - pending)
        if base_room < 50:
            log("Core holding: no room left in the invested budget today", "Trader")
            return
        if need < 50:
            return
        log(f"Core holding: putting ${need:,.0f} into {', '.join(etfs)} (target ${target:,.0f} = {share:.0%} of the budget)", "Trader")
        for sym in etfs:
            price = self.a.latest_price(sym)
            qty = int((need / len(etfs)) // price) if price else 0
            if qty < 1:
                continue
            tid = f"ahq-core-{sym}-{now_utc():%Y%m%d%H%M%S}"
            try:
                o = self.a.buy_stock(sym, qty, tid)
            except HttpError as err:
                event("error", "order_failed", err, sym)
                continue
            self.ledger["trades"].insert(0, {
                "id": tid, "symbol": sym, "asset": "stock", "status": "pending", "strategy": "core",
                "entryOrderId": o["id"], "qty": qty, "cost": round(qty * price, 2), "estPrice": price, "entryPrice": price,
                "stop": round_price(price * 0.9), "target": round_price(price * 1.5), "openedAt": iso(),
                "news": {"summary": "Core holding: rides the whole (halal) market", "category": "core", "sources": []},
                "reason": {"triage": "core holding", "confidence": None, "confirmation": f"{share:.0%} of the budget",
                           "publishers": [], "tradingAgents": "not used (core)"}})
            self.decide(f"core|{today}|{sym}", sym, "bought", "core holding: rides the market")
        self.s["publishNow"] = True

    def market_study(self, clock):
        """Once a day (after the open): rank every halal stock + coin on trend, momentum and quality (study.py)."""
        from . import study
        today = now_et().date().isoformat()
        if self.s.get("studyDate") == today or now_et().hour < 9 or (now_et().hour == 9 and now_et().minute < 35):
            return
        self.s["studyDate"] = today
        try:
            self.study = study.build(self.a, self.universe or {})
        except Exception as ex:                       # the study must never stop the bot
            event("error", "market_study", ex)
            log(f"Market study failed: {ex}", "Market Study")

    def _sleeve(self, strategy):
        return sum((t.get("lastPrice") or t["entryPrice"]) * (t.get("qty") or 0) if t.get("qty") else t["cost"]
                   for t in self.open_trades() if t.get("strategy") == strategy)

    def reserved(self, acct):
        """Money news trades must leave alone: the unfilled part of the core holding + the trend picks."""
        from . import study
        eq = float(acct["equity"])
        _, cap = C.sizing()
        budget = C.invest_base(eq, self.ledger.get("startEquity")) * cap
        core = max(0.0, budget * C.core_share() - self._sleeve("core"))
        tr = 0.0
        if C.trend_share() > 0:
            st = study.load()
            held = {t["symbol"] for t in self.open_trades()}
            want = [x for x in (st.get("picks") or {}).get("stocks", []) if (st.get("regime") or {}).get("stocks")] + \
                   [x for x in (st.get("picks") or {}).get("coins", []) if (st.get("regime") or {}).get("coins")]
            slot = budget * C.trend_share() / (C.TREND["stocks"] + C.TREND["coins"])
            tr = min(slot * len([x for x in want if x not in held]), max(0.0, budget * C.trend_share() - self._sleeve("trend")))
        return core + tr

    def trend_sleeve(self, acct, clock):
        """Trend sleeve (TREND_PCT of the invested budget, off by default). Once a day in the stock window:
        sell holdings whose trend broke or that fell out of the top list, then buy today's top picks.
        Each stock gets a wide Alpaca trailing stop; coins get a stop the bot raises. No time limit."""
        from . import risk, study, halal
        share, today = C.trend_share(), now_et().date().isoformat()
        ok, _ = risk.stock_entry_window_open(clock)
        if share <= 0 or not ok or self.s.get("trendDate") == today:
            return
        st = study.load()
        if st.get("date") != today:
            return                                    # wait for today's study
        self.s["trendDate"] = today
        n = C.TREND["stocks"] + C.TREND["coins"]
        ranked = st.get("ranked") or []
        keep = set((st.get("picks") or {}).get("stocks", []) + (st.get("picks") or {}).get("coins", [])) | \
            {c["symbol"] for c in ranked[:2 * n] if c.get("uptrend")}
        by = {c["symbol"]: c for c in ranked}
        for t in [t for t in self.open_trades() if t.get("strategy") == "trend" and t["status"] == "open"]:
            c = by.get(t["symbol"])
            if c and c["price"] < c["ma50"]:
                self.close(t, "trend broke: closed under its 50-day average")
            elif t["symbol"] not in keep:
                self.close(t, "dropped out of the Market Study top list")
        if risk.daily_halt_hit(acct):
            return
        reg = st.get("regime") or {}
        want = ((st.get("picks") or {}).get("stocks", []) if reg.get("stocks") else []) + \
               ((st.get("picks") or {}).get("coins", []) if reg.get("coins") else [])
        eq, cash = float(acct["equity"]), float(acct["cash"])
        _, cap = C.sizing()
        budget = C.invest_base(eq, self.ledger.get("startEquity")) * cap
        slot = budget * share / n
        held = {t["symbol"].replace("/", "") for t in self.open_trades()} | {p["symbol"] for p in self.a.positions()}
        trail = C.TREND["trail_pct"]
        for sym in want:
            if sym.replace("/", "") in held or not halal.allowed(sym, self.universe or {}):
                continue
            pending = sum(t["cost"] for t in self.open_trades() if t["status"] == "pending")
            room = min(budget * share - self._sleeve("trend"), budget - (eq - cash) - pending, cash - pending)
            spend = min(slot, room)
            if spend < 50:
                log("Trend sleeve: no room left in the budget today", "Market Study")
                break
            price = self.a.latest_price(sym)
            if not price:
                continue
            tid = f"ahq-trend-{sym.replace('/', '')}-{now_utc():%Y%m%d%H%M%S}"
            try:
                if "/" in sym:
                    o, qty, cost = self.a.buy_crypto(sym, round(spend, 2), tid), None, spend
                else:
                    qty = int(spend // price)
                    if qty < 1:
                        continue
                    o, cost = self.a.buy_stock(sym, qty, tid), qty * price
            except HttpError as err:
                event("error", "order_failed", err, sym)
                continue
            c = by.get(sym) or {}
            why = f"Market Study pick: score {c.get('score')}, 6-month {c.get('r6')}%, above its 50/200-day averages"
            self.ledger["trades"].insert(0, {
                "id": tid, "symbol": sym, "asset": "crypto" if "/" in sym else "stock", "status": "pending",
                "strategy": "trend", "entryOrderId": o["id"], "qty": qty, "cost": round(cost, 2), "estPrice": price,
                "entryPrice": price, "stop": round_price(price * (1 - trail / 100)), "target": round_price(price * 100),
                "trail": trail, "openedAt": iso(),
                "news": {"summary": why, "category": "trend", "sources": []},
                "reason": {"triage": "market study (trend + momentum + quality)", "confidence": None,
                           "confirmation": why, "publishers": [], "tradingAgents": "not used (trend)"}})
            held.add(sym.replace("/", ""))
            self.decide(f"trend|{today}|{sym}", sym, "bought", why)
            log(f"Trend sleeve BUY {sym} ${cost:,.0f}: {why}", "Market Study")

    def dip_buys(self, acct, clock):
        """Market down 1.5%+ today -> buy the halal Shariah ETFs with part of the budget, hold for days."""
        from . import risk
        D, today = C.DIP, now_et().date().isoformat()
        ok, _ = risk.stock_entry_window_open(clock)
        if not ok or self.s.get("dipDate") == today or risk.daily_halt_hit(acct):
            return
        try:
            bars = self.a.stock_bars([C.BENCHMARK], "1Day", iso(now_utc() - timedelta(days=8))).get(C.BENCHMARK) or []
            prev = [b for b in bars if parse_time(b["t"]).astimezone(now_et().tzinfo).date().isoformat() < today]
            spy = self.a.latest_price(C.BENCHMARK)
            chg = (spy - float(prev[-1]["c"])) / float(prev[-1]["c"]) if prev and spy else 0.0
        except (HttpError, KeyError, ValueError, TypeError):
            return
        if chg > -D["spy_drop_pct"]:
            return
        held = {t["symbol"] for t in self.open_trades()}
        etfs = [s for s in sorted((self.universe or {}).get("stocks") or {}) if s in C.SHARIAH_ETFS and s not in held]
        self.s["dipDate"] = today
        if not etfs:
            return
        eq, cash = float(acct["equity"]), float(acct["cash"])
        per, cap = C.sizing()
        base = C.invest_base(eq, self.ledger.get("startEquity"))
        pending = sum(t["cost"] for t in self.open_trades() if t["status"] == "pending")
        room = min(base * cap - (eq - cash) - pending, base * cap * D["budget_share"], cash - pending)
        if room < 50:
            log(f"Market down {chg:.1%} today, but no room left in the budget for dip buys", "Trader")
            return
        log(f"Market down {chg:.1%} today: buying the dip in {', '.join(etfs)}", "Trader")
        event("info", "dip_buy", f"SPY {chg:+.2%} today, buying {', '.join(etfs)}")
        for sym in etfs:
            price = self.a.latest_price(sym)
            qty = int((room / len(etfs)) // price) if price else 0
            if qty < 1:
                continue
            stop, target = price * (1 - D["stop_pct"]), price * (1 + D["target_pct"])
            tid = f"ahq-dip-{sym}-{now_utc():%Y%m%d%H%M%S}"
            try:
                o = self.a.buy_stock_bracket(sym, qty, round(stop, 2), round(target, 2), tid)
            except HttpError as err:
                event("error", "order_failed", err, sym)
                continue
            self.ledger["trades"].insert(0, {
                "id": tid, "symbol": sym, "asset": "stock", "status": "pending", "strategy": "dip",
                "entryOrderId": o["id"], "qty": qty, "cost": round(qty * price, 2), "estPrice": price,
                "entryPrice": price, "stop": round_price(stop), "target": round_price(target), "openedAt": iso(),
                "news": {"summary": f"Buy the dip: the whole market (SPY) was {chg:+.2%} today", "category": "dip", "sources": []},
                "reason": {"triage": "market-wide dip", "confidence": None, "confirmation": f"SPY {chg:+.2%}",
                           "publishers": [], "tradingAgents": "not used (dip buy)"}})
            self.decide(f"dip|{today}|{sym}", sym, "bought", f"buy the dip: SPY {chg:+.2%} today")
        self.s["publishNow"] = True

    # ------------------------------------------------------------ book keeping
    def reconcile(self, positions):
        from .alpaca import to_pos_symbol
        held = {p["symbol"]: p for p in positions}
        for t in self.open_trades():
            ps = to_pos_symbol(t["symbol"])
            try:
                entry = self.a.order(t["entryOrderId"])
            except HttpError as e:
                log(f"can't read order for {t['symbol']}: {e}", "Trader")
                event("error", "read_order", e, t["symbol"])
                continue
            if t["status"] == "pending":
                if entry.get("status") == "filled":
                    t["status"], t["entryPrice"] = "open", float(entry["filled_avg_price"])
                    t["qty"] = float(entry["filled_qty"])
                    if t["asset"] == "stock":
                        for leg in entry.get("legs") or []:
                            if leg.get("type") == "limit":
                                t["target"] = float(leg["limit_price"])
                            elif leg.get("type") in ("stop", "stop_limit"):
                                t["stop"] = float(leg["stop_price"])
                    else:
                        t["stop"] = round_price(t["entryPrice"] * (1 - C.RISK["stop_loss_pct"]))
                        t["target"] = round_price(t["entryPrice"] * (1 + C.RISK["take_profit_pct"]))
                    log(f"Bought {t['qty']:g} {t['symbol']} at ${t['entryPrice']:,.2f} (stop ${t['stop']:,.2f}, target ${t['target']:,.2f})")
                elif entry.get("status") in ("canceled", "expired", "rejected"):
                    t.update({"status": "cancelled", "closedAt": iso(), "exitReason": f"entry {entry.get('status')}"})
                    event("error", "entry_order_" + str(entry.get("status")), "Alpaca did not fill the buy", t["symbol"])
                    continue
                else:
                    continue
            # stocks with a trailing stop: put it on Alpaca's side as soon as the shares are in the account
            if t["asset"] == "stock" and t.get("trail") and not t.get("stopOrderId") and ps in held:
                qty = int(float(held[ps].get("qty_available") or held[ps]["qty"]))
                try:
                    o = self.a.trailing_stop(t["symbol"], qty, t["trail"], f"{t['id']}-trail")
                    t["stopOrderId"], t["qty"] = o["id"], qty
                    t["target"] = None
                    log(f"Trailing stop for {t['symbol']} placed on Alpaca: sells if it falls {t['trail']:g}% from its high", "Risk Officer")
                except HttpError as ex:
                    log(f"couldn't place {t['symbol']} trailing stop, selling to stay safe: {ex}", "Risk Officer")
                    event("risk", "no_stop_loss_possible", f"couldn't place the trailing stop, sold: {ex}", t["symbol"])
                    self.close(t, "no stop-loss possible")
                    continue
            # crypto: put the stop-loss on Alpaca's side as soon as the coins are in the account
            if t["asset"] == "crypto" and not t.get("stopOrderId") and ps in held:
                qty = float(held[ps].get("qty_available") or held[ps]["qty"])
                try:
                    o = self.a.crypto_stop(t["symbol"], qty, t["stop"], f"{t['id']}-stop")
                    t["stopOrderId"], t["qty"] = o["id"], qty
                    log(f"Stop-loss for {t['symbol']} placed on Alpaca at ${t['stop']:,.2f}", "Risk Officer")
                except HttpError as e:
                    log(f"couldn't place {t['symbol']} stop, selling to stay safe: {e}", "Risk Officer")
                    event("risk", "no_stop_loss_possible", f"couldn't place the stop, sold: {e}", t["symbol"])
                    self.close(t, "no stop-loss possible")
                    continue
            if ps in held:
                p = held[ps]
                t["lastPrice"] = float(p.get("current_price") or 0)
                t["unrealizedPct"] = round(float(p.get("unrealized_plpc") or 0) * 100, 2)
                continue
            # position is gone: find out how it ended
            exit_price, reason = None, "closed outside the bot"
            legs = entry.get("legs") or []
            if t.get("stopOrderId"):
                try:
                    legs = legs + [self.a.order(t["stopOrderId"])]
                except HttpError:
                    pass
            for leg in legs:
                if leg.get("status") == "filled":
                    exit_price = float(leg["filled_avg_price"])
                    if leg.get("type") == "trailing_stop":
                        px = float(leg["filled_avg_price"])
                        reason = f"trailing stop hit ({(px - t['entryPrice']) / t['entryPrice'] * 100:+.1f}%)"
                    else:
                        reason = "target +6% hit" if leg.get("type") == "limit" else "stop-loss -3% hit"
            self.finish(t, exit_price or t.get("lastPrice") or t["entryPrice"], reason)

    def finish(self, t, price, reason):
        t.update({"status": "closed", "closedAt": iso(), "exitPrice": price, "exitReason": reason,
                  "pnl": round((price - t["entryPrice"]) * t["qty"], 2),
                  "pnlPct": round((price - t["entryPrice"]) / t["entryPrice"] * 100, 2)})
        log(f"Closed {t['symbol']}: {reason}, {t['pnlPct']:+.2f}% (${t['pnl']:+,.2f})")
        rule = exit_rule(reason)
        if rule:
            event("risk", rule, f"{reason}, {t['pnlPct']:+.2f}% (${t['pnl']:+,.2f})", t["symbol"])

    def close(self, t, reason):
        try:
            self.a.sell_all(t["symbol"])
        except HttpError as e:
            log(f"sell {t['symbol']} failed: {e}")
            event("error", "sell_failed", e, t["symbol"])
            return
        t["closing"] = reason
        time.sleep(2)
        price = self.a.latest_price(t["symbol"]) or t.get("lastPrice") or t["entryPrice"]
        self.finish(t, price, reason)

    def time_and_target_exits(self, clock):
        now = now_et()
        for t in [t for t in self.open_trades() if t["status"] == "open"]:
            opened = parse_time(t["openedAt"])
            if t["asset"] == "crypto":
                price = self.a.latest_price(t["symbol"])
                if price and t.get("trail"):
                    self.trail_crypto(t, price)
                elif price and price >= t["target"]:
                    self.close(t, "target +6% hit")
                elif t.get("strategy") != "trend" and now_utc() - opened >= timedelta(hours=C.RISK["crypto_max_hold_hours"]):
                    self.close(t, "48h limit")
                continue
            if not clock.get("is_open"):
                continue
            start = opened.astimezone(now.tzinfo).date()
            cal = self.a.calendar(start.isoformat(), now.date().isoformat())
            days = sum(1 for d in cal if d["date"] > start.isoformat() and d["date"] <= now.date().isoformat())
            close_t = parse_time(clock.get("next_close")).astimezone(now.tzinfo) if clock.get("next_close") else None
            near_close = close_t and close_t - now <= timedelta(minutes=15)
            if t.get("strategy") in ("core", "trend"):
                continue                       # core + trend holdings: no time limit (trend exits on the study)
            lim = C.DIP["max_hold_days"] if t.get("strategy") == "dip" else C.RISK["stock_max_hold_trading_days"]
            if t.get("trail") and (t.get("unrealizedPct") or 0) >= 2:
                continue                       # a winner with a trailing stop rides; the stop decides when to sell
            if days > lim or (days == lim and near_close):
                self.close(t, f"{lim} trading-day limit")

    def trail_crypto(self, t, price):
        """Coins: raise the Alpaca stop as the price makes new highs (Alpaca has no trailing stop for crypto)."""
        t["high"] = max(t.get("high") or t["entryPrice"], price)
        new_stop = round_price(t["high"] * (1 - t["trail"] / 100))
        if new_stop <= (t.get("stop") or 0) * 1.005 or not t.get("stopOrderId"):
            return
        try:
            self.a.cancel(t["stopOrderId"])
            o = self.a.crypto_stop(t["symbol"], t["qty"], new_stop, f"{t['id']}-stop-{int(time.time())}")
            t["stopOrderId"], t["stop"] = o["id"], new_stop
            log(f"{t['symbol']} new high ${t['high']:,.2f}: stop raised to ${new_stop:,.2f}", "Risk Officer")
        except HttpError as ex:
            event("error", "trail_update", ex, t["symbol"])

    def bad_news_exits(self):
        from .triage import publishers
        for t in [t for t in self.open_trades() if t["status"] == "open"]:
            for e in self.s["events"].values():
                a = e["assets"].get(t["symbol"])
                if not a or a["direction"] != "down" or a["confidence"] < C.CONFIRM["sell_min_confidence"]:
                    continue
                if e["firstSeen"] < t["openedAt"]:
                    continue
                _, news_pubs = publishers(e)
                if news_pubs:
                    log(f"Bad news for {t['symbol']}: {e['summary'][:100]}", "News Analyst")
                    self.close(t, f"bad news: {e['summary'][:80]}")
                    break

    def kill(self, acct):
        from .risk import total_change
        log(f"KILL SWITCH: account down {total_change(acct, self.ledger['startEquity']):.1%} from the start. "
            "Selling everything and stopping. Run 'unlock' after you review.", "Risk Officer")
        event("risk", "kill_switch", f"down {total_change(acct, self.ledger['startEquity']):.2%} from the start: sold everything, locked")
        try:
            self.a.cancel_all_and_flatten()
        except HttpError as e:
            log(f"flatten failed: {e}", "Risk Officer")
            event("error", "flatten_failed", e)
        for t in self.open_trades():
            self.finish(t, self.a.latest_price(t["symbol"]) or t.get("lastPrice") or t["entryPrice"], "kill switch")
        self.ledger.update({"killed": True, "killedAt": iso()})
        self.s["alert"] = "Kill switch: down 10% from the start. Everything sold, bot locked."
        alert_popup(self.s["alert"])
        self.s["publishNow"] = True

    def track_equity(self, acct):
        eq = self.ledger["equity"]
        if eq and now_utc() - parse_time(eq[-1]["t"]) < timedelta(minutes=30):
            return
        try:
            spy = self.a.latest_price(C.BENCHMARK)
        except HttpError:
            spy = None
        eq.append({"t": iso(), "equity": round(float(acct["equity"]), 2), "spy": spy})
        del eq[:-1500]

    # ------------------------------------------------------------ entries
    def entries(self, acct, clock):
        from . import market, risk, deep, halal
        from .triage import publishers
        R = C.confirm_rules()
        fresh_cut = iso(now_utc() - timedelta(hours=C.CONFIRM["event_fresh_hours"]))
        cands = []
        stock_ok, stock_why = risk.stock_entry_window_open(clock)
        for e in self.s["events"].values():
            if e["firstSeen"] < fresh_cut and not (R.get("carry_overnight") and market.carry_ok(e["firstSeen"], now_utc())):
                continue
            pubs, news_pubs = publishers(e)
            for sym, a in e["assets"].items():
                key = f"{e['key']}|{sym}"
                if a["direction"] != "up" or key in self.s["decided"]:
                    continue
                if not halal.allowed(sym, self.universe):
                    self.decide(key, sym, "blocked", "fails the halal screen", e)
                    event("halal", "halal_screen", "fails the halal screen", sym)
                    continue
                if a["confidence"] < R["min_confidence"]:
                    continue
                av = (C.coach().get("avoid") or {}).get(sym)
                if av and parse_time(av) > now_utc():
                    self.decide(key, sym, "skipped", f"Coach: lost its last 3 trades, avoiding until {av[:10]}", e)
                    continue
                src_ok, _ = C.sources_ok(pubs, news_pubs, R)
                if not src_ok:
                    self.decide(key, sym, "waiting", f"only {len(pubs)} source(s) so far: {', '.join(sorted(pubs))}", e, final=False)
                    continue
                if "/" not in sym and not stock_ok:
                    if stock_why != "market closed":
                        event("risk", "stock_entry_window", stock_why, sym)
                    continue
                try:
                    chk = market.confirm(self.a, sym, "up", e["firstSeen"], rules=R)
                except HttpError as err:
                    log(f"price check {sym} failed: {err}", "Analyst")
                    continue
                if not chk["passed"]:
                    final = "too late" in chk["reason"]
                    self.decide(key, sym, "skipped" if final else "waiting", chk["reason"], e, final=final)
                    continue
                cands.append((a["confidence"] * min(chk["rvol"] / (R["min_rvol"] or 1.0), 2.0), key, sym, a, e, chk, pubs))
        cands.sort(key=lambda c: c[0], reverse=True)
        for score, key, sym, a, e, chk, pubs in cands:
            acct = self.a.account()
            positions = self.a.positions()
            ok, why = risk.can_open(sym, acct, positions, self.open_trades(),
                                    {**self.s, "killed": self.ledger.get("killed")}, self.ledger["startEquity"],
                                    confidence=a.get("confidence"))
            if not ok:
                self.decide(key, sym, "waiting", why, e, final=False)
                event("risk", risk.rule_name(why), why, sym)
                continue
            counters, used = self.today_count("deep")
            if R.get("skip_deep"):          # ultra mode: no TradingAgents gate, buy on the news
                self.buy(key, sym, a, e, chk, {"approved": True, "rating": "not used (ultra mode)"}, pubs, acct)
                continue
            if used >= C.DEEP["max_per_day"]:
                self.decide(key, sym, "waiting", "used today's 5 TradingAgents checks", e, final=False)
                event("limit", "tradingagents_daily_cap", "used today's 5 TradingAgents checks", sym)
                continue
            counters["deep"] = used + 1
            self.save()
            ctx = f"News: {e['summary']} | why {sym}: {a['why']} | sources: {', '.join(sorted(pubs))}"
            verdict = deep.run(sym, context=ctx)
            if verdict.get("error"):
                event("error", "tradingagents", verdict["error"][:200], sym)
            elif not verdict["approved"]:
                event("ai", "tradingagents_said_no", f"TradingAgents said {verdict.get('rating')}", sym)
            if not verdict["approved"]:
                self.decide(key, sym, "rejected", f"TradingAgents said {verdict.get('rating')}"
                            + (f" ({verdict['error'][:80]})" if verdict.get("error") else ""), e)
                continue
            # the analysis takes minutes: re-check the price is still inside the window
            chk2 = market.confirm(self.a, sym, "up", e["firstSeen"], rules=R)
            if chk2.get("movePct") is not None and chk2["movePct"] / 100 > C.CONFIRM["max_move_pct"]:
                self.decide(key, sym, "skipped", f"moved {chk2['movePct']:+.2f}% while being analysed, too late", e)
                continue
            self.buy(key, sym, a, e, chk2 if chk2.get("price") else chk, verdict, pubs, acct)

    def buy(self, key, sym, a, e, chk, verdict, pubs, acct):
        from . import risk
        price = self.a.latest_price(sym) or chk["price"]
        pending = sum(t["cost"] for t in self.open_trades() if t["status"] == "pending") + self.reserved(acct)
        budget, _ = risk.size_order(acct, price, pending, confidence=a.get("confidence"), n_sources=len(pubs),
                                    start_equity=self.ledger.get("startEquity"), publishers=sorted(pubs))
        stop, target = risk.stop_and_target(price)
        tid = f"ahq-{sym.replace('/', '')}-{now_utc():%Y%m%d%H%M%S}"
        try:
            if "/" in sym:
                if budget < 10:
                    raise ValueError("not enough cash")
                o = self.a.buy_crypto(sym, budget, tid)
                qty, cost = None, budget
            else:
                qty = int(budget // price)
                if qty < 1:
                    raise ValueError("not enough cash for one share")
                if C.trail_pct() > 0:
                    o = self.a.buy_stock(sym, qty, tid)      # trailing stop goes on as soon as it fills (reconcile)
                else:
                    o = self.a.buy_stock_bracket(sym, qty, round(stop, 2), round(target, 2), tid)
                cost = qty * price
        except (HttpError, ValueError) as err:
            self.decide(key, sym, "error", f"order failed: {str(err)[:120]}", e)
            log(f"Order for {sym} failed: {err}")
            if "not enough cash" in str(err):
                event("risk", "cash_only_no_margin", str(err), sym)
            else:
                event("error", "order_failed", err, sym)
            return
        self.decide(key, sym, "bought", f"{chk['reason']}; TradingAgents: {verdict['rating']}", e)
        self.ledger["trades"].insert(0, {
            "id": tid, "symbol": sym, "asset": "crypto" if "/" in sym else "stock", "status": "pending",
            "entryOrderId": o["id"], "qty": qty, "cost": round(cost, 2), "estPrice": price,
            "entryPrice": price, "stop": round_price(stop), "target": round_price(target), "openedAt": iso(),
            "trail": C.trail_pct() if C.trail_pct() > 0 else None,
            "news": {"summary": e["summary"], "category": e["category"],
                     "sources": [{"publisher": x["publisher"], "title": x["title"], "url": x.get("url")} for x in e["items"][:6]]},
            "reason": {"triage": a["why"], "confidence": a["confidence"], "confirmation": chk["reason"],
                       "rvol": chk.get("rvol"), "movePct": chk.get("movePct"), "publishers": sorted(pubs),
                       "tradingAgents": verdict["rating"], "taSummary": verdict.get("summary", "")[:600]},
        })
        log(f"BUY {sym}: {e['summary'][:90]} | {chk['reason']} | TradingAgents {verdict['rating']}")
        self.s["publishNow"] = True


def exit_rule(reason):
    """Which risk rule closed a trade (None for exits that aren't a risk rule)."""
    r = reason.lower()
    for key, rule in (("trailing stop", "trailing_stop"), ("stop-loss", "stop_loss_-3%"), ("target", "take_profit_+6%"), ("3 trading-day", "stock_3_day_limit"),
                      ("48h", "crypto_48h_limit"), ("bad news", "bad_news_exit"), ("kill switch", "kill_switch_exit"),
                      ("no stop-loss", "no_stop_loss_possible"), ("outside the bot", "closed_outside_bot")):
        if key in r:
            return rule
    return None


def alert_popup(msg):
    if sys.platform != "win32":
        return
    import subprocess
    ps = ("Add-Type -AssemblyName PresentationFramework;"
          f"[System.Windows.MessageBox]::Show('{msg.replace(chr(39), '')}','Agent HQ Trading Bot','OK','Warning')")
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", ps])
    except OSError:
        pass


# ------------------------------------------------------------ entry points
def run_forever():
    from . import report, publish
    from .news import agent_reach_available
    with SingleInstance():
        log("Paper-trading bot started (Alpaca PAPER account only). Close this window to stop it.", "Trader")
        event("info", "bot_started", "started (PAPER only)")
        try:   # save to the dashboard right after a (re)start, so a fix shows up within minutes
            st = read_json(STATE, {}) or {}
            st["publishNow"], st["lastPublish"] = True, None
            write_json(STATE, st)
        except OSError:
            pass
        if not agent_reach_available():
            log("Agent Reach not found: news feeds + Yahoo Finance + Reddit direct (no X)", "News Scout")
        last_social = None
        while True:
            open_now = False
            try:
                bot = Bot()
                social = (last_social is None or
                                                      now_utc() - last_social >= timedelta(minutes=C.LOOP["social_minutes"]))
                if social:
                    last_social = now_utc()
                bot.cycle(social=social)
                open_now = bool(bot.a.clock().get("is_open"))
                report.write(bot)
                publish.maybe(bot.s)
                bot.save()
            except KeyboardInterrupt:
                raise
            except SystemExit:
                raise
            except Exception:  # noqa: BLE001  keep running; stop-losses live on Alpaca anyway
                log("Cycle error (will retry): " + traceback.format_exc().strip().splitlines()[-1], "Trader")
                event("error", "cycle", traceback.format_exc().strip().splitlines()[-1])
                traceback.print_exc()
            wait = C.LOOP["market_minutes"] if open_now else C.LOOP["offhours_minutes"]
            time.sleep(wait * 60)


def main(argv):
    load_env()
    cmd = argv[1] if len(argv) > 1 else "run"
    if cmd == "run":
        run_forever()
    elif cmd == "once":
        from . import report
        with SingleInstance():
            b = Bot(); b.cycle(social=True); report.write(b); b.save()
    elif cmd == "check":
        from . import check
        check.run()
    elif cmd == "universe":
        from . import halal
        from .alpaca import Alpaca
        u = halal.build_universe(Alpaca(), force=True)
        print(f"{len(u.get('stocks', {}))} stocks/ETFs + {len(u.get('crypto', {}))} coins pass the halal screen "
              f"({len(u.get('rejected', {}))} rejected)")
        if u.get("partial"):
            print("PARTIAL: " + u.get("problem", "") + " -> only coins + Shariah ETFs for now, retries hourly.")
        else:
            print("Sample: " + ", ".join(sorted(u.get("stocks", {}))[:25]))
    elif cmd == "publish":
        from . import publish
        publish.push("Trading bot: manual save")
    elif cmd == "unlock":
        led = read_json(LEDGER, {}) or {}
        led.update({"killed": False, "unlockedAt": iso()})
        write_json(LEDGER, led)
        print("Kill switch cleared. The bot will trade again on its next cycle.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
