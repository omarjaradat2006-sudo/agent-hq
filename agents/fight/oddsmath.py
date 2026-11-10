"""Odds math. Prices are stored as decimal odds; American odds are for display."""
from functools import reduce


def american_to_decimal(a):
    a = float(a)
    return 1 + a / 100 if a > 0 else 1 + 100 / abs(a)


def decimal_to_american(d):
    d = float(d)
    if d <= 1:
        return 0
    return round((d - 1) * 100) if d >= 2 else round(-100 / (d - 1))


def fmt_american(d):
    a = decimal_to_american(d)
    return f"+{a}" if a > 0 else str(a)


def implied(d):
    """Implied probability of a decimal price (includes the book's margin)."""
    return 1 / float(d)


def no_vig(prices):
    """Fair probabilities for one market at one book: remove the margin proportionally.
    prices: list of decimal odds for every outcome of the market."""
    raw = [implied(p) for p in prices]
    s = sum(raw)
    return [r / s for r in raw]


def ev(prob, d):
    """Expected profit per 1 unit staked at decimal price d."""
    return prob * (d - 1) - (1 - prob)


def blend(fair, model, weight):
    """Shrink the research estimate toward the market (LLM estimates are overconfident)."""
    if model is None:
        return fair
    model = min(max(float(model), 0.01), 0.99)
    return fair + weight * (model - fair)


def parlay_decimal(decs):
    return reduce(lambda a, b: a * b, decs, 1.0)


def parlay_prob(probs):
    return reduce(lambda a, b: a * b, probs, 1.0)


def profit_per_100(result, d):
    """Profit on a flat $100 stake."""
    if result == "win":
        return round(100 * (d - 1), 2)
    if result == "loss":
        return -100.0
    return 0.0  # push / void
