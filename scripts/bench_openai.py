"""Run every prompt in data/prompts.json through the OpenAI Decision API (client.decisions.create).

Usage: OPENAI_API_KEY=... python3 scripts/bench_openai.py [rounds] [guided|generic|detailed]
Writes results/openai/results_openai_<catalog>.json (same record shape as results/router/results.json,
engine="openai") and results/openai/summary_openai_<catalog>.json.

The router's model catalog is not available here, so there are three choice-description sets:
  detailed - written after seeing the prompts; names task types that appear in the test set (optimistic)
  generic  - only the catalog-level phrases quoted in the LLM engine's rationales in results.json (pessimistic)
  guided   - follows the Decisions guide: say when each option applies, in observable terms, without
             naming the test prompts' specific topics
"""
import json, sys, time
from pathlib import Path
from openai import OpenAI
from metrics import summarize

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "results" / "openai"

MODEL = "gpt-6-luna"
ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
INSTRUCTIONS = ("Which model should handle this user request? Choose the model whose strengths best match "
                "the request's type and difficulty; prefer the cheaper model when it is good enough.")
CATALOG = sys.argv[2] if len(sys.argv) > 2 else "guided"
DETAILED = [
    {"value": "gpt-4.1-mini", "description": "Fastest, cheapest model. Greetings, chit-chat, thanks and trivial one-line factual questions."},
    {"value": "gpt-4o", "description": "Fast general-purpose model. Short summaries, rewriting or polishing text, list/format conversion."},
    {"value": "gpt-4.1", "description": "Solid coding model. Writing, reviewing, debugging and explaining code, SQL and frameworks."},
    {"value": "gpt-5.4", "description": "Strongest reasoning model. Math proofs, probability, deep multi-step analysis, complex system design and root-cause investigation."},
    {"value": "gpt-6-luna", "description": "Creative model. Stories, poems, toasts, marketing copy, brand stories and other creative or long-form writing."},
]
GENERIC = [
    {"value": "gpt-4.1-mini", "description": "Fastest, cheapest, lightweight model."},
    {"value": "gpt-4o", "description": "Fast general-purpose model."},
    {"value": "gpt-4.1", "description": "Solid coding model."},
    {"value": "gpt-5.4", "description": "Strongest reasoning model for deep multi-step analysis."},
    {"value": "gpt-6-luna", "description": "Creative model for creative long-form writing."},
]
GUIDED = [
    {"value": "gpt-4.1-mini", "description": "Use when the request is casual conversation or a short factual question with one well-known answer."},
    {"value": "gpt-4o", "description": "Use when the request asks to transform text the user supplies (summarise, rewrite, reformat, restructure) without creating new content."},
    {"value": "gpt-4.1", "description": "Use when the request involves source code: writing, modifying, reviewing, debugging or explaining code or queries."},
    {"value": "gpt-5.4", "description": "Use when the request needs extended multi-step reasoning: a mathematical proof or derivation, or open-ended analysis or design of a complex system."},
    {"value": "gpt-6-luna", "description": "Use when the request asks for original creative writing where tone and style matter, such as fiction or persuasive copy."},
]
CHOICES = {"detailed": DETAILED, "generic": GENERIC, "guided": GUIDED}[CATALOG]
QUESTIONS = [{"type": "choice", "name": "route", "instructions": INSTRUCTIONS, "choices": CHOICES}]

client = OpenAI(max_retries=3, timeout=30)

def decide(text):
    t0 = time.perf_counter()
    d = client.decisions.create(model=MODEL, input=text, questions=QUESTIONS)
    return d, (time.perf_counter() - t0) * 1000

def record(rnd, setname, idx, lang, want, text):
    rec = dict(round=rnd, set=setname, idx=idx, lang=lang, engine="openai", want=want, got=None, ok=False,
               correct=False, decision_ms=None, total_ms=None, p=None, confidence=None, error=None,
               checkpoint=None, rationale=None, usage=None)
    try:
        d, ms = decide(text)
    except Exception as ex:  # keep the run going; the error is recorded and counted in the summary
        rec["error"] = f"{type(ex).__name__}: {ex}"
        return rec
    a = d.answers[0]
    rec.update(decision_ms=round(ms, 1), total_ms=int(ms),
               usage={"prompt_tokens": d.usage.input_tokens, "completion_tokens": d.usage.output_tokens})
    if a.type != "choice":
        rec["error"] = f"answer type {a.type}"
        return rec
    rec.update(got=a.choice, ok=True, correct=a.choice == want, confidence=a.confidence,
               p={x.value: x.probability for x in a.probabilities},
               rationale=f"Decision API picked {a.choice} (confidence {a.confidence:.2f})")
    return rec

prompts = json.load(open(ROOT / "data" / "prompts.json"))
out = []
# warm-up: one call, not recorded (connection setup)
decide("hello")
for rnd in range(ROUNDS):
    for setname in ("A", "B"):
        for i, (lang, text, want) in enumerate(prompts[setname]):
            rec = record(rnd, setname, i + 1, lang, want, text)
            out.append(rec)
            print(rnd, setname, i + 1, "openai", rec["got"], "OK" if rec["correct"] else "x", rec["decision_ms"], rec["error"] or "", flush=True)
    json.dump(out, open(OUT / f"results_openai_{CATALOG}.json", "w"), ensure_ascii=False, indent=1)
summary = summarize(out, ROUNDS)
json.dump({"openai": summary}, open(OUT / f"summary_openai_{CATALOG}.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False))
