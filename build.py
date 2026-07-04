# -*- coding: utf-8 -*-
"""RyuLongRise 静态站生成器（零第三方依赖）。

用法：  python build.py
输入：  data/site.json, data/chain.json, data/{hikes,jensen,breakthroughs}/*.json
输出：  docs/  （GitHub Pages 直接以 main 分支 /docs 目录发布）

设计原则：
- 每条记录 = 一个永久 URL（内容只增不删，SEO 复利）
- 全部内容服务端渲染进 HTML，爬虫与 AI 引擎无需执行 JS
- 每页独立 title/description/canonical/OG/JSON-LD；全站 sitemap/RSS/llms.txt
"""
import json
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from html import escape as esc
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "docs"
CST = timezone(timedelta(hours=8))

# ---------------------------------------------------------------- 数据加载

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))

REQUIRED = {
    "hikes": ["slug", "title", "date", "sector", "level", "what", "summary", "source_url"],
    "jensen": ["slug", "title", "date", "quote", "summary", "source_url"],
    "breakthroughs": ["slug", "title", "date", "maturity", "what", "summary", "source_url"],
    "reviews": ["slug", "title", "date", "summary", "market"],
}

def load_entries(kind: str):
    items = []
    for p in sorted((DATA / kind).glob("*.json")):
        it = load_json(p)
        missing = [k for k in REQUIRED[kind] if not it.get(k)]
        if missing:
            sys.exit(f"[build] {p} 缺少字段: {missing}")
        datetime.strptime(it["date"], "%Y-%m-%d")  # 校验日期格式
        items.append(it)
    items.sort(key=lambda x: (x["date"], x["slug"]), reverse=True)
    return items

SITE = load_json(DATA / "site.json")
CHAIN = load_json(DATA / "chain.json")
HIKES = load_entries("hikes")
JENSEN = load_entries("jensen")
BREAKS = load_entries("breakthroughs")
REVIEWS = load_entries("reviews")
BASE = SITE["base_url"].rstrip("/")
TODAY = datetime.now(CST).strftime("%Y-%m-%d")

if "USERNAME" in BASE:
    print("[build] 警告：data/site.json 的 base_url 仍是占位符，"
          "上线前请改成真实地址（影响 canonical/sitemap/RSS）。")

# 反查：涨价记录 -> 产业链环节
HIKE2CHAIN = {}
for c in CHAIN["components"]:
    for s in c.get("related_hikes", []):
        HIKE2CHAIN[s] = c

# ---------------------------------------------------------------- 通用

def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

def d_disp(e) -> str:
    return e.get("date_display") or e["date"]

def rfc822(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=8, tzinfo=CST)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0800")

LEVEL_CLS = {"超级周期": "lv-super", "过热": "lv-super", "强势": "lv-strong",
             "题材": "lv-theme", "启动": "lv-start"}
MAT_CLS = {"实验室": "mt-lab", "中试": "mt-pilot", "产业化临近": "mt-near"}
TAG_CLS = {"高位": "t-high", "强势": "t-strong", "关注": "t-watch", "低位启动": "t-low"}

def badge(text, cls):
    return f'<span class="badge {cls}">{esc(text)}</span>'

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
           "fill='%230a0e14'/%3E%3Cpath d='M8 24 L24 8 M14 8 h10 v10' "
           "stroke='%2376b900' stroke-width='3.5' fill='none' "
           "stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")

