#!/usr/bin/env bash
# repo-wiki 本地插件安装/升级：同步到 zcode 插件缓存并注册启用。可重复执行。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/repo-wiki"
NAME="$(python3 -c "import json;print(json.load(open('$SRC/.zcode-plugin/plugin.json'))['name'])")"
VER="$(python3 -c "import json;print(json.load(open('$SRC/.zcode-plugin/plugin.json'))['version'])")"
MARKET="local"
CACHE="$HOME/.zcode/cli/plugins/cache/$MARKET/$NAME/$VER"
TS="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$CACHE"
rsync -a --delete "$SRC/" "$CACHE/"

python3 - "$NAME" "$VER" "$MARKET" "$CACHE" "$SRC" "$TS" <<'PY'
import hashlib, json, subprocess, sys, time
from pathlib import Path

name, ver, market, cache, src, ts = sys.argv[1:7]
plug_dir = Path.home() / ".zcode" / "cli" / "plugins"

# provenance: 与官方 file:// 安装一致的 sha256（对源目录 zip 的摘要）
zip_path = Path(src).parent / f"{name}-{ver}.zip"
if not zip_path.exists():
    subprocess.run(["zip", "-qr", zip_path.name, name], cwd=Path(src).parent, check=True)
sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()

ipf = plug_dir / "installed_plugins.json"
ipf.with_suffix(f".json.bak-{ts}").write_text(ipf.read_text())
ip = json.loads(ipf.read_text())
entry = {
    "id": f"{name}@{market}",
    "name": name,
    "marketplace": market,
    "version": ver,
    "installPath": str(cache),
    "installedAt": ip.get("installedAt") or time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
    "scope": "user",
    "source": {
        "source": "url",
        "type": "zip",
        "url": f"file://{Path(src).parent}",
        "sha256": sha,
        "path": name,
    },
}
plugins = [p for p in ip.get("plugins", []) if p.get("id") != entry["id"]]
plugins.append(entry)
ip["plugins"] = plugins
ipf.write_text(json.dumps(ip, ensure_ascii=False, indent=2))

for cfg in (plug_dir.parent / "config.json", plug_dir.parent / "setting.json"):
    if not cfg.exists():
        continue
    cfg.with_suffix(f".json.bak-{ts}").write_text(cfg.read_text())
    data = json.loads(cfg.read_text())
    data.setdefault("plugins", {}).setdefault("enabledPlugins", {})[entry["id"]] = True
    cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2))
print(f"[install] 已注册并启用 {entry['id']} → {cache}")
PY

zcode plugins list
