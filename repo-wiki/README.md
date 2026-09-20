# repo-wiki（ZCode 插件）

纯本地的仓库深度文档（Repo Wiki）插件：**零上传、零网络、不直接读取 `.git` 对象内容**（唯一例外：可选使用 `git log --oneline -15` 级摘要命令），用于替代 3.14.0 起被下架的官方 Repo Wiki 入口。

## 能力

- **generate**：由 agent 在本地分析仓库，产出分页 wiki（目录树 + 内联 SVG / mermaid 图 + 带文件路径证据的正文），落盘 `<仓库>/.zcode-wiki/`
- **import-legacy**：把旧版（≤3.13）存量数据 `~/.zcode/v2/repo-wiki/<hash>/` 转成本插件格式并建站（本机存量 17 份中 15 份可恢复；另 2 份只剩任务元数据，仅凭 `task.json` 无法重建正文）
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

## 数据格式（repo-wiki-local/1）

`wiki.json` 为唯一事实源（markdown 内嵌），`pages/*.md` 为导出副本；与旧版 `wiki.json` 的 pages 结构（id/parentId/title/order/filePaths/markdown）保持兼容，便于互转。生成配置不属于内容，写在旁路的 `generation-meta.json`（新增于 v0.2），schema 不变，旧目录零改动兼容。