CSS = """
:root{--bg:#0a0e14;--panel:#121821;--panel2:#0e141d;--line:#1f2a38;--text:#e6edf3;
--muted:#8b9bb0;--green:#76b900;--red:#ff4d4d;--orange:#ff9f43;--purple:#a974ff;
--blue:#4d9fff;--shadow:0 6px 24px rgba(0,0,0,.35)}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#10202a 0,var(--bg) 60%);
color:var(--text);line-height:1.7;font-family:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:0 18px 60px}
header.top{border-bottom:1px solid var(--line)}
.topin{max-width:1080px;margin:0 auto;padding:16px 18px;display:flex;flex-wrap:wrap;
align-items:baseline;gap:8px 18px}
.logo{font-size:24px;font-weight:800;letter-spacing:.5px;color:var(--text)}
.logo b,.logo .ar{color:var(--green)}.logo:hover{text-decoration:none}
nav.main{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13.5px}
nav.main a{color:var(--muted)}nav.main a:hover{color:var(--text)}
h1{font-size:25px;line-height:1.45;margin:26px 0 10px}
h2{display:flex;align-items:center;gap:9px;font-size:17px;margin:30px 0 12px;flex-wrap:wrap}
h2::before{content:"";width:9px;height:9px;border-radius:50%;background:var(--green);
box-shadow:0 0 10px var(--green);flex:none}
h3{font-size:15.5px;margin:20px 0 8px}
.lead{color:var(--muted);font-size:14.5px;margin:0 0 20px}
.crumb{font-size:12.5px;color:var(--muted);margin-top:20px}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;
color:var(--muted);margin:6px 0 20px}
.sec{background:var(--panel);border:1px solid var(--line);border-radius:13px;
padding:18px 20px;margin:18px 0;box-shadow:var(--shadow)}
.badge{font-size:11.5px;font-weight:700;padding:2px 10px;border-radius:20px;border:1px solid;white-space:nowrap}
.lv-super{color:var(--red);border-color:var(--red);background:rgba(255,77,77,.08)}
.lv-strong{color:var(--orange);border-color:var(--orange);background:rgba(255,159,67,.08)}
.lv-theme{color:var(--purple);border-color:var(--purple);background:rgba(169,116,255,.08)}
.lv-start{color:var(--green);border-color:var(--green);background:rgba(118,185,0,.08)}
.mt-lab{color:var(--muted);border-color:var(--muted)}
.mt-pilot{color:var(--orange);border-color:var(--orange);background:rgba(255,159,67,.08)}
.mt-near{color:var(--green);border-color:var(--green);background:rgba(118,185,0,.08)}
.t-high{color:var(--red);border-color:var(--red);background:rgba(255,77,77,.08)}
.t-strong{color:var(--orange);border-color:var(--orange);background:rgba(255,159,67,.08)}
.t-watch{color:var(--blue);border-color:var(--blue);background:rgba(77,159,255,.08)}
.t-low{color:var(--green);border-color:var(--green);background:rgba(118,185,0,.08)}
.chg{color:var(--red);font-weight:800;letter-spacing:1px}
article p{margin:12px 0;font-size:14.5px}
blockquote{margin:16px 0;padding:11px 14px;border-left:3px solid var(--green);
background:#0c121a;border-radius:0 8px 8px 0;color:#cfe0d2;font-size:14px}
.box{background:#0c121a;border:1px solid var(--line);border-radius:10px;
padding:11px 14px;margin:13px 0;font-size:13.5px}
.box b{color:var(--green)}
.risk{border-left:3px solid var(--orange)}
.risk::before{content:"⚠ ";color:var(--orange)}
.mkt{font-size:13.5px;color:#cfe0d2;background:#0c121a;border:1px solid var(--line);
border-left:3px solid var(--blue);border-radius:0 8px 8px 0;padding:11px 14px;margin:13px 0}
.src{font-size:13px;color:var(--muted);border-top:1px dashed var(--line);
margin-top:24px;padding-top:13px}
.disc{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:14px 0}
th{text-align:left;color:var(--muted);font-size:12.5px;font-weight:600;
border-bottom:1px solid var(--line);padding:8px 10px 8px 0;white-space:nowrap}
td{border-bottom:1px solid var(--line);padding:10px 10px 10px 0;vertical-align:top}
td.nowrap,th.nowrap{white-space:nowrap}
.list-item{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
border-radius:13px;padding:14px 16px;margin:12px 0;box-shadow:var(--shadow);transition:.15s}
.list-item:hover{border-color:#2c3e52;transform:translateY(-1px)}
.list-item h3{margin:0 0 6px;font-size:15.5px}
.list-item .sum{font-size:13px;color:var(--muted);margin:6px 0 0}
.pick{display:flex;flex-wrap:wrap;align-items:center;gap:9px;padding:12px 0;
border-bottom:1px solid var(--line);font-size:13px}
.pick:last-child{border-bottom:none}
.pstock{font-weight:800;font-size:14px;min-width:130px}
.pd{font-size:11px;font-weight:800;padding:2px 9px;border-radius:20px;color:#0a0e14;
background:var(--green);white-space:nowrap}
.pd.weak{background:var(--muted)}
.pline{flex-basis:100%;font-size:12.5px}
.pmoney{color:var(--green);font-weight:600}
.ppos{color:var(--orange)}
.pwhy{color:var(--green);border-left:2px solid var(--green);padding-left:8px}
.psent,.plogic{color:#d7e2ee}
.thermo{background:#0c121a;border:1px solid var(--line);border-radius:11px;padding:13px 15px;margin:13px 0}
.thermo-top{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-bottom:9px;font-size:13.5px}
.temp{font-size:13px;font-weight:800;padding:3px 12px;border-radius:8px;background:var(--green);color:#0a0e14}
.temp-冰点{background:var(--blue)}.temp-回暖,.temp-发酵{background:var(--green)}
.temp-偏热{background:var(--orange)}.temp-过热,.temp-退潮{background:var(--red);color:#fff}
.tmetrics{display:flex;flex-wrap:wrap;gap:8px;font-size:12px}
.tm{background:var(--panel);border:1px solid var(--line);border-radius:7px;padding:3px 9px}
.tm b{color:var(--green)}
.note{font-size:11.5px;color:var(--muted);font-weight:400}
.cat{display:flex;flex-wrap:wrap;align-items:center;gap:9px;padding:10px 0;
border-bottom:1px solid var(--line);font-size:13px}
.cat:last-child{border-bottom:none}
.catwhen{font-size:11.5px;font-weight:800;color:#0a0e14;background:var(--orange);
border-radius:6px;padding:3px 10px;white-space:nowrap}
.catben{font-size:12.5px;color:var(--green);flex-basis:100%}
.catnote{font-size:12.5px;color:var(--orange);flex-basis:100%}
.pn{display:flex;justify-content:space-between;gap:16px;font-size:13.5px;
margin-top:26px;padding-top:14px;border-top:1px solid var(--line)}
footer.bottom{border-top:1px solid var(--line);margin-top:50px;padding:20px 0 0;
font-size:12.5px;color:var(--muted)}
footer.bottom p{margin:6px 0}
.filter{width:100%;background:var(--panel);border:1px solid var(--line);color:var(--text);
border-radius:9px;padding:9px 12px;font-size:14px;margin:10px 0;outline:none}
.filter:focus{border-color:var(--green)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:700px){.grid2{grid-template-columns:1fr}}
.stat{font-size:13px;color:var(--muted)}
.stat b{color:var(--green);font-size:16px}
.comp{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
border-radius:13px;padding:16px 18px;margin:16px 0;box-shadow:var(--shadow)}
.comp h3{margin:0 0 4px}.comp .en{font-size:12px;color:var(--muted)}
.comp p{font-size:14px;margin:8px 0}
.permalink{font-size:12px;color:var(--muted);word-break:break-all}
.dashhead{display:flex;flex-wrap:wrap;align-items:center;gap:14px;margin:26px 0 6px}
.biglogo{font-size:30px;font-weight:800;letter-spacing:.5px}
.biglogo .ryu,.biglogo .arrow{color:var(--green)}.biglogo .arrow{font-size:22px}
.dashhead h1{font-size:14px;color:var(--muted);font-weight:400;margin:0}
.updated{margin-left:auto;font-size:12.5px;color:var(--muted);border:1px solid var(--line);
padding:5px 11px;border-radius:20px;background:var(--panel)}
.updated b{color:var(--green)}
.sub{color:var(--muted);font-size:13px;margin:2px 0 22px;border-bottom:1px solid var(--line);padding-bottom:16px}
.sub .warn{color:var(--orange)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:26px}
@media(max-width:840px){.grid{grid-template-columns:1fr}}
h2.sd{margin:0 0 13px;font-size:16px}h2.sd::before{display:none}
.col h2.sd,.sec h2.sd{margin-top:0}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;flex:none}
.dot.g{background:var(--green);box-shadow:0 0 10px var(--green)}
.dot.r{background:var(--red);box-shadow:0 0 10px var(--red)}
.dot.b{background:var(--blue);box-shadow:0 0 10px var(--blue)}
.dot.y{background:var(--orange);box-shadow:0 0 10px var(--orange)}
.count{font-size:11.5px;color:var(--muted);border:1px solid var(--line);border-radius:10px;padding:1px 8px}
.mlink{font-size:12px;font-weight:400}
.legend{font-size:11.5px;color:var(--muted);background:var(--panel);border:1px solid var(--line);
border-radius:9px;padding:9px 11px;margin-bottom:12px;line-height:1.7}
.legend b{color:var(--text)}
.row{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.mdate{font-size:11.5px;color:var(--muted)}
.jtitle{font-weight:700;font-size:14.5px;margin:6px 0 7px}.jtitle a{color:var(--text)}
.take{font-size:12.5px;color:var(--green);margin-top:9px;display:flex;gap:6px}
.take::before{content:"▸"}
.srcline{font-size:11.5px;color:var(--muted);margin-top:8px}
.sector{font-weight:800;font-size:15px}
.what{font-size:13px;color:#d7e2ee;margin:8px 0}
.leaders{font-size:12.5px;background:#0c121a;border:1px solid var(--line);border-radius:8px;padding:6px 9px;margin:7px 0}
.leaders b{color:var(--green)}
.risk2{font-size:12px;color:var(--orange);margin-top:7px;display:flex;gap:6px}
.risk2::before{content:"⚠"}
.announced{font-size:11px;background:#0c121a;border:1px solid var(--line);border-radius:8px;padding:2px 8px}
.announced b{color:var(--green)}
.fresh{font-size:11px;font-weight:800;padding:2px 9px;border-radius:20px}
.fresh-hot{color:#fff;background:var(--red)}.fresh-new{color:#0a0e14;background:var(--green)}
.fresh-mid{color:#0a0e14;background:var(--orange)}.fresh-old{color:var(--muted);border:1px solid var(--line)}
.card.hot{border-color:rgba(255,77,77,.55);box-shadow:0 0 0 1px rgba(255,77,77,.25),var(--shadow)}
.card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
border-radius:13px;padding:14px 15px;margin-bottom:12px;box-shadow:var(--shadow);transition:.15s}
.card:hover{border-color:#2c3e52;transform:translateY(-1px)}
.brk{padding:12px 0;border-bottom:1px solid var(--line)}
.brk:last-child{border-bottom:none}
.brktitle{font-weight:700;font-size:13.5px;margin-top:6px}.brktitle a{color:var(--text)}
.brkwhat{font-size:12.5px;color:#d7e2ee;margin:7px 0}
.brkimp{font-size:12px;color:var(--green)}
.brkstk{font-size:12px;background:#0c121a;border:1px solid var(--line);border-radius:8px;padding:6px 9px;margin-top:7px}
.brkstk b{color:var(--green)}
.map{margin-top:26px;background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:16px 18px}
.map h3{margin:0 0 12px;font-size:15px}
.chain{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12.5px}
.node{background:#0c121a;border:1px solid var(--line);border-radius:8px;padding:6px 10px;color:var(--text)}
.node b{color:var(--green)}.node:hover{text-decoration:none;border-color:#2c3e52}
.sep{color:var(--muted)}
.empty{color:var(--muted);font-size:13px;padding:20px;text-align:center;border:1px dashed var(--line);border-radius:10px}
.catwhen.soon{background:var(--red);color:#fff}.catwhen.roll{background:var(--muted)}
.cathead{font-size:13.5px;font-weight:700;margin:16px 0 6px;border-top:1px dashed var(--line);padding-top:13px}
"""

