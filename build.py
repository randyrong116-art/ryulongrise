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

def badge(text, cls):
    return f'<span class="badge {cls}">{esc(text)}</span>'

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
           "viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' "
           "fill='%230a0e14'/%3E%3Cpath d='M8 24 L24 8 M14 8 h10 v10' "
           "stroke='%2376b900' stroke-width='3.5' fill='none' "
           "stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")

CSS = """
:root{--bg:#0a0e14;--panel:#121821;--panel2:#0e141d;--line:#1f2a38;--text:#e6edf3;
--muted:#8b9bb0;--green:#76b900;--red:#ff4d4d;--orange:#ff9f43;--blue:#4d9fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);line-height:1.75;
font-family:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:860px;margin:0 auto;padding:0 18px 60px}
header.top{border-bottom:1px solid var(--line);background:var(--panel2)}
.topin{max-width:860px;margin:0 auto;padding:14px 18px;display:flex;flex-wrap:wrap;
align-items:baseline;gap:8px 18px}
.logo{font-size:20px;font-weight:800;color:var(--text)}
.logo b{color:var(--green)}.logo:hover{text-decoration:none}
nav.main{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13.5px}
nav.main a{color:var(--muted)}nav.main a:hover{color:var(--text)}
h1{font-size:26px;line-height:1.4;margin:28px 0 10px}
h2{font-size:19px;margin:34px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:22px 0 8px}
.lead{color:var(--muted);font-size:15px;margin:0 0 24px}
.crumb{font-size:12.5px;color:var(--muted);margin-top:20px}
.meta{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;
color:var(--muted);margin:6px 0 22px}
.badge{font-size:12px;font-weight:700;padding:2px 10px;border-radius:20px;border:1px solid}
.lv-super{color:var(--red);border-color:var(--red);background:rgba(255,77,77,.08)}
.lv-strong{color:var(--orange);border-color:var(--orange);background:rgba(255,159,67,.08)}
.lv-theme{color:#a974ff;border-color:#a974ff;background:rgba(169,116,255,.08)}
.lv-start{color:var(--green);border-color:var(--green);background:rgba(118,185,0,.08)}
.mt-lab{color:var(--muted);border-color:var(--muted)}
.mt-pilot{color:var(--orange);border-color:var(--orange);background:rgba(255,159,67,.08)}
.mt-near{color:var(--green);border-color:var(--green);background:rgba(118,185,0,.08)}
.chg{color:var(--red);font-weight:800;letter-spacing:1px}
article p{margin:12px 0}
blockquote{margin:16px 0;padding:12px 16px;border-left:3px solid var(--green);
background:var(--panel);border-radius:0 8px 8px 0;color:#cfe0d2}
.box{background:var(--panel);border:1px solid var(--line);border-radius:10px;
padding:12px 16px;margin:14px 0;font-size:14px}
.box b{color:var(--green)}
.risk{border-left:3px solid var(--orange)}
.risk::before{content:"⚠ ";color:var(--orange)}
.src{font-size:13px;color:var(--muted);border-top:1px dashed var(--line);
margin-top:26px;padding-top:14px}
.disc{font-size:12px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:14px;margin:16px 0}
th{text-align:left;color:var(--muted);font-size:12.5px;font-weight:600;
border-bottom:1px solid var(--line);padding:8px 10px 8px 0;white-space:nowrap}
td{border-bottom:1px solid var(--line);padding:10px 10px 10px 0;vertical-align:top}
td.nowrap,th.nowrap{white-space:nowrap}
.list-item{padding:16px 0;border-bottom:1px solid var(--line)}
.list-item h3{margin:0 0 6px;font-size:16px}
.list-item .sum{font-size:13.5px;color:var(--muted);margin:6px 0 0}
.pn{display:flex;justify-content:space-between;gap:16px;font-size:13.5px;
margin-top:30px;padding-top:14px;border-top:1px solid var(--line)}
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
.comp{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:16px 18px;margin:16px 0}
.comp h3{margin:0 0 4px}.comp .en{font-size:12px;color:var(--muted)}
.comp p{font-size:14px;margin:8px 0}
.permalink{font-size:12px;color:var(--muted);word-break:break-all}
"""

NAV = [("index.html", "首页", 0), ("hikes/", "涨价数据库", 1), ("jensen/", "黄仁勋言论", 1),
       ("breakthroughs/", "前沿突破", 1), ("chain/", "产业链图谱", 1), ("about/", "关于", 1)]

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
<a class="logo" href="{rel}index.html"><b>Ryu</b>↗LongRise</a>
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
        + f"<article><h1>{esc(e['title'])}</h1>"
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
        + f"<article><h1>{esc(e['title'])}</h1>"
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
        + f"<article><h1>{esc(e['title'])}</h1>"
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

