"""Cost vs accuracy scatter: top-left is best. Renders zh / en PNGs."""
import json, sys, asyncio, statistics as st
from pathlib import Path
from playwright.async_api import async_playwright
LANG = sys.argv[1]
ROOT = Path(__file__).resolve().parent.parent
CHARTS = ROOT / "charts"
S = json.load(open(ROOT / 'results' / 'summary.json')); C = json.load(open(ROOT / 'results' / 'cost.json'))
E = ["microsoft", "typesafe", "laya", "llm", "openai"]
COL = {"microsoft": "#2a78d6", "typesafe": "#eb6834", "laya": "#1baf7a", "llm": "#eda100", "openai": "#7a4fd0"}
NAME = {"en": {"microsoft": "Microsoft-Decision-1", "typesafe": "TypeSafe Jev", "laya": "Self-hosted Laya", "llm": "LLM (gpt-4.1-mini)", "openai": "OpenAI Decision API"},
        "zh": {"microsoft": "Microsoft-Decision-1", "typesafe": "TypeSafe Jev", "laya": "自部署 Laya", "llm": "LLM（gpt-4.1-mini）", "openai": "OpenAI Decision API"}}[LANG]
T = {"en": dict(t="Cost vs accuracy: closer to the top-left is better",
                s="5 decision engines on the same 40 routing requests · accuracy = mean of 3 runs · cost from measured billed tokens",
                x="Cost per million decisions (USD)", y="Correct picks", best="Better: cheaper and more accurate",
                cheaper="cheaper", accurate="more accurate", laya_note="$0 per call, needs your own GPU machine",
                foot="Decision-1 and Jev: $0.042 per million input tokens, output free. gpt-4.1-mini: Azure Global Standard $0.40 / $1.60 per million. OpenAI Decision API (gpt-6-luna): $0.10 per million input tokens, output free. 11–14 Oct 2026."),
     "zh": dict(t="费用 vs 准确率：越靠左上角越好",
                s="5 个决策引擎、同样 40 个路由请求 · 准确率为 3 轮平均 · 费用按实测计费 token 计算",
                x="每百万次决策的费用（美元）", y="选对比例", best="更便宜、更准",
                cheaper="更便宜", accurate="更准", laya_note="按次 0 美元，需自备 GPU 机器",
                foot="Decision-1 与 Jev：每百万输入 token 0.042 美元，输出免费。gpt-4.1-mini：Azure 全球标准部署，每百万输入 0.40 / 输出 1.60 美元。OpenAI Decision API（gpt-6-luna）：每百万输入 token 0.10 美元，输出免费。2026-10-11 至 10-14。")}[LANG]
pts = {e: (C[e]["per_million"], (st.mean(S[e]["A-ALL"]) + st.mean(S[e]["B-ALL"])) / 40 * 100) for e in E}
W, H = 920, 520; L, R, TOP, B = 90, 30, 20, 60
x0, x1, y0, y1 = 0, 160, 40, 104
X = lambda v: L + (v - x0) / (x1 - x0) * (W - L - R)
Y = lambda v: TOP + (y1 - v) / (y1 - y0) * (H - TOP - B)
g = []
# best-corner wash
g.append(f'<defs><radialGradient id="best" cx="0" cy="0" r="1"><stop offset="0" stop-color="#2b9a5a" stop-opacity=".13"/><stop offset="1" stop-color="#2b9a5a" stop-opacity="0"/></radialGradient></defs>')
g.append(f'<rect x="{L}" y="{TOP}" width="{(W-L-R)*0.6}" height="{(H-TOP-B)*0.6}" fill="url(#best)"/>')
g.append(f'<text x="{L+14}" y="{Y(78)}" class="best">↖ {T["best"]}</text>')
for v in range(0, 161, 20):
    g.append(f'<line x1="{X(v)}" x2="{X(v)}" y1="{TOP}" y2="{H-B}" class="grid"/><text x="{X(v)}" y="{H-B+22}" class="tick" text-anchor="middle">${v}</text>')
for v in range(40, 101, 10):
    g.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v)}" y2="{Y(v)}" class="grid"/><text x="{L-10}" y="{Y(v)+5}" class="tick" text-anchor="end">{v}%</text>')
g.append(f'<line x1="{L}" x2="{W-R}" y1="{H-B}" y2="{H-B}" class="axis"/><line x1="{L}" x2="{L}" y1="{TOP}" y2="{H-B}" class="axis"/>')
g.append(f'<text x="{(L+W-R)/2}" y="{H-12}" class="atitle" text-anchor="middle">{T["x"]}　←　{T["cheaper"]}</text>')
g.append(f'<text transform="translate(24,{(TOP+H-B)/2}) rotate(-90)" class="atitle" text-anchor="middle">{T["y"]}　→　{T["accurate"]}</text>')
# label placement: (dx, dy, anchor)
place = {"microsoft": (16, 30, "start"), "typesafe": (0, -36, "middle"), "laya": (16, 6, "start"), "llm": (-16, -16, "end"), "openai": (16, 30, "start")}
for e in E:
    c, a = pts[e]; px, py = X(c), Y(a); dx, dy, anc = place[e]
    cost = ("$0" if c == 0 else f"${c:.1f}")
    g.append(f'<circle cx="{px}" cy="{py}" r="9" fill="{COL[e]}" stroke="#fbfaf8" stroke-width="2.5"/>')
    sub = f'{a:.1f}% · ' + (T["laya_note"] if e == "laya" else cost)
    g.append(f'<text x="{px+dx}" y="{py+dy}" class="lab" text-anchor="{anc}">{NAME[e]}</text>')
    g.append(f'<text x="{px+dx}" y="{py+dy+20}" class="val" text-anchor="{anc}">{sub}</text>')
legend = "".join(f'<span><span class="sw" style="background:{COL[e]}"></span>{NAME[e]}</span>' for e in E)
CSS = """body{margin:0;background:#fff;font-family:-apple-system,'PingFang SC','Helvetica Neue','Noto Sans CJK SC',sans-serif}
.card{width:1000px;padding:36px 40px 28px;background:#fbfaf8;border:1px solid #e7e5e0;border-radius:18px;box-sizing:border-box}
h1{margin:0 0 8px;font-size:28px;color:#111}.sub{color:#555;font-size:16px;margin-bottom:16px}
.leg{display:flex;flex-wrap:wrap;gap:22px;font-size:15px;color:#333;margin-bottom:8px}.sw{display:inline-block;width:12px;height:12px;border-radius:6px;margin-right:7px;vertical-align:-1px}
.grid{stroke:#e9e7e2;stroke-width:1}.axis{stroke:#b9b6ae;stroke-width:1}.tick{font-size:13px;fill:#6b6a64}
.atitle{font-size:14px;fill:#444}.lab{font-size:16px;font-weight:600;fill:#111}.val{font-size:14px;fill:#555}.best{font-size:15px;fill:#2b7a4b;font-weight:600}
.foot{color:#888;font-size:13px;margin-top:10px;line-height:1.5}"""
html = f"""<div class="card"><h1>{T['t']}</h1><div class="sub">{T['s']}</div><div class="leg">{legend}</div>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}">{''.join(g)}</svg><div class="foot">{T['foot']}</div></div>"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(device_scale_factor=2, viewport={"width": 1040, "height": 900})
        await pg.set_content(f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>{html}</body></html>")
        await pg.locator(".card").screenshot(path=CHARTS / f"{LANG}-10-cost-vs-accuracy.png"); await b.close()
asyncio.run(main())
print({e: (round(c, 1), round(a, 1)) for e, (c, a) in pts.items()})