NAV = [("index.html", "首页", 0), ("reviews/", "每日复盘", 1), ("hikes/", "涨价数据库", 1),
       ("jensen/", "黄仁勋言论", 1), ("breakthroughs/", "前沿突破", 1),
       ("chain/", "产业链图谱", 1), ("about/", "关于", 1)]

def shell(*, title, desc, path, depth, body, jsonld=None, og_type="website",
          published=None, modified=None):
    """整页 HTML。path 形如 "" / "hikes/" / "hikes/slug/"（canonical 用）。"""
    rel = "../" * depth
    canonical = f"{BASE}/{path}"
    nav = "".join(f'<a href="{rel}{h}">{t}</a>' for h, t, _ in NAV)
    lds = "".join(f'<script type="application/ld+json">{jdump(x)}</script>'
                  for x in (jsonld or []))
    art = ""
    if og_type == "article" and published:
        art = (f'<meta property="article:published_time" content="{published}T08:00:00+08:00">'
               f'<meta property="article:modified_time" content="{modified or published}T08:00:00+08:00">')
    return f"""<!DOCTYPE html>
<html lang="{SITE['lang']}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="icon" href="{FAVICON}">
<link rel="alternate" type="application/rss+xml" title="{esc(SITE['name'])} RSS" href="{BASE}/rss.xml">
<meta name="theme-color" content="#0a0e14">
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:type" content="{og_type}">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary">{art}
{lds}<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="topin">
<a class="logo" href="{rel}index.html"><b>Ryu</b><span class="ar">↗</span>LongRise</a>
<nav class="main">{nav}</nav>
</div></header>
<div class="wrap">
{body}
<footer class="bottom">
<p><b>{esc(SITE['name'])}</b> · {esc(SITE['tagline'])} · 数据更新至 {TODAY}（北京时间）</p>
<p>本站全部内容为公开信息的结构化整理（每条均附来源链接），仅供信息参考与研究，
<b>不构成任何投资建议或证券投资咨询</b>。市场有风险，决策需独立判断。</p>
<p><a href="{rel}about/">关于本站与方法论</a> · <a href="{BASE}/rss.xml">RSS 订阅</a> ·
<a href="{BASE}/data.json">数据下载(JSON)</a> · <a href="{BASE}/llms.txt">llms.txt</a></p>
</footer>
</div>
</body>
</html>"""

def crumb(depth, *parts):
    rel = "../" * depth
    items = [f'<a href="{rel}index.html">首页</a>']
    items += parts
    return '<nav class="crumb">' + " › ".join(items) + "</nav>"

def breadcrumb_ld(path_titles):
    """path_titles: [(url_path, title), ...] 从首页开始。"""
    return {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": t,
             "item": f"{BASE}/{p}"}
            for i, (p, t) in enumerate(path_titles)]}

def article_ld(e, path):
    return {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": e["title"], "description": e["summary"],
        "datePublished": f"{e['date']}T08:00:00+08:00",
        "dateModified": f"{e['date']}T08:00:00+08:00",
        "inLanguage": "zh-CN", "isAccessibleForFree": True,
        "mainEntityOfPage": f"{BASE}/{path}",
        "author": {"@type": "Organization", "name": SITE["name"], "url": f"{BASE}/"},
        "publisher": {"@type": "Organization", "name": SITE["name"], "url": f"{BASE}/"},
    }

def src_block(e, path):
    parts = []
    if e.get("reported") and e["reported"] != e["date"]:
        parts.append(f"官宣日 {esc(d_disp(e))} · 报道日 {esc(e['reported'])}（北京时间）")
    else:
        parts.append(f"日期 {esc(d_disp(e))}（北京时间）")
    name = e.get("source_name") or "来源链接"
    parts.append(f'信息来源：<a href="{esc(e["source_url"])}" target="_blank" '
                 f'rel="noopener">{esc(name)} ↗</a>')
    return (f'<div class="src">{" · ".join(parts)}'
            f'<div class="permalink">本页永久链接：{esc(BASE)}/{esc(path)}</div></div>')

def stocks_box(label, stocks):
    if not stocks:
        return ""
    return (f'<div class="box">📌 {esc(label)}：<b>{esc(stocks)}</b>'
            f'<div class="disc">（公开信息整理·产业链映射，非个股推荐）</div></div>')

def prevnext(items, i, section, depth):
    rel = "../" * depth
    parts = []
    if i + 1 < len(items):  # 列表按时间倒序，下一个 = 更早
        p = items[i + 1]
        parts.append(f'<span>← 更早：<a href="{rel}{section}/{p["slug"]}/">{esc(p["title"])}</a></span>')
    else:
        parts.append("<span></span>")
    if i > 0:
        n = items[i - 1]
        parts.append(f'<span>更新：<a href="{rel}{section}/{n["slug"]}/">{esc(n["title"])}</a> →</span>')
    return f'<div class="pn">{"".join(parts)}</div>'

# ---------------------------------------------------------------- 详情页

def hike_detail(e, i):
    path = f"hikes/{e['slug']}/"
    chain_link = ""
    c = HIKE2CHAIN.get(e["slug"])
    if c:
        chain_link = (f'<p>🗺️ 所属产业链环节：'
                      f'<a href="../../chain/#{c["id"]}">{esc(c["name"])}</a></p>')
    body = (
        crumb(2, '<a href="../">涨价数据库</a>', esc(e["sector"]))
        + f'<article class="sec"><h1>{esc(e["title"])}</h1>'
        + '<div class="meta">'
        + f'<time datetime="{e["date"]}">📅 官宣 {esc(d_disp(e))}</time>'
        + badge(e["level"], LEVEL_CLS.get(e["level"], "lv-theme"))
        + (f'<span class="chg">{esc(e["change"])}</span>' if e.get("change") else "")
        + f'<span>板块：{esc(e["sector"])}</span></div>'
        + f"<h2>发生了什么</h2><p>{esc(e['what'])}</p>"
        + stocks_box("产业链相关上市公司", e.get("leaders"))
        + (f'<h2>风险与后续观察</h2><div class="box risk">{esc(e["risk"])}</div>'
           if e.get("risk") else "")
        + chain_link
        + src_block(e, path)
        + prevnext(HIKES, i, "hikes", 2)
        + "</article>")
    lds = [article_ld(e, path),
           breadcrumb_ld([("", "首页"), ("hikes/", "涨价数据库"), (path, e["title"])])]
    return path, shell(title=f"{e['title']} | {SITE['name']}", desc=e["summary"],
                       path=path, depth=2, body=body, jsonld=lds,
                       og_type="article", published=e["date"])

