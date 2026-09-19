---
name: repo-wiki
description: 纯本地 Repo Wiki（零上传）。Use when the user says "repo wiki", "生成 wiki", "仓库知识库", "导入旧 wiki", "repo-wiki", or wants deep paged documentation of a repository without uploading anything. Generates a paged wiki (tree + diagrams + evidence-based prose) entirely locally, imports legacy ~/.zcode/v2/repo-wiki data, and builds a self-contained static viewer with offline mermaid rendering.
---

# repo-wiki — 纯本地仓库 Wiki（零上传）

你是一个文档工程执行器。本技能的价值契约：**全程本地、零上传、零网络、证据优先、产物自包含**。

## 硬约束（每一步都适用，违反即失败）

1. **禁止一切网络访问**：不调用 WebFetch / WebSearch / 任何 URL 抓取；不 curl / wget；不访问任何云端生成端点。分析只靠本地读文件。
2. **禁止上传**：不 git push、不发布、不把仓库内容发往任何外部服务。
3. **不读取 `.git` 目录内容**：不看对象/包文件，不做全历史导出。需要版本背景时最多使用 `git log --oneline -15` 这类摘要元信息，且非必需。
4. **产物只落本地**：默认 `<仓库>/.zcode-wiki/`，不写到仓库外（`import-legacy` 除外，见下）。
5. **证据优先**：页面里的每个论断尽量带仓库相对路径（和行号）；不确定的写"待确认"，不编造 API/文件。

## 工具脚本

构建器位于本技能基目录（加载时系统给出的 Base directory）下的 `../../scripts/build_wiki_site.py`，即
`<插件根>/scripts/build_wiki_site.py`。若拿不到基目录，用
`find ~/.zcode/cli/plugins/cache -path '*repo-wiki*' -name build_wiki_site.py 2>/dev/null | head -1` 定位。
纯 Python3 标准库，无第三方依赖，无网络行为。

三个子命令：

```bash
python3 build_wiki_site.py build       --wiki <.zcode-wiki目录>          # 由 wiki.json 构建自包含 site/index.html
python3 build_wiki_site.py import-legacy <hash|绝对路径> [--dest <dir>]  # 导入旧版 ~/.zcode/v2/repo-wiki/<hash>
python3 build_wiki_site.py selfcheck   --wiki <.zcode-wiki目录>          # 树完整性 + 零外链校验，exit 0/1
```

## 子命令一：generate <仓库路径>

### Phase 0 盘点（只读文件系统）
- 列顶层目录与关键清单文件（README、package.json、pyproject、go.mod、Cargo.toml…）。
- 跳过目录：`.git`、`node_modules`、`dist`、`build`、`out`、`target`、`.venv`、`vendor`、`Pods`、锁文件、二进制与大资产。
- 用 `find … -type f | wc -l`、按扩展名统计等手段掌握规模，不要 cat 大文件。

### Phase 1 语言判定
跟仓库现有文档走：README/注释以中文为主 → 全部页面用 zh-CN，否则用 en。

### Phase 2 规划页面树（6–40 页）
- 骨架建议：总览 → 架构总览 → 核心模块 ×N → 数据流/协议 → 构建·运行 → 已知问题/FAQ。
- 每页先定元数据：`id`（短横线小写）、`parentId`（根为 null）、`order`、`title`、`description`、`filePaths`（3–8 个关键文件，仓库相对路径）。
- 树要平衡：任何一级 ≤8 个子节点，深度 ≤4。

### Phase 3 逐页写作
- 每页 400–900 字 + 要点列表；开头 2–3 句回答"这页讲什么、读完能干什么"。
- 架构、数据流、模块边界类页面**必须有 1 张图**：优先内联 SVG（自包含、风格可控，参考线框+配色克制），也可用 mermaid 代码块（查看器内置离线渲染）。
- 关键代码点用 `` `path/to/file.ts:42` `` 形式引用；跨页引用直接写页面标题。
- 面向"接手的人"：讲清不变量、坑、为什么这样设计，而不是复述目录名。

### Phase 4 落盘与构建
产物写到 `<仓库>/.zcode-wiki/`：
- `wiki.json`：`{"schema":"repo-wiki-local/1","repoId":"<绝对路径>","language":"…","generatedBy":"agent","pages":[{id,parentId,title,order,description,filePaths,markdown}]}`（markdown 内嵌，作为唯一事实源）
- `pages/<id>.md`：每页一份导出（便于人读和 diff），构建以 wiki.json 为准。
- 然后 `build` + `selfcheck`，两者必须全绿。

### Phase 5 汇报
输出：site/index.html 绝对路径、页数、目录树摘要、以及"未覆盖/待确认"清单。

## 子命令二：import-legacy <hash|绝对路径>

把旧版 ZCode（≤3.13）生成的存量 wiki 转成本插件格式：
- 优先读 `<hash>/wiki.json`（含完整 pages.markdown）；若缺页回退 `draft-pages/*.json`。
- 默认落盘到 `<repoId>/.zcode-wiki/`（repoId 取自旧数据），`--dest` 可覆盖。
- 旧 `generationModel`、`generationOptions` 写入 `legacy-meta.json` 留档。
- 构建并自检后，报告站点路径与页数。

## 子命令三：view <wiki目录>

对已有 `.zcode-wiki/` 重建站点（内容更新后用）：`build` + `selfcheck`，报告站点路径。

## 质量门（selfcheck 必须全绿才算完成）

- 页面树：无孤儿（父缺失降级为根并告警）、无环、order 可排序。
- `site/index.html` 存在且自包含：`href=`/`src=` 属性中不得出现 `http(s)://` 外链（mermaid 运行时已内联，允许 `xmlns` 命名空间声明）。
- 内联 mermaid 库存在（assets/mermaid.min.js 已打进站点），否则报告为降级（图表仅显源码）。
