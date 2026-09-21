# repo-wiki（ZCode 插件）

纯本地的仓库深度文档（Repo Wiki）插件：**零上传、零网络、不直接读取 `.git` 对象内容**（唯一例外：可选使用 `git log --oneline -15` 级摘要命令），用于替代 ZCode 3.14.0 起被下架的官方 Repo Wiki 入口。

<img src="../docs/assets/viewer-light.png" alt="查看器：目录树、路径 chip、来源角标、mermaid 架构图" width="100%">

本文件是插件的完整行为说明；仓库总览与截图见[根 README](../README.md)。

**目录**

- [能力](#能力) · [用法](#用法) · [生成配置](#生成配置v02) · [隐私承诺](#隐私承诺) · [已知边界](#已知边界) · [数据格式](#数据格式repo-wiki-local1) · [测试](#测试)

## 能力

- **generate**：由 agent 在本地分析仓库，产出分页 wiki（目录树 + 内联 SVG / mermaid 图 + 带文件路径证据的正文），落盘 `<仓库>/.zcode-wiki/`
- **import-legacy**：把旧版（≤3.13）存量数据 `~/.zcode/v2/repo-wiki/<hash>/` 转成本插件格式并建站（优先读 `wiki.json`，缺页回退 `draft-pages/*.json`；只有任务元数据、正文已不可重建的存量会被如实报告为无法恢复）
- **view**：内容更新后重建站点
- 产物是**单文件自包含** `site/index.html`：内联 mermaid 11 离线渲染、全文搜索（单页索引上限 2 万字符，超出部分不参与搜索）、深浅双主题（跟随系统 + 手动切换 + localStorage 持久化，脏值自动归一）、窄屏自适应（≤760px 侧栏堆叠）、搜索命中项可键盘操作（Tab + Enter）、禁用 JS 时给出提示、零外链。外链机检为**有界启发式**：覆盖真实元素属性的常见形态（单/双/无引号、实体编码、protocol-relative、`values/to/from/by`、`@import` 与 CSS 字符串 URL，含反斜杠转义归一）与 `<style>`/`style=` 内的 CSS（正文中以代码块/行内代码讲解 CSS 的文本不误报）；直通 SVG 经 XML 解析器白名单净化（删脚本/事件/外部 URL 与 `<style>`/`style=`/`<animate>`，保留滤镜/几何/`data:image` 内联图与呈现属性；不可解析则降级为转义代码文本），净化与机检共同保障"零外链、零脚本注入"
- **生成配置可调**（v0.2+）：语言、页面切分粒度、页数、页长、图表密度、引用策略、骨架、树形限制，三层配置 + 命令行旗标，详见下方"生成配置"

## 用法

会话内：`/repo-wiki generate <仓库路径>`、`/repo-wiki import-legacy <hash>`、`/repo-wiki view <wiki目录>`。临时覆盖参数：`/repo-wiki generate <仓库路径> --set language=zh-CN --set profile=legacy`。

脚本直用（纯 Python3 标准库，要求 Python ≥3.7）：

```bash
python3 scripts/build_wiki_site.py import-legacy cd9589b2d516   # 例: PTsol（构建但不自检，随后可 selfcheck）
python3 scripts/build_wiki_site.py build       --wiki <仓库>/.zcode-wiki
python3 scripts/build_wiki_site.py selfcheck   --wiki <仓库>/.zcode-wiki
python3 scripts/build_wiki_site.py resolve-config --repo <仓库路径> [--set k=v …] [--dry-run]
```

`--set` 支持点路径下钻对象字段（`--set pages.max=24`）；列表字段需整体赋值（`--set 'wordsPerPage=[300,600]'`）；未知键会被拒绝。诊断信息（WARN/FAIL）走 stderr，数据走 stdout。

## 生成配置（v0.2+）

合并优先级：**内置默认 → `~/.zcode/repo-wiki/config.json` → `<仓库>/.zcode-wiki/config.json` → `--set` 旗标**。不建任何配置文件时行为与零配置完全一致。`resolve-config` 输出生效配置，并把结果与每字段的来源层（provenance，profile 展开记为 `<层>:profile`，对应 `layers.profiles`）写入 `<仓库>/.zcode-wiki/generation-meta.json` 留档。

```json
{
  "profile": "standard",
  "language": "auto",
  "granularity": "theme",
  "pages":   { "min": 6, "max": 40 },
  "tree":    { "maxChildren": 8, "maxDepth": 4 },
  "wordsPerPage": [400, 900],
  "diagrams": "minimal",
  "citations": "strict",
  "skeleton": { "knownIssues": true }
}
```

字段说明与值域：`profile` 取 `compact|standard|deep|legacy`（快捷档位，可被下列字段覆盖）；`language` 取 `auto` 或简化 BCP47（如 `zh-CN`）；`granularity` 取 `theme`（按主题）| `file`（逐文件，旧版风格）| `hybrid`；`pages.min/max` 为 1–100 的整数且 min ≤ max；`tree.maxChildren` 2–16、`tree.maxDepth` 2–6；`wordsPerPage` 为 [min, max] 两个 100–5000 的整数（整列表覆盖，不能只改一项）；`diagrams` 取 `none|minimal|rich`；`citations` 取 `strict|relaxed`（引用机检永远常开，不受此项控制）；`skeleton.knownIssues` 为布尔值。嵌套对象按子键合并：仓库层只写 `pages.max` 时 `pages.min` 沿用低层值。脚本按标准 JSON 解析（不支持 `//` 注释），未知键与未知子键会被拒绝并报错。

`profile` 预设展开：`compact`（少而短）、`standard`（数值等同内置默认）、`deep`（长文深读）、`legacy`（复刻旧版：逐文件 + rich 图表 + 1200–2200 字/页）。不设 `profile` 时即使用内置默认值。

## 隐私承诺

| 行为 | 本插件 |
|---|---|
| 上传仓库内容 / Git 历史 | 从不 |
| 网络请求（生成、图表、字体、脚本） | 从不；站点零外链由 selfcheck 的有界启发式机检强制，见上 |
| 读取 `.git` 对象内容 | 从不（唯一例外：可选的 `git log --oneline -15` 摘要命令） |
| 产物位置 | 仅本地磁盘 |

内联的 mermaid 运行时 bundle 内含第三方组件（mermaid、DOMPurify 等）的许可声明，见 [`assets/THIRD-PARTY-NOTICES`](./assets/THIRD-PARTY-NOTICES)。

## 已知边界

- **外链机检是有界启发式**，不是形式化证明：它覆盖真实元素属性与 CSS 上下文的常见形态，但无法证明"任何输入都不可能生成外链"。
- **引用机检只覆盖白名单扩展名**（见脚本 `_REF_EXTS`，含 `.ts/.js/.py/.go/.sh/.md/.json/.yml` 等）；白名单外的引用不做机检，写作时应自觉保证真实。
- **图表依赖内联的 mermaid 运行时**：运行时缺失时站点不失败，而是降级为展示图表源码（selfcheck 报 WARN）。
- **站点交互依赖前端脚本**：禁用 JS 时给出静态提示，此时搜索、主题切换、页面切换不可用。
- **存量 wiki 的引用机检会降级**：仓库已移动或删除时降级为 WARN 而非 FAIL，避免把"仓库不在原处"误报成"文档损坏"。

## 数据格式（repo-wiki-local/1）

`wiki.json` 为唯一事实源（markdown 内嵌），`pages/*.md` 为导出副本；与旧版 `wiki.json` 的 pages 结构（id/parentId/title/order/filePaths/markdown）保持兼容，便于互转。顶层可选 `title` 决定站点品牌位的显示名（缺省回落到 `repoId`，与历史行为一致；引用机检的仓库根始终取 `repoId`）。生成配置不属于内容，写在旁路的 `generation-meta.json`（新增于 v0.2），schema 不变，旧目录零改动兼容。

## 测试

```bash
python3 tests/test_build_wiki_site.py      # 纯标准库，无需参数，不写仓库
```

回归套件覆盖 fixture 构建/自检、配置合并与校验边界（含 bool/null/未知键/点路径）、注入与净化 PoC（SVG 变异绕过、CSS 转义/动画 URL、外链扫描器）、失败路径的干净报错与写入原子性；结尾打印 `N/N passed`。CI 另用 `node --check` 校验站点内联脚本的真实语法（viewer 的搜索/主题/图表都在那段脚本里）。样本与覆盖清单见 [`tests/README.md`](./tests/README.md)。