def jensen_detail(e, i):
    path = f"jensen/{e['slug']}/"
    body = (
        crumb(2, '<a href="../">黄仁勋言论</a>', esc(e["date"]))
        + f'<article class="sec"><h1>{esc(e["title"])}</h1>'
        + '<div class="meta">'
        + f'<time datetime="{e["date"]}">🕒 {esc(e["date"])}</time>'
        + (f'<span>{esc(e["time_note"])}</span>' if e.get("time_note") else "")
        + "</div>"
        + f"<h2>原话</h2><blockquote>{esc(e['quote'])}</blockquote>"
        + (f"<h2>背景与解读</h2><p>{esc(e['take'])}</p>" if e.get("take") else "")
        + stocks_box("A 股产业链相关公司", e.get("stocks"))
        + src_block(e, path)
        + prevnext(JENSEN, i, "jensen", 2)
        + "</article>")
    lds = [article_ld(e, path),
           breadcrumb_ld([("", "首页"), ("jensen/", "黄仁勋言论"), (path, e["title"])])]
    return path, shell(title=f"{e['title']} | {SITE['name']}", desc=e["summary"],
                       path=path, depth=2, body=body, jsonld=lds,
                       og_type="article", published=e["date"])

def break_detail(e, i):
    path = f"breakthroughs/{e['slug']}/"
    body = (
        crumb(2, '<a href="../">前沿突破</a>', esc(d_disp(e)))
        + f'<article class="sec"><h1>{esc(e["title"])}</h1>'
        + '<div class="meta">'
        + f'<time datetime="{e["date"]}">🕒 {esc(d_disp(e))}</time>'
        + badge(f"成熟度：{e['maturity']}", MAT_CLS.get(e["maturity"], "mt-lab"))
        + "</div>"
        + f"<h2>突破内容</h2><p>{esc(e['what'])}</p>"
        + (f"<h2>产业影响评估</h2><p>{esc(e['impact'])}</p>" if e.get("impact") else "")
        + stocks_box("相关方向上市公司", e.get("stocks"))
        + src_block(e, path)
        + prevnext(BREAKS, i, "breakthroughs", 2)
        + "</article>")
    lds = [article_ld(e, path),
           breadcrumb_ld([("", "首页"), ("breakthroughs/", "前沿突破"), (path, e["title"])])]
    return path, shell(title=f"{e['title']} | {SITE['name']}", desc=e["summary"],
                       path=path, depth=2, body=body, jsonld=lds,
                       og_type="article", published=e["date"])

# ---------------------------------------------------------------- 每日复盘

def thermo_html(t):
    if not t:
        return ""
    chips = []
    if t.get("limitUp"):
        chips.append(f'<span class="tm">涨停 <b>{esc(t["limitUp"])}</b> / 跌停 {esc(t.get("limitDown", ""))}</span>')
    if t.get("maxBoard"):
        chips.append(f'<span class="tm">最高 <b>{esc(t["maxBoard"])}</b></span>')
    if t.get("promote"):
        chips.append(f'<span class="tm">连板 {esc(t.get("lianban", ""))} · 晋级 <b>{esc(t["promote"])}</b></span>')
    if t.get("fengban"):
        chips.append(f'<span class="tm">炸板 {esc(t.get("zhaban", ""))} · 封板 {esc(t["fengban"])}</span>')
    if t.get("effect"):
        chips.append(f'<span class="tm">{esc(t["effect"])}</span>')
    return ('<div class="thermo"><div class="thermo-top"><b>🌡️ 市场情绪温度计</b>'
            + (f'<span class="temp temp-{esc(t["temp"])}">{esc(t["temp"])}</span>' if t.get("temp") else "")
            + "</div>"
            + (f'<div class="note" style="margin-bottom:8px">{esc(t["stage"])}</div>' if t.get("stage") else "")
            + f'<div class="tmetrics">{"".join(chips)}</div></div>')

def ladder_html(items):
    rows = ""
    for p in items:
        d = p.get("dragon", "")
        strong = d and ("龙头" in d) and ("非龙头" not in d) and ("跟风" not in d)
        rows += ('<div class="pick"><span class="pstock">' + esc(p["stock"]) + "</span>"
                 + (f'<span class="pd{"" if strong else " weak"}">🐲 {esc(d)}</span>' if d else "")
                 + (f'<span class="badge {TAG_CLS.get(p["tag"], "t-watch")}">{esc(p["tag"])}</span>'
                    if p.get("tag") else "")
                 + (f'<span class="pline pmoney">💰 {esc(p["money"])}</span>' if p.get("money") else "")
                 + (f'<span class="pline psent">🔥 {esc(p["sentiment"])}</span>' if p.get("sentiment") else "")
                 + (f'<span class="pline plogic">🧠 {esc(p["logic"])}</span>' if p.get("logic") else "")
                 + (f'<span class="pline ppos">📍 {esc(p["pos"])}</span>' if p.get("pos") else "")
                 + (f'<span class="pline pwhy">🐲 {esc(p["why"])}</span>' if p.get("why") else "")
                 + "</div>")
    return rows

def cats_html(cz):
    rows = ""
    for c in cz:
        when = c.get("date") or c.get("when") or ""
        extra = f'（{esc(c["when"])}）' if c.get("when") and c.get("date") else ""
        rows += ('<div class="cat"><span class="catwhen">📅 ' + esc(when) + extra + "</span>"
                 + f'<span>{esc(c.get("event", ""))}</span>'
                 + (f'<span class="catben">📈 相关方向：{esc(c["benefit"])}</span>' if c.get("benefit") else "")
                 + (f'<span class="catnote">💡 {esc(c["note"])}</span>' if c.get("note") else "")
                 + "</div>")
    return rows

def review_detail(e, i):
    path = f"reviews/{e['slug']}/"
    ladder = e.get("ladder") or []
    wk = f"（{esc(e['weekday'])}）" if e.get("weekday") else ""
    body = (
        crumb(2, '<a href="../">每日复盘</a>', esc(e["date"]))
        + f'<article class="sec"><h1>{esc(e["title"])}</h1>'
        + '<div class="meta">'
        + f'<time datetime="{e["date"]}">📅 {esc(e["date"])}{wk} 收盘复盘</time>'
        + "<span>北京时间 · 事实性观察记录</span></div>"
        + thermo_html(e.get("thermo"))
        + (f'<div class="mkt">🧭 {esc(e["market"])}</div>' if e.get("market") else "")
        + (f'<h2>📋 涨停梯队与人气标的 <span class="note">（{len(ladder)} 只 · 观察记录，非任何操作建议）</span></h2>'
           + ladder_html(ladder) if ladder else "")
        + ("<h2>📅 催化日历</h2>" + cats_html(e["catalysts"]) if e.get("catalysts") else "")
        + '<div class="box disc">本页为公开行情数据与财经媒体报道的事实性汇总（观察池记录），'
          "不含任何买卖点、仓位或操作建议，亦不构成投资建议；数据以交易所与信息披露原文为准。</div>"
        + f'<div class="src"><div class="permalink">本页永久链接：{esc(BASE)}/{esc(path)}</div></div>'
        + prevnext(REVIEWS, i, "reviews", 2)
        + "</article>")
    lds = [article_ld(e, path),
           breadcrumb_ld([("", "首页"), ("reviews/", "每日复盘"), (path, e["title"])])]
    return path, shell(title=f"{e['title']} | {SITE['name']}", desc=e["summary"],
                       path=path, depth=2, body=body, jsonld=lds,
                       og_type="article", published=e["date"])

