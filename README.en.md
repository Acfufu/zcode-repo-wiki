<div align="center">

  <img src="docs/assets/logo.svg" alt="repo-wiki" width="104">

  <h1>repo-wiki</h1>

  <p><strong>A local-only repository wiki: zero upload, zero network.</strong><br />
  An agent reads the repo on your machine and writes a paged wiki — directory tree, diagrams, file-level evidence — then builds it into a single self-contained site.</p>

  <p><em>Replaces the official Repo Wiki entry that ZCode removed in 3.14.0.</em></p>

  <p>
    <a href="repo-wiki/README.md">Plugin docs</a> ·
    <a href="#-install">Install</a> ·
    <a href="#-usage">Usage</a> ·
    <a href="#-what-it-looks-like">Screenshots</a> ·
    <a href="#-privacy">Privacy</a> ·
    <a href="CHANGELOG.md">Changelog</a>
  </p>

  <p>English · <a href="README.md">简体中文</a></p>

  <br />

  <a href="https://github.com/Acfufu/zcode-repo-wiki/actions/workflows/test.yml"><img src="https://github.com/Acfufu/zcode-repo-wiki/actions/workflows/test.yml/badge.svg" alt="test"></a>

  <br />
</div>

> [!NOTE]
> **What a codebase knows should not live only in the original author's head — and it should not cost you uploading the whole repo.**
>
> repo-wiki has an agent read your code locally, splits it into pages by theme, and writes prose plus diagrams with **file-path and line-number evidence**. The result is one HTML file you can double-click open. No CDN, no font requests, no telemetry: the mermaid runtime is inlined whole and the built site has zero external links — not by convention, but enforced by a build-time check.
>
> ```bash
> git clone https://github.com/Acfufu/zcode-repo-wiki && cd zcode-repo-wiki && bash install.sh
> ```

## 🖼️ What it looks like

The generated site is a single self-contained file: sidebar tree, full-text search, light/dark themes, narrow-screen layout — all offline.

<img src="docs/assets/viewer-light.png" alt="Viewer (light theme): sidebar tree, path chips, source badges, mermaid diagram" width="100%">

<details>
<summary>Dark theme / full-text search / narrow screen</summary>

<img src="docs/assets/viewer-dark.png" alt="Viewer (dark theme)" width="100%">

<img src="docs/assets/viewer-search.png" alt="Full-text search hits" width="100%">

<img src="docs/assets/viewer-mobile.png" alt="Narrow-screen layout" width="260">

</details>

The screenshots come from the demo shipped in this repo — `docs/demo/`, a wiki about this very repository. You do not need an agent to see it:

```bash
python3 repo-wiki/scripts/build_wiki_site.py build --wiki docs/demo
open docs/demo/site/index.html        # Linux: xdg-open
```

## 🚀 Install

Requirements: the ZCode desktop app (signed in), plus `python3`, `rsync` and `zip`. The builder is pure Python 3 standard library (≥3.7) with no third-party dependencies.

```bash
git clone https://github.com/Acfufu/zcode-repo-wiki
cd zcode-repo-wiki
bash install.sh          # sync into the engine plugin cache → register → enable (idempotent)
```

`install.sh` syncs `repo-wiki/` into `~/.zcode/cli/plugins/cache/local/repo-wiki/<version>/`, writes a sha256-pinned registry entry into `installed_plugins.json`, and enables the plugin in `setting.json`. All three JSON files are validated first and written atomically (tmp + replace) so a failure never leaves a half-installed state; newly created config files get mode `0600`. The `<name>-<version>.zip` at the repo root is only rebuilt when missing or older than its sources.

## 🧭 Usage

Ask in a session, or use the command:

```
/repo-wiki generate <repo path>      # generate the wiki, build the site, self-check
/repo-wiki import-legacy <hash>      # import legacy (≤3.13) data
/repo-wiki view <wiki dir>           # rebuild the site after content changes
```

Override generation parameters inline: `/repo-wiki generate <repo path> --set language=en --set profile=legacy`.

Or drive the script directly (diagnostics on stderr, data on stdout):

```bash
python3 repo-wiki/scripts/build_wiki_site.py build          --wiki <repo>/.zcode-wiki
python3 repo-wiki/scripts/build_wiki_site.py selfcheck      --wiki <repo>/.zcode-wiki
python3 repo-wiki/scripts/build_wiki_site.py resolve-config --repo <repo path> [--set k=v …]
python3 repo-wiki/scripts/build_wiki_site.py import-legacy  <hash|abs path>
```

