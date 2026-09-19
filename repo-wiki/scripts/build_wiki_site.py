#!/usr/bin/env python3
"""repo-wiki 插件构建器 — 纯本地、零网络、仅标准库。

子命令:
  build          --wiki <dir>                       由 wiki.json 构建自包含 site/index.html
  import-legacy  <hash|path> [--dest <dir>]         导入旧版 ~/.zcode/v2/repo-wiki/<hash> 并构建
  selfcheck      --wiki <dir>                       树完整性 + 零外链校验 (exit 0/1)
"""
import argparse
import html
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

HOME = Path.home()
LEGACY_BASE = HOME / ".zcode" / "v2" / "repo-wiki"
MERMAID_PATH = Path(__file__).resolve().parent.parent / "assets" / "mermaid.min.js"

# ---------------------------------------------------------------- markdown

def _inline(s: str) -> str:
    stash: list[str] = []

    def _stash(m):
        stash.append(m.group(1))
        return f"\x00{len(stash) - 1}\x00"

    s = re.sub(r"`([^`]+)`", _stash, s)
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
               lambda m: f'<span class="imgref" title="{m.group(2)}">🖼 {m.group(1) or "图片"}（离线查看器不加载外部图片）</span>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               lambda m: f'<span class="linkref" title="{m.group(2)}">{m.group(1)}</span>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\x00(\d+)\x00",
               lambda m: "<code>" + html.escape(stash[int(m.group(1))], quote=False) + "</code>", s)
    return s


def _list_html(items, pos, depth):
    ordered = items[pos][1]
    tag = "ol" if ordered else "ul"
    out = [f"<{tag}>"]
    while pos < len(items):
        d, _o, text = items[pos]
        if d < depth:
            break
        if d == depth and pos + 1 < len(items) and items[pos + 1][0] > depth:
            sub, pos = _list_html(items, pos + 1, depth + 1)
            out.append(f"<li>{_inline(text)}{sub}</li>")
        else:
            out.append(f"<li>{_inline(text)}</li>")
            pos += 1
    out.append(f"</{tag}>")
    return "".join(out), pos