def reviews_index():
    path = "reviews/"
    cards = "".join(
        f'<div class="list-item"><h3><a href="{e["slug"]}/">{esc(e["title"])}</a></h3>'
        f'<div class="meta" style="margin:0"><time datetime="{e["date"]}">{esc(e["date"])}</time>'
        + (f'<span class="temp temp-{esc(e["thermo"]["temp"])}" style="font-size:11.5px;padding:2px 10px">'
           f'{esc(e["thermo"]["temp"])}</span>'
           if e.get("thermo", {}).get("temp") else "")
        + f'</div><p class="sum">{esc(e["summary"])}</p></div>'
        for e in REVIEWS)
    body = (crumb(1, "每日复盘")
            + "<h1>A 股每日复盘（事实层）</h1>"
            + '<p class="lead">每个交易日收盘后的复盘记录：市场情绪温度计（涨停/跌停/连板/封板率数据）、'
              "大盘与资金面综述、涨停梯队与人气标的、未来催化日历。全部为公开行情与媒体报道的事实性整理，"
              "<b>不含任何买卖点或操作建议</b>。</p>"
            + f'<p class="stat">共 <b>{len(REVIEWS)}</b> 个交易日 · 收盘后自动更新</p>' + cards)
    lds = [breadcrumb_ld([("", "首页"), (path, "每日复盘")])]
    return path, shell(title=f"A股每日复盘：情绪温度计与涨停梯队记录 | {SITE['name']}",
                       desc="A股每日收盘复盘的事实性记录：情绪温度计（涨停/连板/封板率）、大盘资金面综述、涨停梯队与催化日历，每个交易日收盘后自动更新。",
                       path=path, depth=1, body=body, jsonld=lds)

# ---------------------------------------------------------------- 列表页

def hikes_table(items, link_prefix):
    rows = "".join(
        f'<tr><td class="nowrap"><time datetime="{e["date"]}">{esc(d_disp(e))}</time></td>'
        f'<td class="nowrap">{esc(e["sector"])}</td>'
        f'<td class="nowrap">{badge(e["level"], LEVEL_CLS.get(e["level"], "lv-theme"))}</td>'
        f'<td><a href="{link_prefix}{e["slug"]}/">{esc(e["title"])}</a></td></tr>'
        for e in items)
    return ('<table id="hiketable"><thead><tr><th class="nowrap">官宣日期</th>'
            '<th class="nowrap">板块</th><th class="nowrap">级别</th><th>记录</th>'
            f"</tr></thead><tbody>{rows}</tbody></table>")

FILTER_JS = """<script>
(function(){var f=document.getElementById('f');if(!f)return;
f.addEventListener('input',function(){var q=f.value.trim().toLowerCase();
document.querySelectorAll('#hiketable tbody tr').forEach(function(tr){
tr.style.display=!q||tr.textContent.toLowerCase().indexOf(q)>=0?'':'none';});});})();
</script>"""

def hikes_index():
    path = "hikes/"
    n = len(HIKES)
    span = f"{HIKES[-1]['date']} ~ {HIKES[0]['date']}" if HIKES else "—"
    body = (
        crumb(1, "涨价数据库")
        + "<h1>AI 硬件涨价官宣数据库</h1>"
        + '<p class="lead">收录 AI 算力硬件供应链各环节的<b>官方涨价函 / 调价公告 / 合约价发布</b>，'
        "以官宣日期为准（区别于媒体报道日），每条附来源链接。覆盖 GPU、HBM、存储、PCB、CCL、"
        "MLCC、光模块等十类元件。</p>"
        + f'<p class="stat">共 <b>{n}</b> 条记录 · 时间跨度 {esc(span)} · 每个交易日盘前更新</p>'
        + '<input class="filter" id="f" placeholder="🔍 过滤板块/关键词，如：铜箔、存储、MLCC…">'
        + hikes_table(HIKES, "")
        + '<div class="box disc">字段说明：<b>官宣日</b>=厂商涨价函/公告/合约价的官方发布日；'
        "<b>级别</b>为本站对该环节涨价所处阶段的标注（启动→强势→超级周期），属方法论标签，"
        '详见<a href="../about/">关于页</a>。</div>'
        + FILTER_JS)
    lds = [{
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "AI 硬件涨价官宣数据库",
        "description": "AI 算力硬件供应链（GPU/HBM/存储/PCB/CCL/MLCC/光模块等）涨价官宣的结构化时间线数据库，含官宣日期、涨幅、级别与来源。",
        "url": f"{BASE}/hikes/",
        "creator": {"@type": "Organization", "name": SITE["name"]},
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": f"{BASE}/data.json"}],
    }, breadcrumb_ld([("", "首页"), (path, "涨价数据库")])]
    return path, shell(title=f"AI 硬件涨价官宣数据库 | {SITE['name']}",
                       desc=f"AI 算力硬件供应链涨价官宣的结构化数据库：{n} 条记录，覆盖 HBM、存储、PCB、CCL、MLCC 等环节，按官宣日期收录并附来源。",
                       path=path, depth=1, body=body, jsonld=lds)

def simple_index(path, h1, lead, items, section, title, desc):
    lis = "".join(
        f'<div class="list-item"><h3><a href="{e["slug"]}/">{esc(e["title"])}</a></h3>'
        f'<div class="meta" style="margin:0"><time datetime="{e["date"]}">{esc(d_disp(e))}</time>'
        + (badge(f"成熟度：{e['maturity']}", MAT_CLS.get(e["maturity"], "mt-lab"))
           if e.get("maturity") else "")
        + f'</div><p class="sum">{esc(e["summary"])}</p></div>'
        for e in items)
    body = (crumb(1, h1) + f"<h1>{h1}</h1><p class='lead'>{lead}</p>"
            + f'<p class="stat">共 <b>{len(items)}</b> 条</p>' + lis)
    lds = [breadcrumb_ld([("", "首页"), (path, h1)])]
    return path, shell(title=title, desc=desc, path=path, depth=1, body=body, jsonld=lds)

# ---------------------------------------------------------------- 专题页

def chain_page():
    path = "chain/"
    comps = ""
    for c in CHAIN["components"]:
        rel_links = ""
        rl = [h for h in HIKES if h["slug"] in set(c.get("related_hikes", []))]
        if rl:
            links = " · ".join(f'<a href="../hikes/{h["slug"]}/">{esc(h["title"])}</a>' for h in rl)
            rel_links = f'<p>📈 相关涨价记录：{links}</p>'
        comps += (
            f'<section class="comp" id="{c["id"]}"><h3>{esc(c["name"])} '
            f'<span class="en">{esc(c["en"])}</span></h3>'
            f'<p><b>角色：</b>{esc(c["role"])}</p>'
            f'<p><b>涨价传导逻辑：</b>{esc(c["why_hike"])}</p>'
            f'<p><b>相关上市公司（公开信息整理）：</b>{esc(c["companies"])}</p>'
            + rel_links + "</section>")
    body = (crumb(1, "产业链图谱")
            + "<h1>AI 算力产业链图谱：十类核心元件速查</h1>"
            + f'<p class="lead">{esc(CHAIN["intro"])}</p>' + comps)
    lds = [breadcrumb_ld([("", "首页"), (path, "产业链图谱")])]
    return path, shell(
        title=f"AI 算力产业链图谱：GPU/HBM/PCB/CCL/MLCC 十类元件速查 | {SITE['name']}",
        desc="AI 服务器十类核心元件（GPU、HBM、DRAM/NAND、CPO 光模块、PCB、CCL、MLCC、先进封装、FPC、液冷）的角色、涨价传导逻辑与相关上市公司速查。",
        path=path, depth=1, body=body, jsonld=lds)

