"""Rebuild every summary and cost file from the raw results, then merge them for the charts.

Usage: python3 scripts/merge_results.py [original|guided|generic|detailed]
  results/router/results.json, usage-results.json -> results/router/summary.json, cost.json
  results/openai/results_openai_<catalog>.json    -> results/openai/summary_openai_<catalog>.json, cost_openai.json
  router + the chosen OpenAI catalog (default original) -> results/summary.json, results/cost.json
"""
import json, sys
from pathlib import Path
from metrics import cost, summarize

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
CATALOG = sys.argv[1] if len(sys.argv) > 1 else "original"


def load(path):
    return json.load(open(path))


def dump(obj, path):
    json.dump(obj, open(path, "w"), ensure_ascii=False, indent=1)
    print("wrote", path.relative_to(ROOT))


def engines(records):
    return list(dict.fromkeys(r["engine"] for r in records))


def summaries(records):
    rounds = max(r["round"] for r in records) + 1
    return {e: summarize([r for r in records if r["engine"] == e], rounds) for e in engines(records)}


def costs(records):
    return {e: cost(e, [r["usage"] for r in records if r["engine"] == e and r.get("usage")]) for e in engines(records)}


if not (RES / "openai" / f"results_openai_{CATALOG}.json").is_file():
    sys.exit(f"no results/openai/results_openai_{CATALOG}.json; run scripts/bench_openai.py 3 {CATALOG} first")

router_summary = summaries(load(RES / "router" / "results.json"))
router_cost = costs(load(RES / "router" / "usage-results.json"))
dump(router_summary, RES / "router" / "summary.json")
dump(router_cost, RES / "router" / "cost.json")

openai_cost = {}
for path in sorted((RES / "openai").glob("results_openai_*.json")):
    catalog = path.stem.removeprefix("results_openai_")
    records = load(path)
    dump(summaries(records), RES / "openai" / f"summary_openai_{catalog}.json")
    openai_cost[catalog] = costs(records)["openai"]
dump(openai_cost, RES / "openai" / "cost_openai.json")

dump({**router_summary, "openai": load(RES / "openai" / f"summary_openai_{CATALOG}.json")["openai"]}, RES / "summary.json")
dump({**router_cost, "openai": openai_cost[CATALOG]}, RES / "cost.json")