def md_to_html(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r"^\s*```(\w*)\s*$", line)
        if m:
            lang, buf = m.group(1).lower(), []
            i += 1
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(buf)
            if lang == "mermaid":
                out.append('<pre class="mermaid">' + html.escape(code) + "</pre>")
            else:
                lab = f'<span class="lang">{html.escape(lang)}</span>' if lang else ""
                out.append(f'<pre class="code">{lab}<code>{html.escape(code)}</code></pre>')
            continue
        if re.match(r"^\s*<svg\b", line):
            buf = [line]
            i += 1
            while i < n and "</svg>" not in lines[i]:
                buf.append(lines[i])
                i += 1
            if i < n:
                buf.append(lines[i])
                i += 1
            out.append('<div class="diagram">' + "\n".join(buf) + "</div>")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            lv = len(m.group(1))
            out.append(f"<h{lv}>{_inline(m.group(2))}</h{lv}>")
            i += 1
            continue
        if re.match(r"^\s*([-*_])\s*(\1\s*){2,}$", line):
            out.append("<hr>")
            i += 1
            continue
        if "|" in line and i + 1 < n and re.match(r"^\s*\|?[\s:|-]*-", lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            th = "".join(f"<th>{_inline(c)}</th>" for c in header)
            tr = "".join("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>")
            continue
        if re.match(r"^\s*>", line):
            buf = []
            while i < n and re.match(r"^\s*>", lines[i]):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + md_to_html("\n".join(buf)) + "</blockquote>")
            continue
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", line)
        if m:
            items = []
            while i < n:
                mm = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", lines[i])
                if mm:
                    items.append((len(mm.group(1)) // 2, mm.group(2)[0].isdigit(), mm.group(3)))
                    i += 1
                elif lines[i].strip() and items and re.match(r"^\s{2,}\S", lines[i]):
                    d, o, t = items[-1]
                    items[-1] = (d, o, t + " " + lines[i].strip())
                    i += 1
                else:
                    break
            lst, _ = _list_html(items, 0, items[0][0])
            out.append(lst)
            continue
        if not line.strip():
            i += 1
            continue
        buf = [line]
        i += 1
        while (i < n and lines[i].strip()
               and not re.match(r"^\s*(```|#{1,6}\s|>|\s*([-*+]|\d+[.)])\s|<svg\b)", lines[i])):
            buf.append(lines[i])
            i += 1
        out.append("<p>" + _inline(" ".join(s.strip() for s in buf)) + "</p>")
    return "\n".join(out)


def _strip_tags(h: str) -> str:
    return re.sub(r"<[^>]+>", " ", h)


# ---------------------------------------------------------------- tree / pages

def _sortkey(p):
    o = p.get("order")
    return (0, o) if isinstance(o, (int, float)) else (1, 0)


def build_tree(pages):
    by_id = {p["id"]: p for p in pages}
    children = defaultdict(list)
    roots = []
    for p in sorted(pages, key=_sortkey):
        pid = p.get("parentId")
        if pid and pid in by_id:
            children[pid].append(p)
        else:
            roots.append(p)
    return roots, children


def _safe_id(raw: str, used: set) -> str:
    sid = re.sub(r"[^A-Za-z0-9_-]", "-", raw or "page") or "page"
    base, k = sid, 2
    while sid in used:
        sid = f"{base}-{k}"
        k += 1
    used.add(sid)
    return sid


def normalize_pages(raw_pages):
    used: set = set()
    pages = []
    for p in raw_pages:
        pages.append({
            "id": _safe_id(str(p.get("id") or p.get("title") or "page"), used),
            "parentId": p.get("parentId"),
            "title": p.get("title") or "无标题",
            "order": p.get("order"),
            "description": p.get("description") or "",
            "filePaths": p.get("filePaths") or [],
            "sources": p.get("sources") or [],
            "markdown": p.get("markdown") or "",
        })
    return pages


def _tree_html(roots, children) -> str:
    def node(p):
        kids = children.get(p["id"], [])
        sub = "".join(node(k) for k in kids)
        inner = html.escape(str(p.get("title") or p["id"]))
        ul = f"<ul>{sub}</ul>" if sub else ""
        return f'<li><a class="navitem" data-page="{p["id"]}" href="#{p["id"]}">{inner}</a>{ul}</li>'

    return "<ul>" + "".join(node(p) for p in roots) + "</ul>"


def _page_section(p) -> str:
    chips = "".join(f'<span class="chip">{html.escape(str(f))}</span>' for f in p["filePaths"][:12])
    chip_html = f'<div class="chips">{chips}</div>' if chips else ""
    srcs = "".join(
        f'<span class="chip src">{html.escape(str(s.get("path", "?")))}'
        f'{":" + str(s["startLine"]) if s.get("startLine") else ""}</span>'
        for s in p["sources"][:20])
    src_html = f'<div class="chips"><span class="srclab">来源</span>{srcs}</div>' if srcs else ""
    desc = f'<p class="desc">{_inline(p["description"])}</p>' if p["description"] else ""
    body = md_to_html(p["markdown"]) if p["markdown"] else '<p class="todo">（此页无内容）</p>'
    return (f'<section class="page" id="pg-{p["id"]}" hidden>'
            f'<h1>{html.escape(str(p["title"]))}</h1>{desc}{chip_html}{src_html}'
            f'<div class="content">{body}</div></section>')


# ---------------------------------------------------------------- template

_TEMPLATE = """<!DOCTYPE html>
<html lang="__LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fafaf8;--fg:#1f2328;--muted:#59636e;--panel:#ffffff;--border:#d1d9e0;--accent:#0969da;--codebg:#f2f4f7;--chipbg:#eceff3;--shadow:rgba(0,0,0,.06)}
[data-theme=dark]{--bg:#0d1117;--fg:#e6edf3;--muted:#8b949e;--panel:#161b22;--border:#30363d;--accent:#4493f8;--codebg:#10151c;--chipbg:#1d242d;--shadow:rgba(0,0,0,.4)}
*{box-sizing:border-box}html,body{margin:0;height:100%}
body{display:flex;background:var(--bg);color:var(--fg);font:15px/1.75 -apple-system,"PingFang SC","Segoe UI",Roboto,sans-serif}
aside{width:300px;min-width:300px;height:100vh;overflow:auto;background:var(--panel);border-right:1px solid var(--border);padding:16px 14px 32px}
#tbtn{float:right;background:none;border:1px solid var(--border);border-radius:6px;color:var(--fg);cursor:pointer;font-size:12px;padding:2px 8px}
#repo{font-weight:700;font-size:15px;margin:2px 44px 10px 0;word-break:break-all}
#search{width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--fg);font-size:13px;margin-bottom:8px}
#hits{border:1px solid var(--border);border-radius:8px;margin-bottom:8px;max-height:45vh;overflow:auto;background:var(--bg)}
.hit{padding:6px 10px;border-bottom:1px solid var(--border);cursor:pointer;font-size:12.5px}
.hit:last-child{border-bottom:0}.hit.none{color:var(--muted);cursor:default}
.hit b{display:block;font-size:13px}.hit span{color:var(--muted)}
aside ul{list-style:none;margin:0;padding-left:14px}aside>ul{padding-left:0}
.navitem{display:block;padding:3px 8px;border-radius:6px;color:var(--fg);text-decoration:none;font-size:13.5px;line-height:1.5}
.navitem:hover{background:var(--chipbg)}.navitem.active{background:var(--chipbg);color:var(--accent);font-weight:600}
main{flex:1;height:100vh;overflow:auto;padding:40px 56px 80px;max-width:980px}
section.page[hidden]{display:none}
h1{font-size:26px;line-height:1.3;margin:0 0 8px;border-bottom:1px solid var(--border);padding-bottom:12px}
.desc{color:var(--muted)}
.chips{margin:10px 0;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.srclab{color:var(--muted);font-size:12px}
.chip{background:var(--chipbg);border-radius:5px;padding:1px 8px;font-size:12px;font-family:ui-monospace,Menlo,monospace}
h2{font-size:20px;margin:28px 0 10px}h3{font-size:17px;margin:22px 0 8px}
pre.code{background:var(--codebg);border:1px solid var(--border);border-radius:10px;padding:12px 14px;overflow:auto;position:relative}
pre.code .lang{position:absolute;top:6px;right:12px;font-size:11px;color:var(--muted)}
code{font-family:ui-monospace,Menlo,monospace;font-size:.92em}
p code,li code,td code,h2 code,h3 code{background:var(--chipbg);border-radius:4px;padding:1px 5px}
pre.mermaid{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:16px;text-align:center;overflow:auto}
.mermaid-fallback{background:var(--codebg);border:1px dashed var(--border);border-radius:10px;padding:12px;font-family:ui-monospace,Menlo,monospace;font-size:12px;white-space:pre-wrap;color:var(--muted)}
.diagram{margin:18px 0;overflow-x:auto}.diagram svg{max-width:100%}
blockquote{border-left:3px solid var(--accent);margin:14px 0;padding:2px 16px;color:var(--muted);background:var(--panel);border-radius:0 8px 8px 0}
table{border-collapse:collapse;margin:14px 0;width:100%}
th,td{border:1px solid var(--border);padding:6px 10px;text-align:left;font-size:13.5px}
th{background:var(--chipbg)}
.linkref{color:var(--accent);border-bottom:1px dotted var(--accent);cursor:help}
.imgref{color:var(--muted);font-size:.92em}
.todo{color:var(--muted);font-style:italic}
hr{border:0;border-top:1px solid var(--border);margin:22px 0}
footer{margin-top:60px;color:var(--muted);font-size:12px}
@media (prefers-reduced-motion:no-preference){.navitem,.chip{transition:background .15s}}
</style>
</head>
<body>
<aside>
  <button id="tbtn" title="切换主题">🌓</button>
  <div id="repo">__REPO__</div>
  <input id="search" type="search" placeholder="全文搜索…" autocomplete="off">
  <div id="hits" hidden></div>
  <nav id="tree">__TREE__</nav>
</aside>
<main id="main">
__PAGES__
<footer>repo-wiki@local · 纯本地生成，零上传 · __DATE__</footer>
</main>
<script>__MERMAID__</script>
<script>
window.INDEX=__INDEX__;
(function(){
var $=function(s){return document.querySelector(s)};
function show(id){
  var ok=false;
  document.querySelectorAll('section.page').forEach(function(s){var v=s.id==='pg-'+id;s.hidden=!v;if(v)ok=true;});
  if(!ok){var first=document.querySelector('section.page');if(first){first.hidden=false;id=first.id.slice(3);}}
  document.querySelectorAll('.navitem').forEach(function(a){a.classList.toggle('active',a.dataset.page===id);});
  if(history.replaceState)history.replaceState(null,'','#'+id);
  $('#main').scrollTop=0;
}
document.addEventListener('click',function(e){
  var a=e.target.closest('.navitem');
  if(a){e.preventDefault();show(a.dataset.page);return;}
  var h=e.target.closest('.hit[data-page]');
  if(h){show(h.dataset.page);$('#hits').hidden=true;$('#search').value='';}
});
window.addEventListener('hashchange',function(){var id=location.hash.slice(1);if(id)show(id);});
var search=$('#search'),hits=$('#hits');
search.addEventListener('input',function(){
  var q=search.value.trim().toLowerCase();
  if(!q){hits.hidden=true;hits.innerHTML='';return;}
  var out=[];
  for(var id in window.INDEX){
    var it=window.INDEX[id];
    var hay=(it.title+' '+it.desc+' '+it.text).toLowerCase();
    var pos=hay.indexOf(q);
    if(pos>=0){out.push({id:id,t:it.title,s:it.text.substr(Math.max(0,pos-30),90)});
      if(out.length>=30)break;}
  }
  hits.innerHTML=out.length?out.map(function(h){return '<div class="hit" data-page="'+h.id+'"><b>'+h.t+'</b><span>'+h.s+'</span></div>';}).join(''):'<div class="hit none">无命中</div>';
  hits.hidden=false;
});
function renderMermaids(){
  if(!window.mermaid||!window.mermaid.initialize)return false;
  document.querySelectorAll('pre.mermaid').forEach(function(el){
    if(el.dataset.src===undefined){el.dataset.src=el.textContent;}
    else{el.innerHTML='';el.textContent=el.dataset.src;}
  });
  try{
    mermaid.initialize({startOnLoad:false,securityLevel:'strict',
      theme:document.documentElement.dataset.theme==='dark'?'dark':'neutral'});
    mermaid.run({querySelector:'pre.mermaid'});
    return true;
  }catch(err){
    document.querySelectorAll('pre.mermaid').forEach(function(el){
      el.classList.add('mermaid-fallback');el.textContent=el.dataset.src||el.textContent;});
    return false;
  }
}
function applyTheme(t){
  document.documentElement.dataset.theme=t;
  try{localStorage.setItem('rw-theme',t);}catch(e){}
  document.getElementById('tbtn').textContent=t==='dark'?'☀️ 浅色':'🌙 深色';
  renderMermaids();
}
document.getElementById('tbtn').onclick=function(){
  applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark');};
var saved='light';
try{saved=localStorage.getItem('rw-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}catch(e){}
applyTheme(saved);
var initial=location.hash.slice(1);
show(initial);
})();
</script>
</body>
</html>
"""


def _mermaid_runtime() -> str:
    if MERMAID_PATH.exists():
        js = MERMAID_PATH.read_text(encoding="utf-8", errors="surrogatepass")
        js = js.replace("</script", "<\\/script").replace("<!--", "<\\!--")
        adapter = ("var __rwNs=window.__esbuild_esm_mermaid_nm;"
                   "window.mermaid=(__rwNs&&__rwNs.mermaid)&&(__rwNs.mermaid.default||__rwNs.mermaid);"
                   "if(!window.mermaid)console.warn('repo-wiki: mermaid 挂载失败,图表仅显源码');")
        return js + "\n" + adapter
    return "window.mermaid=null;console.warn('mermaid.min.js 未内联，图表仅显源码');"


def build_site(wiki_dir: Path) -> dict:
    wiki_json = wiki_dir / "wiki.json"
    data = json.loads(wiki_json.read_text(encoding="utf-8"))
    pages = normalize_pages(data.get("pages") or [])
    if not pages:
        sys.exit(f"[repo-wiki] {wiki_json} 中没有页面")
    sections, index = [], {}
    roots, children = build_tree(pages)
    for p in pages:
        sections.append(_page_section(p))
        index[p["id"]] = {
            "title": str(p["title"]),
            "desc": str(p["description"]),
            "text": _strip_tags(md_to_html(p["markdown"]))[:20000],
        }
    title = str(data.get("repoId") or wiki_dir.name)
    page_html = "\n".join(sections)
    idx_json = json.dumps(index, ensure_ascii=False).replace("</", "<\\/")
    doc = (_TEMPLATE
           .replace("__LANG__", str(data.get("language") or "zh-CN"))
           .replace("__TITLE__", html.escape(title))
           .replace("__REPO__", html.escape(title))
           .replace("__TREE__", _tree_html(roots, children))
           .replace("__PAGES__", page_html)
           .replace("__DATE__", time.strftime("%Y-%m-%d %H:%M"))
           .replace("__MERMAID__", _mermaid_runtime())
           .replace("__INDEX__", idx_json))
    site = wiki_dir / "site"
    site.mkdir(parents=True, exist_ok=True)
    out = site / "index.html"
    out.write_text(doc, encoding="utf-8")
    return {"pages": len(pages), "path": out, "bytes": out.stat().st_size,
            "mermaid": MERMAID_PATH.exists()}


# ---------------------------------------------------------------- import legacy

def load_legacy(source: Path):
    meta_src = {}
    pages = []
    wj = source / "wiki.json"
    if wj.exists():
        data = json.loads(wj.read_text(encoding="utf-8"))
        meta_src = data
        pages = [p for p in (data.get("pages") or []) if (p.get("markdown") or "").strip()]
    if not pages:
        for f in sorted((source / "draft-pages").glob("*.json")):
            try:
                p = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (p.get("markdown") or "").strip():
                pages.append(p)
    if not pages:
        sys.exit(f"[repo-wiki] {source} 里既无含正文的 wiki.json，也无可用 draft-pages")
    draft = {}
    dj = source / "draft.json"
    if dj.exists():
        draft = json.loads(dj.read_text(encoding="utf-8"))
    catalog = meta_src.get("catalogTree") or draft.get("catalogTree") or []
    return meta_src, draft, pages, catalog


def merge_catalog(catalog, pages):
    """旧版目录树(catalogTree 节点) + 内容页(pages, 挂在节点下) → 统一页面树。

    有 pageId 的节点替换为对应内容页；无 pageId 的节点生成"本节导览"页。
    未被目录树引用的内容页降级为根并计数。
    """
    if not catalog:
        return pages, len(pages), 0
    by_id = {str(p.get("id")): p for p in pages}
    used = {str(p.get("id")) for p in pages}
    merged, seen = [], set()

    def walk(nodes, parent):
        for nd in nodes:
            nid = str(nd.get("id"))
            seen.add(nid)
            pid = nd.get("pageId")
            if pid and str(pid) in by_id:
                page = dict(by_id[str(pid)])
                page["parentId"] = parent or None
                merged.append(page)
                seen.add(str(pid))
            else:
                kids = nd.get("children") or []
                toc = "## 本节导览\n\n" + "\n".join(
                    f"- {c.get('title')}" for c in kids) if kids else ""
                merged.append({
                    "id": nid if nid not in used else nid + "-sec",
                    "parentId": parent or None,
                    "title": nd.get("title") or nid,
                    "order": nd.get("order"),
                    "description": "",
                    "filePaths": [],
                    "sources": [],
                    "markdown": toc,
                })
                seen.add(merged[-1]["id"])
            walk(nd.get("children") or [], nid)

    walk(catalog, None)
    orphans = 0
    for p in pages:
        if str(p.get("id")) not in seen:
            merged.append(dict(p))
            orphans += 1
    return merged, len(merged), orphans


def cmd_import(args):
    src = Path(args.source).expanduser()
    if not src.is_absolute():
        src = LEGACY_BASE / src
    if not src.exists():
        sys.exit(f"[repo-wiki] 找不到 {src}")
    meta_src, draft, raw_pages, catalog = load_legacy(src)
    merged, total, orphans = merge_catalog(catalog, raw_pages)
    if orphans:
        print(f"[repo-wiki] WARN {orphans} 个内容页不在目录树中，已降级为根节点")
    repo_id = meta_src.get("repoId") or draft.get("repoId") or ""
    dest = Path(args.dest).expanduser() if args.dest else (
        Path(repo_id) / ".zcode-wiki" if repo_id else HOME / ".zcode/v2/repo-wiki-local" / src.name)
    dest.mkdir(parents=True, exist_ok=True)
    wiki = {
        "schema": "repo-wiki-local/1",
        "repoId": repo_id or src.name,
        "language": meta_src.get("language") or draft.get("language") or "zh-CN",
        "generatedBy": "import-legacy",
        "importedAt": time.strftime("%Y-%m-%d %H:%M:%S"),
        "legacySource": str(src),
        "pages": merged,
    }
    (dest / "wiki.json").write_text(json.dumps(wiki, ensure_ascii=False, indent=1), encoding="utf-8")
    legacy_meta = {k: meta_src.get(k) for k in ("generationModel", "generationOptions", "wikiId") if meta_src.get(k)}
    if legacy_meta:
        (dest / "legacy-meta.json").write_text(json.dumps(legacy_meta, ensure_ascii=False, indent=1), encoding="utf-8")
    pages_dir = dest / "pages"
    pages_dir.mkdir(exist_ok=True)
    for f in pages_dir.glob("*.md"):
        f.unlink()
    for p in merged:
        pid = re.sub(r"[^A-Za-z0-9_-]", "-", str(p.get("id") or "page"))
        (pages_dir / f"{pid}.md").write_text(p.get("markdown") or "", encoding="utf-8")
    info = build_site(dest)
    print(f"[repo-wiki] 导入完成: {src.name} → {dest}")
    print(f"[repo-wiki] 页数 {info['pages']}, 站点 {info['path']} ({info['bytes'] // 1024} KB), "
          f"mermaid离线渲染 {'✓' if info['mermaid'] else '✗(仅源码)'}")
    print(f"[repo-wiki] 用浏览器打开: {info['path']}")


# ---------------------------------------------------------------- build / selfcheck

def cmd_build(args):
    info = build_site(Path(args.wiki).expanduser())
    print(f"[repo-wiki] 构建: {info['pages']} 页 → {info['path']} ({info['bytes'] // 1024} KB), "
          f"mermaid离线渲染 {'✓' if info['mermaid'] else '✗(仅源码)'}")


_EXT_RE = re.compile(r'(?:href|src|xlink:href)="(https?://[^"]+)"')


def cmd_selfcheck(args):
    wiki_dir = Path(args.wiki).expanduser()
    problems, warns = [], []
    wj = wiki_dir / "wiki.json"
    if not wj.exists():
        sys.exit(f"[repo-wiki] selfcheck 失败: 缺 {wj}")
    data = json.loads(wj.read_text(encoding="utf-8"))
    pages = data.get("pages") or []
    ids = {str(p.get("id")) for p in pages}
    for p in pages:
        pid = p.get("parentId")
        if pid and str(pid) not in ids:
            warns.append(f"页面 {p.get('id')} 的父 {pid} 缺失（降级为根）")
    # 环检测
    graph = {str(p.get("id")): str(p.get("parentId") or "") for p in pages}
    for start in graph:
        seen, cur = set(), start
        while cur and cur in graph and graph[cur]:
            if cur in seen:
                problems.append(f"页面树存在环: {start}")
                break
            seen.add(cur)
            cur = graph[cur]
    site = wiki_dir / "site" / "index.html"
    if not site.exists():
        problems.append(f"缺站点文件 {site}")
    else:
        doc = site.read_text(encoding="utf-8")
        for url in _EXT_RE.findall(doc):
            problems.append(f"外链 {url}")
        if "__esbuild_esm_mermaid_nm" not in doc:
            warns.append("站点未内联 mermaid 运行时（图表将仅显源码）")
    for w in warns:
        print(f"[repo-wiki] WARN {w}")
    if problems:
        for p in problems:
            print(f"[repo-wiki] FAIL {p}")
        sys.exit(1)
    print(f"[repo-wiki] selfcheck 通过: {len(pages)} 页, 站点自包含、零外链")


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(prog="build_wiki_site.py", description="repo-wiki 纯本地构建器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="由 wiki.json 构建自包含站点")
    b.add_argument("--wiki", required=True)
    im = sub.add_parser("import-legacy", help="导入旧版 repo-wiki 数据并构建")
    im.add_argument("source")
    im.add_argument("--dest", default=None)
    sc = sub.add_parser("selfcheck", help="树完整性 + 零外链校验")
    sc.add_argument("--wiki", required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        cmd_build(args)
    elif args.cmd == "import-legacy":
        cmd_import(args)
    elif args.cmd == "selfcheck":
        cmd_selfcheck(args)


if __name__ == "__main__":
    main()