def about_page():
    path = "about/"
    body = (
        crumb(1, "关于")
        + f"<h1>关于 {esc(SITE['name'])}</h1>"
        + f"<p class='lead'>{esc(SITE['description'])}</p>"
        + "<h2>本站是什么</h2>"
        + "<p>RyuLongRise 是一个聚焦 <b>AI 算力硬件供应链</b>的公开事实数据库，三条主线：</p>"
        + '<ul><li><a href="../hikes/">涨价官宣数据库</a> —— 各环节厂商的涨价函、调价公告、'
          "合约价发布，以<b>官宣日期</b>为锚点收录；</li>"
          '<li><a href="../jensen/">黄仁勋公开言论时间线</a> —— 英伟达 CEO 在发布会、'
          "财报会、专访中的原话与背景；</li>"
          '<li><a href="../breakthroughs/">全球前沿突破雷达</a> —— 与算力硬件相关的'
          "实验室/中试/产业化技术进展，标注成熟度。</li></ul>"
        + "<h2>方法论</h2>"
        + "<p>每个交易日盘前，自动化流程扫描公开信息源（财经媒体、行业研究机构、厂商公告），"
          "按以下规则收录：</p>"
        + "<ul><li><b>官宣日 vs 报道日</b>：涨价以厂商官方发布日为准，媒体报道日单独标注，"
          "两者分离是本库与普通新闻聚合的核心区别；</li>"
          "<li><b>级别标注</b>：启动（首轮提价）→ 强势（多轮提价、交期拉长）→ "
          "超级周期（价格突破历史高点、供需长期失衡），为本站方法论标签；</li>"
          "<li><b>成熟度标注</b>（前沿突破）：实验室 → 中试 → 产业化临近；</li>"
          "<li>每条记录附<b>来源链接</b>，可回溯核验；</li>"
          "<li>记录只增不删；如有事实性更正，在原条目内注明。</li></ul>"
        + "<h2>AI 使用披露</h2>"
        + "<p>本站内容由 AI 辅助扫描与整理公开信息生成，发布前经人工方法论规则约束"
          "（日期锚定、来源必附、级别标注）。AI 可能出错，请以来源链接的原始信息为准。</p>"
        + "<h2>引用本站</h2>"
        + f"<p>欢迎引用，格式建议：<code>RyuLongRise · AI 硬件供应链涨价追踪，{esc(BASE)}/</code>，"
          "并注明具体条目的永久链接。机器可读数据见 "
          f'<a href="{BASE}/data.json">data.json</a> 与 <a href="{BASE}/llms.txt">llms.txt</a>。</p>'
        + "<h2>免责声明</h2>"
        + "<p>本站全部内容为公开信息的结构化整理，<b>仅供信息参考与研究用途，不构成任何"
          "投资建议、证券投资咨询或个股推荐</b>。页面中出现的上市公司名单仅为产业链映射整理，"
          "不代表任何买卖倾向。市场有风险，投资决策请独立判断并自担风险。</p>")
    lds = [{"@context": "https://schema.org", "@type": "AboutPage",
            "name": f"关于 {SITE['name']}", "url": f"{BASE}/about/",
            "inLanguage": "zh-CN"},
           breadcrumb_ld([("", "首页"), (path, "关于")])]
    return path, shell(title=f"关于本站与方法论 | {SITE['name']}",
                       desc="RyuLongRise 的定位、数据收录方法论（官宣日锚定、级别标注、来源可溯）、AI 使用披露与免责声明。",
                       path=path, depth=1, body=body, jsonld=lds)

CHAIN_STRIP = [("gpu", "GPU", "算力心脏", "→"), ("hbm", "HBM", "显存", "→"),
               ("cpo", "CPO", "光互联", "→"), ("pcb", "PCB", "骨架", "+"),
               ("ccl", "CCL", "覆铜板", "→"), ("sip", "SiP", "封装", "·"),
               ("storage", "DRAM/NAND", "存储", "·"), ("mlcc", "MLCC", "被动", "·"),
               ("fpc", "FPC", "软板", "·"), ("cooling", "液冷", "热管理", "")]

def freshness(date_str):
    """相对构建日的新鲜度徽章（与本地仪表盘逻辑一致）。"""
    try:
        a = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return "日期未知", "fresh-old", 9999
    d = (datetime.strptime(TODAY, "%Y-%m-%d") - a).days
    if d <= 0:
        return "🔥 今日官宣", "fresh-hot", d
    if d == 1:
        return "🟢 昨日官宣", "fresh-new", d
    if d <= 4:
        return f"🟡 {d}天前官宣", "fresh-mid", d
    return f"⚪ 已发酵 {d} 天", "fresh-old", d

def cats_home_html(cz, rdate):
    """催化提示（相对复盘日的 T-N 倒计时，与本地仪表盘一致）。"""
    rd = datetime.strptime(rdate, "%Y-%m-%d")
    rows = ""
    for c in cz:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", c.get("date") or "")
        cls = ""
        if m:
            d = (datetime(int(m[1]), int(m[2]), int(m[3])) - rd).days
            if d > 0:
                bdg = f"⏳ T-{d}天（{m[0]}）"
                cls = " soon" if d <= 2 else ""
            elif d == 0:
                bdg = f"🔔 今日（{m[0]}）"
                cls = " soon"
            else:
                bdg = f"✅ 已发生（{m[0]}）"
        else:
            bdg = "📅 " + (c.get("when") or c.get("date") or "")
            cls = " roll"
        rows += (f'<div class="cat"><span class="catwhen{cls}">{esc(bdg)}</span>'
                 f'<span>{esc(c.get("event", ""))}</span>'
                 + (f'<span class="catben">📈 相关方向：{esc(c["benefit"])}</span>' if c.get("benefit") else "")
                 + (f'<span class="catnote">💡 {esc(c["note"])}</span>' if c.get("note") else "")
                 + "</div>")
    return rows

HOME_FILTER_JS = """<script>
(function(){var f=document.getElementById('f');if(!f)return;
f.addEventListener('input',function(){var q=f.value.trim().toLowerCase();
document.querySelectorAll('#hikes .card').forEach(function(c){
c.style.display=!q||c.textContent.toLowerCase().indexOf(q)>=0?'':'none';});});})();
</script>"""

