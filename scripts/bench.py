"""Run every prompt through /v1/config/decision/test (the router's own RouteByAI) for each engine.

Usage: MR_BASE=http://127.0.0.1:8000 MR_ADMIN_PASSWORD=... LAYA_API_KEY=... python3 scripts/bench.py [rounds]
Writes results/router/results.json.
Expects a connection named foundry2 holding gpt-4.1-mini and a msft-decision-1 deployment, a
TypeSafe key in ai_router.typesafe, and laya-serve on 127.0.0.1:8100.
"""
import copy, json, os, sys, time, urllib.request, http.cookiejar
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results" / "router" / "results.json"

BASE = os.environ.get("MR_BASE", "http://127.0.0.1:8000")
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with op.open(req, timeout=120) as r:
        return json.load(r)

call("POST", "/v1/auth/local/login", {"username": "admin", "password": os.environ["MR_ADMIN_PASSWORD"]})
cfg = call("GET", "/v1/config")
laya_key = os.environ.get("LAYA_API_KEY", "")

base = copy.deepcopy(cfg["ai_router"])
base["timeout_seconds"] = 15
base["laya"] = {"base_url": "http://127.0.0.1:8100", "api_key": laya_key}
base["microsoft"] = {"provider": "foundry2", "model": "msft-decision-1"}
base["decision_model"] = "gpt-4.1-mini"
base["decision_provider"] = "foundry2"
ENGINES = ["microsoft", "typesafe", "laya", "llm"]

def draft(engine):
    d = copy.deepcopy(base); d["decision_engine"] = engine; return d

prompts = json.load(open(ROOT / "data" / "prompts.json"))
out = []
# warm-up: one call per engine, not recorded (connection setup)
for e in ENGINES:
    call("POST", "/v1/config/decision/test", {"models": cfg["models"], "ai_router": draft(e), "sample_prompt": "hello"})
for rnd in range(ROUNDS):
    for setname in ("A", "B"):
        for i, (lang, text, want) in enumerate(prompts[setname]):
            for e in ENGINES:
                r = call("POST", "/v1/config/decision/test", {"models": cfg["models"], "ai_router": draft(e), "sample_prompt": text})
                a = r["analysis"]
                rec = dict(round=rnd, set=setname, idx=i + 1, lang=lang, engine=e, want=want, got=r["model"], ok=r["ok"],
                           correct=r["ok"] and r["model"] == want, decision_ms=a.get("decision_latency_ms"),
                           total_ms=r["latency_ms"], p=a.get("probabilities"), confidence=a.get("confidence"),
                           error=a.get("error"), checkpoint=(a.get("decision_checkpoint") or {}).get("model"),
                           rationale=a.get("rationale"))
                out.append(rec)
                print(rnd, setname, i + 1, e, rec["got"], "OK" if rec["correct"] else "x", rec["decision_ms"], rec["error"] or "", flush=True)
                if e == "microsoft":
                    time.sleep(0.3)
    json.dump(out, open(RESULTS, "w"), ensure_ascii=False, indent=1)
json.dump(out, open(RESULTS, "w"), ensure_ascii=False, indent=1)
