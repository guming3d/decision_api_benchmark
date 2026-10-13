"""Shared metrics: per-engine accuracy/latency/confidence summary and cost per decision."""
import statistics as st

# USD per 1M tokens (input, output). Decision-1 and Jev bill input only; Laya runs locally.
PRICES = {"microsoft": (0.042, 0.0), "typesafe": (0.042, 0.0), "llm": (0.40, 1.60), "laya": (0.0, 0.0),
          "openai": (0.10, 0.0)}  # gpt-6-luna on the Decisions API: input only, no cache or output charges
MONTHLY_DECISIONS = 440_000


def summarize(out, rounds):
    """Summary for one engine's records, same shape as an entry in results/summary.json."""
    s = {}
    for setname in ("A", "B"):
        for lang in ("EN", "ZH", "ALL"):
            s[f"{setname}-{lang}"] = [sum(r["correct"] for r in out if r["round"] == rnd and r["set"] == setname
                                          and (lang == "ALL" or r["lang"] == lang)) for rnd in range(rounds)]
    picks = {}
    for r in out:
        picks.setdefault((r["set"], r["idx"]), set()).add(r["got"])
    ms = [r["decision_ms"] for r in out if r["ok"]]
    pch = [r["p"][r["got"]] for r in out if r["ok"] and r["p"]]
    s.update(stable=sum(len(v) == 1 for v in picks.values()), prompts=len(picks),
             ms_p50=round(st.median(ms)) if ms else None,
             ms_p95=round(st.quantiles(ms, n=20, method="inclusive")[18]) if len(ms) > 1 else None,
             ms_min=round(min(ms)) if ms else None, ms_max=round(max(ms)) if ms else None)
    if pch:
        s.update(pchosen_mean=round(st.mean(pch), 3), pchosen_min=round(min(pch), 3),
                 pchosen_ge09=round(sum(p >= 0.9 for p in pch) / len(pch), 3))
    s["errors"] = sum(1 for r in out if r["error"])
    return s


def cost(engine, usage):
    """Cost entry from a list of {"prompt_tokens", "completion_tokens"}, same shape as results/cost.json."""
    tin = st.mean(u["prompt_tokens"] for u in usage)
    tout = st.mean(u["completion_tokens"] for u in usage)
    pin, pout = PRICES[engine]
    per = (tin * pin + tout * pout) / 1e6
    return dict(tin=round(tin), tout=round(tout), per_decision=per, per_million=round(per * 1e6, 1),
                month_440k=round(per * MONTHLY_DECISIONS, 2))