def home_page():
    # 每日复盘精选（事实层）
    if REVIEWS:
        r = REVIEWS[0]
        ladder = r.get("ladder") or []
        cats = r.get("catalysts") or []
        wk = f"（{esc(r['weekday'])}）" if r.get("weekday") else ""
        review_sec = (
            '<section class="sec">'
            f'<h2 class="sd"><span class="dot y"></span>📋 每日复盘精选 <span class="count">{len(ladder)} 只</span> '
            '<span class="note">（涨+资金+逻辑+位置+龙头+人气+接力；观察池·事实层，非买入指令）</span> '
            f'<span class="mlink"><a href="reviews/{r["slug"]}/">本日永久页 →</a> · <a href="reviews/">归档 →</a></span></h2>'
            + thermo_html(r.get("thermo"))
            + (f'<div class="mkt">🧭 {esc(r["market"])}<br>'
               f'<span class="note">复盘日：{esc(r["date"])}{wk}（北京时间）</span></div>' if r.get("market") else "")
            + ladder_html(ladder)
            + (('<div class="cathead">📅 催化提示（相对时间）</div>' + cats_home_html(cats, r["date"]))
               if cats else "")
            + "</section>")
    else:
        review_sec = '<section class="sec"><div class="empty">暂无复盘记录（盘后定时任务会自动生成）。</div></section>'

    jcards = "".join(
        '<div class="card"><div class="row"><span class="mdate">🕒 ' + esc(e["date"])
        + (" · " + esc(e["time_note"]) if e.get("time_note") else "（北京时间）") + "</span></div>"
        + f'<div class="jtitle"><a href="jensen/{e["slug"]}/">{esc(e["title"])}</a></div>'
        + f'<blockquote>“{esc(e["quote"])}”</blockquote>'
        + (f'<div class="take">{esc(e["take"])}</div>' if e.get("take") else "")
        + (f'<div class="leaders">📈 A股产业链相关公司：<b>{esc(e["stocks"])}</b></div>' if e.get("stocks") else "")
        + f'<div class="srcline">来源：<a href="{esc(e["source_url"])}" target="_blank" rel="noopener">'
          f'{esc(e.get("source_name") or "链接")} ↗</a> · <a href="jensen/{e["slug"]}/">详情 →</a></div></div>'
        for e in JENSEN)

    hcards = ""
    for e in HIKES:
        label, cls, d = freshness(e["date"])
        hcards += ('<div class="card' + (" hot" if d <= 0 else "") + '">'
                   + f'<div class="row"><span class="sector">{esc(e["sector"])}</span>'
                     f'<span class="chg" style="margin-left:auto">{esc(e.get("change") or "")}</span></div>'
                   + f'<div class="row" style="margin-top:7px;gap:7px"><span class="fresh {cls}">{label}</span>'
                   + f'<span class="announced">📅 官宣 <b>{esc(d_disp(e))}</b> 北京时间</span>'
                   + badge(e["level"], LEVEL_CLS.get(e["level"], "lv-theme")) + "</div>"
                   + f'<div class="what">{esc(e["what"])}</div>'
                   + (f'<div class="leaders">龙头：<b>{esc(e["leaders"])}</b></div>' if e.get("leaders") else "")
                   + (f'<div class="risk2">{esc(e["risk"])}</div>' if e.get("risk") else "")
                   + '<div class="srcline">'
                   + (f'报道日 {esc(e["reported"])}（北京时间） · ' if e.get("reported") else "")
                   + f'<a href="hikes/{e["slug"]}/">详情 →</a> · '
                     f'<a href="{esc(e["source_url"])}" target="_blank" rel="noopener">来源 ↗</a></div></div>')

    brows = "".join(
        '<div class="brk"><div class="row"><span class="mdate">🕒 ' + esc(d_disp(e)) + "（北京时间）</span>"
        + badge(f"成熟度：{e['maturity']}", MAT_CLS.get(e["maturity"], "mt-lab")) + "</div>"
        + f'<div class="brktitle"><a href="breakthroughs/{e["slug"]}/">{esc(e["title"])}</a></div>'
        + f'<div class="brkwhat">{esc(e["what"])}</div>'
        + (f'<div class="brkimp">▸ {esc(e["impact"])}</div>' if e.get("impact") else "")
        + (f'<div class="brkstk">📈 相关方向：<b>{esc(e["stocks"])}</b></div>' if e.get("stocks") else "")
        + f'<div class="srcline">来源：<a href="{esc(e["source_url"])}" target="_blank" rel="noopener">'
          f'{esc(e.get("source_name") or "链接")} ↗</a> · <a href="breakthroughs/{e["slug"]}/">详情 →</a></div></div>'
        for e in BREAKS)

    nodes = ""
    for cid, nm, role, sep in CHAIN_STRIP:
        nodes += f'<a class="node" href="chain/#{cid}"><b>{nm}</b> {role}</a>'
        if sep:
            nodes += f'<span class="sep">{sep}</span>'

    body = (
        '<div class="dashhead">'
        '<div class="biglogo"><span class="ryu">Ryu</span><span class="arrow">↗</span>LongRise</div>'
        "<h1>复盘精选 × 催化提示 × 黄仁勋雷达 × 涨价</h1>"
        f'<div class="updated">数据更新：<b>{TODAY}</b>（北京时间）</div></div>'
        '<div class="sub">全部日期为<b>北京时间</b> · 仅作信息梳理，<span class="warn">不构成任何投资建议</span></div>'
        + review_sec
        + '<div class="grid"><section class="col">'
        + f'<h2 class="sd"><span class="dot g"></span>黄仁勋雷达 <span class="count">{len(JENSEN)} 条</span> '
          '<span class="mlink"><a href="jensen/">归档 →</a></span></h2>'
        + '<div class="legend">📌 每条言论已附 <b>A 股产业链相关公司</b>（公开信息整理）；'
          "日期为<b>北京时间</b>（美国事件已换算/注明）。</div>"
        + jcards
        + '</section><section class="col">'
        + f'<h2 class="sd"><span class="dot r"></span>涨价官宣雷达 <span class="count">{len(HIKES)} 个板块</span> '
          '<span class="mlink"><a href="hikes/">数据库 →</a></span></h2>'
        + '<div class="legend">📅 <b>官宣日</b>（北京时间）= 涨价函/调价公告官方发布日。'
          "🔥今日 · 🟢昨日 · 🟡数日内=较新；⚪已发酵=发布已有时日。</div>"
        + '<input class="filter" id="f" placeholder="🔍 过滤板块/材料/龙头，如：铜箔、存储、电子布…">'
        + f'<div id="hikes">{hcards}</div>'
        + "</section></div>"
        + '<section class="sec">'
        + f'<h2 class="sd"><span class="dot y"></span>🔬 全球前沿突破雷达 <span class="count">{len(BREAKS)} 条</span> '
          '<span class="note">（实验室突破 ≠ 立即可投资，看成熟度）</span> '
          '<span class="mlink"><a href="breakthroughs/">归档 →</a></span></h2>'
        + brows + "</section>"
        + '<div class="map"><h3>🗺️ AI 算力产业链速查（10 元件）'
          '<span class="mlink"> · <a href="chain/">图谱详情 →</a></span></h3>'
        + f'<div class="chain">{nodes}</div></div>'
        + HOME_FILTER_JS)
    lds = [{"@context": "https://schema.org", "@type": "WebSite",
            "name": SITE["name"], "alternateName": SITE["tagline"],
            "url": f"{BASE}/", "inLanguage": "zh-CN",
            "description": SITE["description"]},
           {"@context": "https://schema.org", "@type": "Organization",
            "name": SITE["name"], "url": f"{BASE}/"}]
    return "", shell(title=f"{SITE['name']} · 复盘精选 × 催化提示 × 黄仁勋雷达 × 涨价｜{SITE['tagline']}",
                     desc=SITE["description"], path="", depth=0, body=body, jsonld=lds)

