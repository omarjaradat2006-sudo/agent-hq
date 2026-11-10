"""Alpaca PAPER account client (stdlib only). The live URL is never used."""
import os
from . import config as C
from .util import http, HttpError


def to_pos_symbol(sym):          # "BTC/USD" -> "BTCUSD" (how positions name crypto)
    return sym.replace("/", "")


def is_crypto(sym):
    return "/" in sym or sym in {to_pos_symbol(c) for c in C.CRYPTO_ALLOWED}


def from_pos_symbol(sym):        # "BTCUSD" -> "BTC/USD"
    return next((c for c in C.CRYPTO_ALLOWED if to_pos_symbol(c) == sym), sym)


class Alpaca:
    def __init__(self, key=None, secret=None, trading_url=C.ALPACA_TRADING_URL, data_url=C.ALPACA_DATA_URL):
        self.key = key or os.environ.get("ALPACA_API_KEY", "")
        self.secret = secret or os.environ.get("ALPACA_SECRET_KEY", "")
        if "paper-api" not in trading_url:
            raise SystemExit("Refusing to run: this bot only trades the Alpaca PAPER account.")
        self.t, self.d = trading_url, data_url
        if not self.key or not self.secret:
            raise SystemExit("Missing ALPACA_API_KEY / ALPACA_SECRET_KEY (laptop: trading_bot/.env, server: ~/.trading-bot.env)")
        if self.key.startswith("AK"):
            raise SystemExit("Refusing to run: that is a LIVE Alpaca key (starts with AK). Use PAPER keys (start with PK).")

    def _h(self):
        return {"APCA-API-KEY-ID": self.key, "APCA-API-SECRET-KEY": self.secret}

    def get(self, path, params=None, data=False):
        return http("GET", (self.d if data else self.t) + path, params=params, headers=self._h())

    def post(self, path, body):
        return http("POST", self.t + path, body=body, headers=self._h(), retries=0)

    def delete(self, path, params=None):
        return http("DELETE", self.t + path, params=params, headers=self._h(), retries=0)

    # ---- account
    def account(self):
        return self.get("/v2/account")

    def clock(self):
        return self.get("/v2/clock")

    def calendar(self, start, end):
        return self.get("/v2/calendar", {"start": start, "end": end}) or []

    def positions(self):
        return self.get("/v2/positions") or []

    def orders(self, status="open", symbols=None, limit=200):
        return self.get("/v2/orders", {"status": status, "limit": limit, "nested": "true",
                                        "symbols": ",".join(symbols) if symbols else None}) or []

    def order(self, oid):
        return self.get(f"/v2/orders/{oid}", {"nested": "true"})

    def cancel(self, oid):
        try:
            self.delete(f"/v2/orders/{oid}")
        except HttpError as e:
            if e.code not in (404, 422):
                raise

    def asset(self, sym):
        try:
            return self.get(f"/v2/assets/{sym.replace('/', '%2F')}")
        except HttpError as e:
            if e.code == 404:
                return None
            raise

    # ---- orders (long only, cash only)
    def buy_stock_bracket(self, sym, qty, stop, target, client_id):
        return self.post("/v2/orders", {
            "symbol": sym, "qty": str(int(qty)), "side": "buy", "type": "market", "time_in_force": "gtc",
            "order_class": "bracket", "client_order_id": client_id,
            "take_profit": {"limit_price": f"{target:.2f}"},
            "stop_loss": {"stop_price": f"{stop:.2f}"},
        })

    def buy_crypto(self, sym, notional, client_id):
        return self.post("/v2/orders", {"symbol": sym, "notional": f"{notional:.2f}", "side": "buy",
                                        "type": "market", "time_in_force": "gtc", "client_order_id": client_id})

    def crypto_stop(self, sym, qty, stop, client_id):
        """Stop-loss that lives on Alpaca's servers (works with the laptop off)."""
        limit = stop * 0.99   # 1% below the trigger so it fills in a fast drop
        return self.post("/v2/orders", {"symbol": sym, "qty": f"{qty}", "side": "sell", "type": "stop_limit",
                                        "stop_price": _p(stop), "limit_price": _p(limit),
                                        "time_in_force": "gtc", "client_order_id": client_id})

    def sell_all(self, sym):
        """Market-sell a whole position (open orders for it are cancelled first)."""
        for o in self.orders("open", symbols=[sym]):
            self.cancel(o["id"])
            for leg in o.get("legs") or []:
                self.cancel(leg["id"])
        try:
            return self.delete(f"/v2/positions/{to_pos_symbol(sym).replace('/', '%2F')}")
        except HttpError as e:
            if e.code == 404:
                return None
            raise

    def cancel_all_and_flatten(self):
        return self.delete("/v2/positions", {"cancel_orders": "true"})

    # ---- market data (free IEX feed for stocks)
    def stock_bars(self, symbols, timeframe, start, end=None, limit=10000):
        out, token = {}, None
        while True:
            r = self.get("/v2/stocks/bars", {"symbols": ",".join(symbols), "timeframe": timeframe, "start": start,
                                              "end": end, "limit": limit, "feed": "iex", "adjustment": "raw",
                                              "page_token": token}, data=True) or {}
            for s, bars in (r.get("bars") or {}).items():
                out.setdefault(s, []).extend(bars)
            token = r.get("next_page_token")
            if not token:
                return out

    def crypto_bars(self, symbols, timeframe, start, end=None, limit=10000):
        out, token = {}, None
        while True:
            r = self.get("/v1beta3/crypto/us/bars", {"symbols": ",".join(symbols), "timeframe": timeframe,
                                                      "start": start, "end": end, "limit": limit,
                                                      "page_token": token}, data=True) or {}
            for s, bars in (r.get("bars") or {}).items():
                out.setdefault(s, []).extend(bars)
            token = r.get("next_page_token")
            if not token:
                return out

    def latest_price(self, sym):
        if "/" in sym:
            r = self.get("/v1beta3/crypto/us/latest/trades", {"symbols": sym}, data=True) or {}
            t = (r.get("trades") or {}).get(sym)
        else:
            r = self.get("/v2/stocks/trades/latest", {"symbols": sym, "feed": "iex"}, data=True) or {}
            t = (r.get("trades") or {}).get(sym)
        return float(t["p"]) if t else None

    def news(self, start, end=None, symbols=None, limit=50, max_pages=6):
        out, token = [], None
        for _ in range(max_pages):
            r = self.get("/v1beta1/news", {"start": start, "end": end, "symbols": ",".join(symbols) if symbols else None,
                                            "limit": limit, "sort": "desc", "include_content": "false",
                                            "page_token": token}, data=True) or {}
            out.extend(r.get("news") or [])
            token = r.get("next_page_token")
            if not token:
                break
        return out


def _p(x):
    return f"{x:.2f}" if x >= 1 else f"{x:.6f}"
