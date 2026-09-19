# repo-wiki（ZCode 插件）

纯本地的仓库深度文档（Repo Wiki）插件：**零上传、零网络、零 `.git` 读取**，用于替代 3.14.0 起被下架的官方 Repo Wiki 入口。

## 能力

- **generate**：由 agent 在本地分析仓库，产出分页 wiki（目录树 + 内联 SVG / mermaid 图 + 带文件路径证据的正文），落盘 `<仓库>/.zcode-wiki/`
- **import-legacy**：把旧版（≤3.13）存量数据 `~/.zcode/v2/repo-wiki/<hash>/` 转成本插件格式并建站，已有的 17 份 wiki 全部可恢复浏览
- **view**：内容更新后重建站点
- 产物是**单文件自包含** `site/index.html`：内联 mermaid 11 离线渲染、全文搜索、深浅双主题（跟随系统 + 手动切换 + localStorage 持久化）、零外链

## 用法

会话内：`/repo-wiki generate <仓库路径>`、`/repo-wiki import-legacy <hash>`、`/repo-wiki view <wiki目录>`。

脚本直用（纯 Python3 标准库）：

```bash
python3 scripts/build_wiki_site.py import-legacy cd9589b2d516   # 例: PTsol
python3 scripts/build_wiki_site.py build       --wiki <仓库>/.zcode-wiki
python3 scripts/build_wiki_site.py selfcheck   --wiki <仓库>/.zcode-wiki
```

## 隐私承诺

| 行为 | 本插件 |
|---|---|
| 上传仓库内容 / Git 历史 | 从不 |
| 网络请求（生成、图表、字体、脚本） | 从不（站点零外链，selfcheck 强制） |
| 读取 `.git` 对象内容 | 从不 |
| 产物位置 | 仅本地磁盘 |

## 数据格式（repo-wiki-local/1）

`wiki.json` 为唯一事实源（markdown 内嵌），`pages/*.md` 为导出副本；与旧版 `wiki.json` 的 pages 结构（id/parentId/title/order/filePaths/markdown）保持兼容，便于互转。