def notfound_page():
    body = ('<h1>404 · 页面不存在</h1><p class="lead">这条链接可能已失效。'
            f'去<a href="{BASE}/">首页</a>或<a href="{BASE}/hikes/">涨价数据库</a>看看。</p>')
    return "404.html", shell(title=f"404 | {SITE['name']}", desc="页面不存在",
                             path="404.html", depth=0, body=body)

# ---------------------------------------------------------------- 站点级文件

def all_pages_for_sitemap():
    pages = [("", TODAY), ("reviews/", REVIEWS[0]["date"] if REVIEWS else TODAY),
             ("hikes/", HIKES[0]["date"] if HIKES else TODAY),
             ("jensen/", JENSEN[0]["date"] if JENSEN else TODAY),
             ("breakthroughs/", BREAKS[0]["date"] if BREAKS else TODAY),
             ("chain/", TODAY), ("about/", TODAY)]
    pages += [(f"reviews/{e['slug']}/", e["date"]) for e in REVIEWS]
    pages += [(f"hikes/{e['slug']}/", e["date"]) for e in HIKES]
    pages += [(f"jensen/{e['slug']}/", e["date"]) for e in JENSEN]
    pages += [(f"breakthroughs/{e['slug']}/", e["date"]) for e in BREAKS]
    return pages

def sitemap_xml():
    urls = "".join(
        f"<url><loc>{BASE}/{p}</loc><lastmod>{d}</lastmod></url>"
        for p, d in all_pages_for_sitemap())
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + urls + "</urlset>")

def rss_xml():
    feed = ([("涨价官宣", "hikes", e) for e in HIKES]
            + [("黄仁勋言论", "jensen", e) for e in JENSEN]
            + [("前沿突破", "breakthroughs", e) for e in BREAKS]
            + [("每日复盘", "reviews", e) for e in REVIEWS])
    feed.sort(key=lambda t: t[2]["date"], reverse=True)
    items = "".join(
        f"<item><title>[{tag}] {esc(e['title'])}</title>"
        f"<link>{BASE}/{sec}/{e['slug']}/</link>"
        f"<guid isPermaLink=\"true\">{BASE}/{sec}/{e['slug']}/</guid>"
        f"<pubDate>{rfc822(e['date'])}</pubDate>"
        f"<description>{esc(e['summary'])}</description></item>"
        for tag, sec, e in feed[:30])
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0"><channel>'
            f"<title>{esc(SITE['name'])} · {esc(SITE['tagline'])}</title>"
            f"<link>{BASE}/</link>"
            f"<description>{esc(SITE['description'])}</description>"
            f"<language>zh-cn</language><lastBuildDate>{rfc822(TODAY)}</lastBuildDate>"
            + items + "</channel></rss>")

def robots_txt():
    return f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n"

def llms_txt():
    lines = [f"# {SITE['name']} · {SITE['tagline']}", "",
             f"> {SITE['description']}", "",
             "本站是 AI 算力硬件供应链的结构化公开事实数据库：涨价官宣（以厂商官方发布日为锚点）、",
             "黄仁勋公开言论时间线、前沿技术突破（标注成熟度）。每条记录附日期与来源链接。",
             "全部数据可从 /data.json 获取机器可读版本。引用时请使用条目的永久链接。", "",
             "## 涨价官宣数据库", ""]
    lines += [f"- [{e['title']}]({BASE}/hikes/{e['slug']}/): {e['summary']}" for e in HIKES]
    lines += ["", "## 黄仁勋言论时间线", ""]
    lines += [f"- [{e['title']}]({BASE}/jensen/{e['slug']}/): {e['summary']}" for e in JENSEN]
    lines += ["", "## 前沿突破", ""]
    lines += [f"- [{e['title']}]({BASE}/breakthroughs/{e['slug']}/): {e['summary']}" for e in BREAKS]
    lines += ["", "## A股每日复盘（事实层，无操作建议）", ""]
    lines += [f"- [{e['title']}]({BASE}/reviews/{e['slug']}/): {e['summary']}" for e in REVIEWS]
    lines += ["", "## 专题", "",
              f"- [产业链图谱]({BASE}/chain/): AI 服务器十类核心元件的角色、涨价传导逻辑与相关公司",
              f"- [关于与方法论]({BASE}/about/): 收录规则、官宣日/报道日定义、级别与成熟度标注", ""]
    return "\n".join(lines)

def data_json():
    return json.dumps({
        "site": {k: SITE[k] for k in ("name", "tagline", "description")},
        "generated": TODAY, "base_url": BASE,
        "hikes": HIKES, "jensen": JENSEN, "breakthroughs": BREAKS, "reviews": REVIEWS,
    }, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 主流程

def write(path_str: str, content: str):
    p = OUT / path_str
    if path_str.endswith("/") or path_str == "":
        p = OUT / path_str / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")

def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    pages = [home_page(), hikes_index(), chain_page(), about_page(), notfound_page()]
    pages.append(simple_index(
        "jensen/", "黄仁勋公开言论时间线",
        "英伟达 CEO 黄仁勋在发布会、财报会、股东大会与专访中的公开言论，"
        "按北京时间收录原话、背景解读与产业链映射，每条附来源。",
        JENSEN, "jensen",
        f"黄仁勋公开言论时间线 | {SITE['name']}",
        "黄仁勋（Jensen Huang）公开言论的结构化时间线：发布会、财报会、股东大会、专访原话，按日期收录并附来源链接。"))
    pages.append(simple_index(
        "breakthroughs/", "全球前沿突破雷达",
        "与 AI 算力硬件相关的全球技术突破：芯片、封装、散热、光子计算、推理加速等，"
        "标注成熟度（实验室 → 中试 → 产业化临近）。实验室突破 ≠ 立即可投资。",
        BREAKS, "breakthroughs",
        f"全球前沿突破雷达：AI 算力硬件技术进展 | {SITE['name']}",
        "AI 算力硬件相关的全球前沿技术突破时间线，标注成熟度（实验室/中试/产业化临近），覆盖芯片、封装、散热、光子计算等方向。"))
    for i, e in enumerate(HIKES):
        pages.append(hike_detail(e, i))
    for i, e in enumerate(JENSEN):
        pages.append(jensen_detail(e, i))
    for i, e in enumerate(BREAKS):
        pages.append(break_detail(e, i))
    pages.append(reviews_index())
    for i, e in enumerate(REVIEWS):
        pages.append(review_detail(e, i))

    for path, html in pages:
        write(path, html)
    (OUT / "sitemap.xml").write_text(sitemap_xml(), encoding="utf-8")
    (OUT / "rss.xml").write_text(rss_xml(), encoding="utf-8")
    (OUT / "robots.txt").write_text(robots_txt(), encoding="utf-8")
    (OUT / "llms.txt").write_text(llms_txt(), encoding="utf-8")
    (OUT / "data.json").write_text(data_json(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    if SITE.get("indexnow_key"):
        k = SITE["indexnow_key"]
        (OUT / f"{k}.txt").write_text(k, encoding="utf-8")

    n_pages = len(pages)
    print(f"[build] 完成：{n_pages} 个页面 + sitemap/rss/robots/llms.txt/data.json → {OUT}")
    print(f"[build] 记录数：复盘 {len(REVIEWS)} · 涨价 {len(HIKES)} · 言论 {len(JENSEN)} · 突破 {len(BREAKS)}")

if __name__ == "__main__":
    main()