def home_page():
    latest_j = "".join(
        f'<div class="list-item"><h3><a href="jensen/{e["slug"]}/">{esc(e["title"])}</a></h3>'
        f'<div class="meta" style="margin:0"><time datetime="{e["date"]}">{esc(e["date"])}</time></div></div>'
        for e in JENSEN[:3])
    latest_b = "".join(
        f'<div class="list-item"><h3><a href="breakthroughs/{e["slug"]}/">{esc(e["title"])}</a></h3>'
        f'<div class="meta" style="margin:0"><time datetime="{e["date"]}">{esc(d_disp(e))}</time>'
        + badge(f"成熟度：{e['maturity']}", MAT_CLS.get(e["maturity"], "mt-lab"))
        + "</div></div>"
        for e in BREAKS[:3])
    body = (
        f"<h1>{esc(SITE['name'])} · {esc(SITE['tagline'])}</h1>"
        + f'<p class="lead">{esc(SITE["description"])}</p>'
        + f'<p class="stat">涨价记录 <b>{len(HIKES)}</b> 条 · 言论 <b>{len(JENSEN)}</b> 条 · '
          f'前沿突破 <b>{len(BREAKS)}</b> 条 · 更新至 {TODAY}</p>'
        + f'<h2>📈 最新涨价官宣 <span class="stat">（<a href="hikes/">进入数据库 →</a>）</span></h2>'
        + hikes_table(HIKES[:6], "hikes/")
        + f'<h2>🎙️ 黄仁勋最新言论 <span class="stat">（<a href="jensen/">全部时间线 →</a>）</span></h2>'
        + latest_j
        + f'<h2>🔬 前沿突破 <span class="stat">（<a href="breakthroughs/">全部记录 →</a>）</span></h2>'
        + latest_b
        + '<h2>🗺️ 产业链速查</h2>'
        + '<p>GPU → HBM → CPO/光模块 → PCB + CCL → 先进封装 · DRAM/NAND · MLCC · FPC · 液冷 —— '
          '十类元件的角色与涨价传导逻辑，见<a href="chain/">产业链图谱</a>。</p>')
    lds = [{"@context": "https://schema.org", "@type": "WebSite",
            "name": SITE["name"], "alternateName": SITE["tagline"],
            "url": f"{BASE}/", "inLanguage": "zh-CN",
            "description": SITE["description"]},
           {"@context": "https://schema.org", "@type": "Organization",
            "name": SITE["name"], "url": f"{BASE}/"}]
    return "", shell(title=f"{SITE['name']} · {SITE['tagline']}｜涨价官宣数据库",
                     desc=SITE["description"], path="", depth=0, body=body, jsonld=lds)

def notfound_page():
    body = ('<h1>404 · 页面不存在</h1><p class="lead">这条链接可能已失效。'
            f'去<a href="{BASE}/">首页</a>或<a href="{BASE}/hikes/">涨价数据库</a>看看。</p>')
    return "404.html", shell(title=f"404 | {SITE['name']}", desc="页面不存在",
                             path="404.html", depth=0, body=body)

# ---------------------------------------------------------------- 站点级文件

def all_pages_for_sitemap():
    pages = [("", TODAY), ("hikes/", HIKES[0]["date"] if HIKES else TODAY),
             ("jensen/", JENSEN[0]["date"] if JENSEN else TODAY),
             ("breakthroughs/", BREAKS[0]["date"] if BREAKS else TODAY),
             ("chain/", TODAY), ("about/", TODAY)]
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
            + [("前沿突破", "breakthroughs", e) for e in BREAKS])
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
    lines += ["", "## 专题", "",
              f"- [产业链图谱]({BASE}/chain/): AI 服务器十类核心元件的角色、涨价传导逻辑与相关公司",
              f"- [关于与方法论]({BASE}/about/): 收录规则、官宣日/报道日定义、级别与成熟度标注", ""]
    return "\n".join(lines)

def data_json():
    return json.dumps({
        "site": {k: SITE[k] for k in ("name", "tagline", "description")},
        "generated": TODAY, "base_url": BASE,
        "hikes": HIKES, "jensen": JENSEN, "breakthroughs": BREAKS,
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

    for path, html in pages:
        write(path, html)
    (OUT / "sitemap.xml").write_text(sitemap_xml(), encoding="utf-8")
    (OUT / "rss.xml").write_text(rss_xml(), encoding="utf-8")
    (OUT / "robots.txt").write_text(robots_txt(), encoding="utf-8")
    (OUT / "llms.txt").write_text(llms_txt(), encoding="utf-8")
    (OUT / "data.json").write_text(data_json(), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    n_pages = len(pages)
    print(f"[build] 完成：{n_pages} 个页面 + sitemap/rss/robots/llms.txt/data.json → {OUT}")
    print(f"[build] 记录数：涨价 {len(HIKES)} · 言论 {len(JENSEN)} · 突破 {len(BREAKS)}")

if __name__ == "__main__":
    main()
