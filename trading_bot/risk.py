"""Hard risk rules. Nothing from the AI layers can change these numbers."""
from datetime import timedelta
from . import config as C
from .util import now_et, ET

R = C.RISK


def account_numbers(acct):
    eq = float(acct.get("equity") or 0)
    last = float(acct.get("last_equity") or eq or 1)
    cash = float(acct.get("cash") or 0)
    return eq, last, cash


def day_change(acct):
    eq, last, _ = account_numbers(acct)
    return (eq - last) / last if last else 0.0


def total_change(acct, start_equity):
    eq, _, _ = account_numbers(acct)
    return (eq - start_equity) / start_equity if start_equity else 0.0


def kill_switch_hit(acct, start_equity):
    return total_change(acct, start_equity) <= -R["total_loss_kill_pct"]


def daily_halt_hit(acct):
    return day_change(acct) <= -R["daily_loss_halt_pct"]


def stock_entry_window_open(clock, now=None):
    """Market open, at least 10 min after the open, and not in the last 30 min."""
    if not clock.get("is_open"):
        return False, "market closed"
    now = (now or now_et()).astimezone(ET)
    open_t = now.replace(hour=9, minute=30, second=0, microsecond=0)
    close_t = now.replace(hour=16, minute=0, second=0, microsecond=0)
    nc = clock.get("next_close")
    if nc:
        from .util import parse_time
        close_t = parse_time(nc).astimezone(ET)   # handles early-close days
    if now < open_t + timedelta(minutes=R["stock_first_entry_after_open_min"]):
        return False, "first minutes after the open"
    if now > close_t - timedelta(minutes=R["stock_no_new_trades_before_close_min"]):
        return False, "last 30 min before the close"
    return True, ""


def size_order(acct, price, pending_cost=0.0):
    """5% of equity, cash only (never margin). Returns (qty_or_notional, cost) or (0, 0)."""
    eq, _, cash = account_numbers(acct)
    budget = eq * R["max_pct_per_trade"]
    free_cash = cash - pending_cost
    budget = min(budget, free_cash)          # no margin: only money we actually have
    if budget <= 0 or not price:
        return 0, 0.0
    return budget, budget


def stop_and_target(entry):
    return entry * (1 - R["stop_loss_pct"]), entry * (1 + R["take_profit_pct"])


def can_open(symbol, acct, positions, open_trades, state, start_equity):
    """Every check that must pass before ANY buy. Returns (ok, reason)."""
    if state.get("killed"):
        return False, "kill switch is on (down 10%)"
    if kill_switch_hit(acct, start_equity):
        return False, "down 10% from start"
    if state.get("haltedDate") == now_et().date().isoformat() or daily_halt_hit(acct):
        return False, "down 3% today, no new trades until tomorrow"
    held = {p["symbol"] for p in positions} | {t["symbol"].replace("/", "") for t in open_trades}
    if symbol.replace("/", "") in held:
        return False, "already holding it"
    if len(held) >= R["max_open_positions"]:
        return False, f"already {len(held)} open positions (max {R['max_open_positions']})"
    if acct.get("trading_blocked") or acct.get("account_blocked"):
        return False, "Alpaca account blocked"
    return True, ""
