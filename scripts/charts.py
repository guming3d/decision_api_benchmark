"""Render the article's charts as HTML -> PNG, in the style of the Laya article."""
import json, sys, asyncio, statistics as st
from pathlib import Path
from playwright.async_api import async_playwright
ROOT = Path(__file__).resolve().parent.parent
CHARTS = ROOT / "charts"
S = json.load(open(ROOT / 'results' / 'summary.json'))
LANG = sys.argv[1]  # zh | en
E = ["microsoft", "typesafe", "laya", "llm", "openai"]
NAME = {"en": {"microsoft": "Microsoft-Decision-1", "typesafe": "TypeSafe Jev", "laya": "Self-hosted Laya", "llm": "LLM (gpt-4.1-mini)", "openai": "OpenAI Decision API"},
        "zh": {"microsoft": "Microsoft-Decision-1", "typesafe": "TypeSafe Jev", "laya": "自部署 Laya", "llm": "LLM（gpt-4.1-mini）", "openai": "OpenAI Decision API"}}[LANG]
T = {"en": dict(
        acc_t="Correct model picks, 2 × 20 routing requests",
        acc_s="Same 5 models and requests for every engine · mean of 3 runs · 10 English + 10 Chinese per set",
        setA="Set A: the Laya-article requests (easy)", setB="Set B: realistic Copilot-style requests (harder)",
        lat_t="Decision time per request", lat_s="Measured inside Model Router (OpenAI: at the client) · median and 95th percentile · 3 runs × 40 requests per engine",
        p50="median", p95="95th percentile",
        foot="Expected model per request set by hand before the run. Router on Apple M4 Pro in Asia; Foundry and Azure OpenAI in East US 2; Laya on the same Mac. 11 Oct 2026. OpenAI Decision API (gpt-6-luna) called directly from a separate Linux client with its own choice descriptions, 13 Oct 2026.",
        total="total"),
     "zh": dict(
        acc_t="选对模型的次数，2 组 × 20 个路由请求",
        acc_s="五个引擎使用相同的 5 个模型和相同的请求 · 3 轮取平均 · 每组中英文各 10 题",
        setA="A 组：沿用 Laya 那篇的题目（简单）", setB="B 组：贴近 Copilot 日常的提问（更难）",
        lat_t="每次决策耗时", lat_s="在 Model Router 内部计时（OpenAI 在客户端计时）· 中位数与 P95 · 每个引擎 3 轮 × 40 个请求",
        p50="中位数", p95="P95",
        foot="每道题的期望模型在运行前人工定好。路由器跑在亚洲的 Apple M4 Pro 上；Foundry 与 Azure OpenAI 在美国东部 2；Laya 在同一台 Mac 上。2026-10-11。OpenAI Decision API（gpt-6-luna）从另一台 Linux 客户端直连调用，使用自己的选项描述，2026-10-13。",
        total="合计")}[LANG]
