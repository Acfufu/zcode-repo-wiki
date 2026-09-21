# 更新日志

本文件是版本摘要；每个版本的完整说明见 [GitHub Releases](https://github.com/Acfufu/zcode-repo-wiki/releases)。

## 0.2.1 — 2026-09-20

安全加固、失败路径健壮性与发布包洁净度。六个审核轮次（5 轮高精度 + 1 轮收敛）的修复全部落地。

**安全**

- SVG 净化重写为「解析 → 白名单 → 重序列化」：此前基于正则的删除可被 `<scr<script>ipt>` 这类拼接绕过（Chrome 实测执行）；事件属性、外部 URL、`<meta refresh>`、`<foreignObject>` 等执行面一律移除，不可解析时降级为转义代码块。
- 收回 SVG 内联 CSS 与 SMIL 动画：`<style>`、`style=` 属性与 `<animate>` 全部移除——CSS 反斜杠转义（`u\72l(`、`@im\70ort`）与 `<animate attributeName="href" values="http://…">` 都能让浏览器真实发起请求而机检全绿（Chrome netlog 实证）。样式请用呈现属性（`fill`、`stroke`、`opacity`）表达。
- 零外链机检与净化同源、逐属性扫描：覆盖单/双/无引号、实体编码与控制字符混淆、protocol-relative、`srcset`/`srcdoc`/meta refresh、`values/to/from/by/attributeName`、CSS `@import` 与字符串 URL（含反斜杠转义归一）；`xmlns` 与 `data-*` 不误报，正文以代码块讲解 CSS 也不误报。
- 搜索索引注入（`JSON.parse` + `\uXXXX` 转义 + `textContent`）、`sources[].startLine` 注入、`_inline` 引号属性注入均已封死。

**健壮性**

- 全链路干净报错：缺文件、坏 JSON、非 UTF-8、目录误传、超深嵌套都给出可读信息与退出码，不再有裸 traceback。
- 原子写 + 权限保持：站点/wiki/meta/pages 写入均走 tmp + replace，替换前不截断旧文件。
- 递归全面有界（树/导航/目录树改迭代、markdown 深度上限、全局 `RecursionError` 兜底）。
- 引用机检拒绝 `..` 与绝对路径越界（不读仓库外文件），仓内符号链接引用正常；相对 `repoId` 以 wiki 目录为基准，不随 CWD 漂移。
- `import-legacy` 的 `--dest` 守卫：等于源目录、位于源目录之外的上层、或非本工具产物目录均拒绝。

**安装器**

- 缓存与 zip 统一排除 `tests/`、`__pycache__`、`*.pyc`，`--delete-excluded` 同时清理历史污染；MIT LICENSE 随包分发。
- zip 仅在缺失或源较新时重建（sha256 与内容一致，registry 溯源可校验），打包失败保留旧包并回滚新建缓存。
- 三份配置 JSON 先全部校验再统一 tmp + replace 落盘，不留半安装状态；新建配置文件用 0600，备份与源文件同权限。

**行为变化（升级需知）**

- 未知配置键与未知子键会被拒绝（此前静默忽略）；`profile` 支持 `--set profile=…`，显式 `null` 报错。
- 站点质量门加严：`site/index.html` 缺失 `DOCTYPE`/`main` 结构或内容不完整判 FAIL。
- 引用机检白名单扩展（`.sh`、`.c`、`.css`、`.html` 等常见代码/配置扩展名纳入）。
- 新增 `repo-wiki/tests/test_build_wiki_site.py` 回归套件（纯标准库）。

## 0.2.0 — 2026-09-20

生成配置全量可调，引用可解析性机检常开。

**新增**

- **生成配置（`resolve-config`）**：四层合并（内置默认 → `~/.zcode/repo-wiki/config.json` → `<仓库>/.zcode-wiki/config.json` → `--set k=v`），不建配置文件时行为与 v0.1 完全一致。
- 八族参数：`language`、`granularity`（`theme`/`file`/`hybrid`）、`pages`、`tree`、`wordsPerPage`、`diagrams`、`citations`、`skeleton.knownIssues`。
- 预设档位 `compact` / `standard` / `deep` / `legacy`；其中 `legacy` 一键复刻旧版内置生成器风格（逐文件切页 + 每页配图 + 长文）。
- 留档复现：合并结果与逐字段 provenance 写入 `<仓库>/.zcode-wiki/generation-meta.json`。
- **引用机检（常开，不受配置控制）**：所有 `` `路径:行号` `` 引用强制校验文件存在且行号在界内；仓库根不可用的存量 wiki 降级为警告。

**兼容性**

- schema 保持 `repo-wiki-local/1`，已生成的 `.zcode-wiki/` 与 `import-legacy` 导入数据零改动兼容。

## 0.1.0 — 2026-09-20

首个版本：纯本地 Repo Wiki 插件，替代 3.14.0 起被下架的官方 Repo Wiki 入口。

- `build` / `selfcheck` / `import-legacy` 三个子命令，纯 Python3 标准库。
- 分页 wiki（目录树 + mermaid 图表 + 带文件路径证据的正文），单文件自包含站点，零外链。
- 内联 mermaid 运行时离线渲染；全文搜索、深浅双主题、窄屏自适应。
- 旧版（≤3.13）`~/.zcode/v2/repo-wiki/<hash>/` 存量数据导入。
