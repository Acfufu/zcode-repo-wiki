---
description: 生成、导入或浏览纯本地 Repo Wiki（零上传）
argument-hint: "[generate <仓库路径> | import-legacy <hash|路径> | view <wiki目录>]"
skills: repo-wiki
---

Use the `repo-wiki` skill for this request:

$ARGUMENTS

Hard constraints: the whole workflow must stay local — no network calls, no uploads, never read `.git` object contents. Produce a self-contained static site and report its absolute path.