CSS = """body{margin:0;background:#fff;font-family:-apple-system,'PingFang SC','Helvetica Neue','Noto Sans CJK SC',sans-serif}
.card{width:1000px;padding:36px 40px 28px;background:#fbfaf8;border:1px solid #e7e5e0;border-radius:18px;box-sizing:border-box}
h1{margin:0 0 8px;font-size:28px;color:#111}.sub{color:#555;font-size:16px;margin-bottom:22px}
.leg{display:flex;gap:24px;font-size:15px;color:#333;margin-bottom:14px}.sw{display:inline-block;width:14px;height:14px;border-radius:4px;margin-right:7px;vertical-align:-2px}
.row{display:grid;grid-template-columns:210px 1fr 90px;align-items:center;margin:16px 0}.lab{font-weight:600;font-size:16px;text-align:right;padding-right:16px;color:#111}
.bars{border-left:1px solid #ccc;padding:2px 0}.bar{height:22px;border-radius:0 7px 7px 0;margin:4px 0;display:flex;align-items:center}
.val{font-size:14px;color:#333;margin-left:8px;white-space:nowrap}.tot{font-weight:700;font-size:17px;text-align:right;color:#111}
.foot{color:#888;font-size:13px;margin-top:20px;line-height:1.5}.hl .lab{color:#0b63c5}"""
A, B = "#2b78d8", "#ec6a35"
def accuracy():
    rows = ""
    for e in E:
        a = st.mean(S[e]["A-ALL"]); b = st.mean(S[e]["B-ALL"])
        fmt = lambda v: (f"{v:.1f}".rstrip('0').rstrip('.'))
        rows += f"""<div class="row{' hl' if e=='microsoft' else ''}"><div class="lab">{NAME[e]}</div><div class="bars">
<div class="bar" style="width:{a/20*100*0.85}%;background:{A}"><span class="val" style="margin-left:calc(100% + 8px)">{fmt(a)}/20</span></div>
<div class="bar" style="width:{b/20*100*0.85}%;background:{B}"><span class="val" style="margin-left:calc(100% + 8px)">{fmt(b)}/20</span></div></div>
<div class="tot">{fmt(a+b)}/40</div></div>"""
    return f"""<div class="card"><h1>{T['acc_t']}</h1><div class="sub">{T['acc_s']}</div>
<div class="leg"><span><span class="sw" style="background:{A}"></span>{T['setA']}</span><span><span class="sw" style="background:{B}"></span>{T['setB']}</span></div>
{rows}<div class="foot">{T['foot']}</div></div>"""
def latency():
    mx = max(S[e]["ms_p95"] for e in E)
    rows = ""
    for e in E:
        p50, p95 = S[e]["ms_p50"], S[e]["ms_p95"]
        f = lambda v: f"{v} ms" if v < 1000 else f"{v/1000:.2f} s"
        rows += f"""<div class="row{' hl' if e=='microsoft' else ''}"><div class="lab">{NAME[e]}</div><div class="bars">
<div class="bar" style="width:{p50/mx*80}%;background:{A}"><span class="val" style="margin-left:calc(100% + 8px)">{f(p50)}</span></div>
<div class="bar" style="width:{p95/mx*80}%;background:#9cc0ef"><span class="val" style="margin-left:calc(100% + 8px)">{f(p95)}</span></div></div><div></div></div>"""
    return f"""<div class="card"><h1>{T['lat_t']}</h1><div class="sub">{T['lat_s']}</div>
<div class="leg"><span><span class="sw" style="background:{A}"></span>{T['p50']}</span><span><span class="sw" style="background:#9cc0ef"></span>{T['p95']}</span></div>
{rows}<div class="foot">{T['foot']}</div></div>"""
COST = json.load(open(ROOT / 'results' / 'cost.json'))
CT = {"en": dict(t="Cost per million routing decisions", s="Measured tokens per decision × list price · USD",
                 laya="$0 per call (runs on your own machine)",
                 foot="Decision-1 and Jev: $0.042 per million input tokens, output free. gpt-4.1-mini: Azure Global Standard $0.40 in / $1.60 out per million. Tokens are the averages billed over the same 40 requests: Decision-1 205 in, Jev 518 in + 82 out (free), LLM 214 in + 35 out. OpenAI Decision API (gpt-6-luna): $0.10 per million input tokens, no output or cache charges; 307 in."),
      "zh": dict(t="每百万次路由决策的费用", s="实测每次决策的 token 数 × 官方单价 · 美元",
                 laya="按次 0 美元（跑在你自己的机器上）",
                 foot="Decision-1 与 Jev：每百万输入 token 0.042 美元，输出免费。gpt-4.1-mini：Azure 全球标准部署，每百万输入 0.40 / 输出 1.60 美元。token 数为同样 40 个请求的计费平均值：Decision-1 输入 205；Jev 输入 518、输出 82（免费）；LLM 输入 214、输出 35。OpenAI Decision API（gpt-6-luna）：每百万输入 token 0.10 美元，输出与缓存不计费；输入 307。")}[LANG]
def cost():
    mx = max(COST[e]["per_million"] for e in E)
    rows = ""
    for e in E:
        v = COST[e]["per_million"]
        label = CT["laya"] if v == 0 else f"${v:.1f}"
        rows += f"""<div class="row{' hl' if e=='microsoft' else ''}"><div class="lab">{NAME[e]}</div><div class="bars">
<div class="bar" style="width:{max(v/mx*80,0.4)}%;background:{'#2b9a5a' if v else '#ccc'}"><span class="val" style="margin-left:calc(100% + 8px)">{label}</span></div></div><div></div></div>"""
    return f"""<div class="card"><h1>{CT['t']}</h1><div class="sub">{CT['s']}</div>{rows}<div class="foot">{CT['foot']}</div></div>"""
async def render(html, out):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(device_scale_factor=2, viewport={"width": 1040, "height": 900})
        await pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{html}</body></html>")
        await pg.locator(".card").screenshot(path=out); await b.close()
asyncio.run(render(accuracy(), CHARTS / f"{LANG}-07-accuracy.png"))
asyncio.run(render(latency(), CHARTS / f"{LANG}-08-latency.png"))
asyncio.run(render(cost(), CHARTS / f"{LANG}-09-cost.png"))