Artifacts land in `<repo>/.zcode-wiki/`: `wiki.json` (single source of truth), `pages/<id>.md` (exported copies), `generation-meta.json` (effective config with provenance), `site/index.html` (the self-contained site).

## 🧩 Capabilities

| Capability | What it gives you |
| --- | --- |
| 📄 **Paged wiki** | Directory tree plus `description` / `filePaths` / source badges per page; page count, page length and split granularity (`theme`/`file`/`hybrid`) are configurable |
| 🧭 **Diagrams** | mermaid fences render offline with the inlined runtime; `diagrams=minimal/rich` controls how often architecture and data-flow pages get one |
| 🧾 **Evidence first** | Claims cite `` `path:line` ``; `selfcheck` fails the build unless every citation resolves to a real file and an in-range line |
| 🔍 **Full-text search** | Built-in index in the site, keyboard-operable hits (Tab + Enter); 20k characters per page participate |
| 🌗 **Two themes** | Follows the system, with manual toggle and localStorage persistence |
| 📱 **Narrow screens** | Below 760px the sidebar stacks above the content |
| 🛡️ **Sanitizing and checks** | Pass-through SVG goes through an XML-parser allowlist and is re-serialized; the external-link scan covers entities, protocol-relative URLs, CSS `url()` and `@import` |
| 🎛️ **Generation config** | Four-layer merge (builtin → global → repo → flags) with per-field provenance; presets `compact`/`standard`/`deep`/`legacy` |
| 📦 **Legacy import** | Converts `~/.zcode/v2/repo-wiki/<hash>/` data into this plugin's format and builds the site |

Full behavior notes (sanitizer details, config ranges, known limits) live in [`repo-wiki/README.md`](repo-wiki/README.md) (Chinese); the agent-side generation protocol is [`repo-wiki/skills/repo-wiki/SKILL.md`](repo-wiki/skills/repo-wiki/SKILL.md).

## 🔒 Privacy

| Behavior | repo-wiki |
| --- | --- |
| Uploading repo content / Git history | Never |
| Network requests (generation, diagrams, fonts, scripts) | Never |
| Reading `.git` object contents | Never (sole exception: the optional `git log --oneline -15` summary command) |
| Where artifacts go | Your local disk only |

The boundaries are stated just as plainly: the external-link check is a **bounded heuristic** (it cannot prove that no input ever produces an external link), and this plugin constrains the shape of its artifacts, not the agent's behavior. See [`SECURITY.md`](SECURITY.md).

## 🧱 Repository layout

```
zcode-repo-wiki/
├── install.sh                      # local installer: sync into the engine cache, register, enable
├── repo-wiki/                      # the plugin payload (distributed through the local marketplace)
│   ├── .zcode-plugin/plugin.json   # manifest (name/version/description/keywords)
│   ├── skills/repo-wiki/SKILL.md   # agent generation protocol: hard constraints + 5 phases
│   ├── commands/repo-wiki.md       # the /repo-wiki command
│   ├── scripts/build_wiki_site.py  # builder: build / selfcheck / resolve-config / import-legacy
│   ├── assets/mermaid.min.js       # offline diagram runtime (third-party notices included)
│   └── tests/                      # regression suite + fixture samples
├── docs/
│   ├── assets/                     # logo and viewer screenshots
│   └── demo/                       # demo wiki (wiki.json; the built site/ is not committed)
└── .github/workflows/test.yml      # regression tests + demo self-check
```

## 🧪 Tests

```bash
python3 repo-wiki/tests/test_build_wiki_site.py     # stdlib only, no arguments, does not write the repo
```

It covers fixture build and self-check, config merge and validation edges, injection and sanitizing (including Chrome-level PoCs), clean failures and atomic writes, and the display-name fallback; it prints `N/N passed` at the end.

CI ([`test.yml`](.github/workflows/test.yml)) runs on Ubuntu (3.9/3.11/3.13) and macOS (3.13), and does two extra things: a **real syntax check** of the site's inlined scripts via `node --check` (the viewer's search, theme toggle and mermaid rendering all live in that script, and substring assertions cannot catch a syntax error), and `build + selfcheck` of the demo so citation line numbers cannot drift.

## 📄 License

MIT — see [`LICENSE`](LICENSE). The `repo-wiki/` directory ships its own copy with the plugin.

The inlined mermaid runtime bundle contains third-party components (mermaid, DOMPurify and others); their notices are in [`repo-wiki/assets/THIRD-PARTY-NOTICES`](repo-wiki/assets/THIRD-PARTY-NOTICES).
