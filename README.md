# RyuLongRise · AI 硬件供应链涨价追踪

AI 算力硬件供应链的结构化公开事实数据库：**涨价官宣**（官方发布日锚定）、**黄仁勋言论时间线**、**前沿技术突破**（成熟度标注）。每条记录一个永久 URL，只增不删，附来源链接。

## 架构

```
data/
  site.json            # 站点配置（名称/描述/base_url）
  chain.json           # 产业链图谱页数据（10 元件）
  hikes/*.json         # 涨价官宣：一条记录 = 一个文件
  jensen/*.json        # 黄仁勋言论
  breakthroughs/*.json # 前沿突破
build.py               # 零依赖静态生成器（Python 3.10+，标准库）
docs/                  # 构建输出（GitHub Pages 发布目录，勿手改）
```

## 日常更新流程（定时任务自动执行）

1. 新增记录：在 `data/hikes/`（或 jensen/breakthroughs）下新建 `YYYY-MM-DD-english-slug.json`，字段参考同目录现有文件；必填：`slug/title/date/summary/source_url` + 类型字段。
2. 构建：`python build.py`
3. 发布：`git add -A && git commit -m "data: ..." && git push`（Pages 自动更新）

## 上线步骤（一次性）

1. 在 GitHub 创建仓库（如 `ryulongrise`），本仓库 `git remote add origin ... && git push -u origin main`
2. 仓库 Settings → Pages → Source 选 `main` 分支 `/docs` 目录
3. **把 `data/site.json` 的 `base_url` 改成真实地址**（如 `https://<用户名>.github.io/ryulongrise`），重新 `python build.py` 并 push——canonical/sitemap/RSS 依赖它
4. 上线后到 Google Search Console / Bing Webmaster 提交 `sitemap.xml`
5. 以后绑定自定义域名：仓库 Pages 设置里填域名 + DNS 加 CNAME，改 `base_url` 重新构建即可

## 内容红线（重要）

公开站**只发布事实类内容**（涨价官宣/言论/突破/产业链映射，全部附来源）。
**禁止**发布：个股买卖点、止损位、仓位建议、操作思路等任何构成投资建议的内容——无牌照公开荐股涉嫌违法。本地私人复盘仪表盘（`D:\RyuLongRise`）与本站物理隔离，其内容不得同步到这里。
