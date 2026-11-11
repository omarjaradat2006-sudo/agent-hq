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
        if not self.ledger.get("killed"):
            self.entries(acct, clock)
        self.track_equity(acct)
        self.save()

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
                if price and price >= t["target"]:
                    self.close(t, "target +6% hit")
                elif now_utc() - opened >= timedelta(hours=C.RISK["crypto_max_hold_hours"]):
                    self.close(t, "48h limit")
                continue
            if not clock.get("is_open"):
                continue
            start = opened.astimezone(now.tzinfo).date()
            cal = self.a.calendar(start.isoformat(), now.date().isoformat())
            days = sum(1 for d in cal if d["date"] > start.isoformat() and d["date"] <= now.date().isoformat())
            close_t = parse_time(clock.get("next_close")).astimezone(now.tzinfo) if clock.get("next_close") else None
            near_close = close_t and close_t - now <= timedelta(minutes=15)
            if days > C.RISK["stock_max_hold_trading_days"] or (days == C.RISK["stock_max_hold_trading_days"] and near_close):
                self.close(t, "3 trading-day limit")

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
                if a["confidence"] < C.CONFIRM["min_confidence"]:
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
                cands.append((a["confidence"] * min(chk["rvol"] / R["min_rvol"], 2.0), key, sym, a, e, chk, pubs))
        cands.sort(key=lambda c: c[0], reverse=True)
        for score, key, sym, a, e, chk, pubs in cands:
            acct = self.a.account()
            positions = self.a.positions()
            ok, why = risk.can_open(sym, acct, positions, self.open_trades(),
                                    {**self.s, "killed": self.ledger.get("killed")}, self.ledger["startEquity"])
            if not ok:
                self.decide(key, sym, "waiting", why, e, final=False)
                event("risk", risk.rule_name(why), why, sym)
                continue
            counters, used = self.today_count("deep")
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
        pending = sum(t["cost"] for t in self.open_trades() if t["status"] == "pending")
        budget, _ = risk.size_order(acct, price, pending)
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
    for key, rule in (("stop-loss", "stop_loss_-3%"), ("target", "take_profit_+6%"), ("3 trading-day", "stock_3_day_limit"),
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
