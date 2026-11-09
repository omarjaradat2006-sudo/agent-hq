"""The brain: TradingAgents deep analysis (multi-agent debate) on Gemini.

Runs in a separate process with a time limit, so a hang or crash can never stop the bot
or place an order. Any error = NOT approved = no trade.
"""
import json, os, subprocess, sys
from . import config as C
from .util import ROOT, now_et, log


def _models():
    """Deep = the Flash model Agent HQ already uses; quick = newest Flash-Lite (cheaper on the free tier)."""
    sys.path.insert(0, str(ROOT / "agents" / "gemini"))
    import gemini
    deep = os.environ.get("TA_DEEP_MODEL") or gemini.model()
    quick = os.environ.get("TA_QUICK_MODEL")
    if not quick:
        try:
            names = [m["name"].split("/")[-1] for m in gemini._req("GET", "models?pageSize=200").get("models", [])
                     if "generateContent" in m.get("supportedGenerationMethods", [])]
            lites = sorted([n for n in names if "flash-lite" in n and "preview" not in n], reverse=True)
            quick = lites[0] if lites else deep
        except Exception:  # noqa: BLE001
            quick = deep
    return deep, quick


def ta_symbol(sym):
    return sym.replace("/", "-") if "/" in sym else sym          # BTC/USD -> BTC-USD (Yahoo style)


def run(symbol, trade_date=None, context=""):
    """Returns {"approved": bool, "rating": str, "summary": str, "error": str|None}."""
    trade_date = trade_date or now_et().date().isoformat()
    cmd = [sys.executable, "-m", "trading_bot.deep", ta_symbol(symbol), trade_date,
           "crypto" if "/" in symbol else "stock"]
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=C.DEEP["timeout_min"] * 60, env={**os.environ, "TA_CONTEXT": context[:1500]})
        line = next((l for l in reversed((p.stdout or "").splitlines()) if l.startswith("{\"rating\"")), None)
        if not line:
            raise RuntimeError((p.stderr or p.stdout or "no output")[-300:])
        out = json.loads(line)
    except subprocess.TimeoutExpired:
        out = {"rating": "ERROR", "summary": "", "error": f"took longer than {C.DEEP['timeout_min']} min"}
    except Exception as e:  # noqa: BLE001
        out = {"rating": "ERROR", "summary": "", "error": str(e)[-300:]}
    out["approved"] = out.get("rating") in C.DEEP["approve_ratings"]
    log(f"TradingAgents on {symbol}: {out.get('rating')}" + (f" ({out['error'][:120]})" if out.get("error") else ""),
        "Deep Analyst")
    return out


def _worker(ticker, trade_date, asset_type):
    from .util import load_env
    load_env()
    from tradingagents.default_config import DEFAULT_CONFIG
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    deep, quick = _models()
    cfg = DEFAULT_CONFIG.copy()
    cfg.update({"llm_provider": "google", "deep_think_llm": deep, "quick_think_llm": quick,
                "max_debate_rounds": 1, "max_risk_discuss_rounds": 1, "max_tool_rounds": 6,
                "news_article_limit": 10, "global_news_article_limit": 6, "llm_max_retries": 4,
                "results_dir": str(ROOT / "trading_bot" / "local" / "ta_logs"),
                "data_cache_dir": str(ROOT / "trading_bot" / "local" / "ta_cache"),
                "memory_log_path": str(ROOT / "trading_bot" / "local" / "ta_memory.md"),
                "holding_period_days": 3})
    ta = TradingAgentsGraph(debug=False, config=cfg)
    state, signal = ta.propagate(ticker, trade_date, asset_type=asset_type)
    text = ""
    if isinstance(state, dict):
        text = str(state.get("final_trade_decision") or state.get("investment_plan") or "")
    print(json.dumps({"rating": str(signal), "summary": text[:900], "error": None, "models": [deep, quick]}), flush=True)


if __name__ == "__main__":
    _worker(*sys.argv[1:4])
