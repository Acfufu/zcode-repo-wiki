#!/usr/bin/env bash
# repo-wiki 本地插件安装/升级：同步到 zcode 插件缓存并注册启用。可重复执行。
# 说明：本脚本是本地安装器，不经 zcode 官方安装事务（registry entry 不写 cacheTransactionId）。
set -euo pipefail

: "${HOME:?HOME 未设置}"

for bin in python3 rsync zip; do
  command -v "$bin" >/dev/null 2>&1 || { echo "[install] 缺少依赖命令: $bin" >&2; exit 2; }
done

SELF="${BASH_SOURCE[0]:-$0}"
if readlink -f "$SELF" >/dev/null 2>&1; then
  SELF="$(readlink -f "$SELF")"
fi
ROOT="$(cd "$(dirname "$SELF")" && pwd)"
SRC="$ROOT/repo-wiki"
PLUGIN_JSON="$SRC/.zcode-plugin/plugin.json"
[ -f "$PLUGIN_JSON" ] || { echo "[install] 找不到 $PLUGIN_JSON" >&2; exit 2; }

meta="$(python3 - "$PLUGIN_JSON" <<'PY'
import json, re, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    name, ver = d["name"], d["version"]
except Exception as exc:
    raise SystemExit(f"[install] 失败: plugin.json 读取失败（{exc}）")
if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", name):
    raise SystemExit(f"[install] 失败: plugin.json 的 name 非法: {name!r}（小写字母/数字/._-）")
if not isinstance(ver, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ver):
    raise SystemExit(f"[install] 失败: plugin.json 的 version 非法: {ver!r}")
sys.stdout.write(f"{name}\t{ver}")
PY
)" || { echo "[install] 失败: 无法从 plugin.json 读取 name/version" >&2; exit 2; }
NAME="${meta%%$'\t'*}"
VER="${meta##*$'\t'}"
if [ -z "$NAME" ] || [ -z "$VER" ] || [ "$NAME" = "$meta" ]; then
  echo "[install] 失败: plugin.json 的 name/version 无效" >&2
  exit 2
fi
MARKET="local"
CACHE="$HOME/.zcode/cli/plugins/cache/$MARKET/$NAME/$VER"
TS="$(date +%Y%m%d-%H%M%S)-$$"

# 统一排除清单：测试样本、字节码与本地产物不进缓存/zip
EXCLUDES=(--exclude=__pycache__/ --exclude='*.pyc' --exclude=tests/
          --exclude='*.zip' --exclude=.DS_Store --exclude=.lazyzcode/ --exclude=artifacts/)
ZIP_EXCLUDES=(-x '*/__pycache__/*' -x '*.pyc' -x '*/tests/*' -x '*.zip'
              -x '*/.DS_Store' -x '*/.lazyzcode/*' -x '*/artifacts/*')

mkdir -p "$CACHE"
CACHE_CREATED=0
[ -d "$CACHE" ] || CACHE_CREATED=1
# --delete-excluded：把历史安装遗留的 tests/、__pycache__ 等排除项从缓存中清除
rsync -a --delete --delete-excluded "${EXCLUDES[@]}" "$SRC/" "$CACHE/"

# zip 每次重建（先打临时包再替换）：sha256 与缓存内容保持一致，失败时保留旧包
ZIP_PARENT="$(dirname "$SRC")"
SRC_BASENAME="$(basename "$SRC")"
ZIP_NAME="$NAME-$VER.zip"
ZIP_TMP="$ZIP_NAME.tmp-$$"
rm -f "$ZIP_PARENT/$ZIP_TMP"
if ! (cd "$ZIP_PARENT" && zip -qr "$ZIP_TMP" "$SRC_BASENAME" "${ZIP_EXCLUDES[@]}"); then
  rm -f "$ZIP_PARENT/$ZIP_TMP"
  if [ "$CACHE_CREATED" = 1 ]; then
    rm -rf "$CACHE"
    echo "[install] 失败: zip 打包失败，已回滚本次新建的缓存目录，旧包保持不动" >&2
  else
    echo "[install] 失败: zip 打包失败，注册未完成（缓存内容已更新），旧包保持不动" >&2
  fi
  exit 3
fi
mv -f "$ZIP_PARENT/$ZIP_TMP" "$ZIP_PARENT/$ZIP_NAME"

python3 - "$NAME" "$VER" "$MARKET" "$CACHE" "$SRC" "$TS" <<'PY'
import hashlib, json, os, sys, time
from pathlib import Path

name, ver, market, cache, src, ts = sys.argv[1:7]
plug_dir = Path.home() / ".zcode" / "cli" / "plugins"
zip_path = Path(src).parent / f"{name}-{ver}.zip"
sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()

def read_json(path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"[install] 失败: {path} 不是合法 JSON（{exc}）")

now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
ipf = plug_dir / "installed_plugins.json"
ip = read_json(ipf, {"version": 1, "plugins": []})
if not isinstance(ip, dict):
    raise SystemExit(f"[install] 失败: {ipf} 顶层不是 JSON 对象")
plugins = ip.get("plugins")
if not isinstance(plugins, list):
    raise SystemExit(f"[install] 失败: {ipf} 的 plugins 不是列表")
entry_id = f"{name}@{market}"
prev = next((p for p in plugins if isinstance(p, dict) and p.get("id") == entry_id), None)
entry = {
    "id": entry_id,
    "name": name,
    "marketplace": market,
    "version": ver,
    "installPath": str(cache),
    "installedAt": (prev or {}).get("installedAt") or now,
    "updatedAt": now,
    "scope": "user",
    "source": {
        "source": "url",
        "type": "zip",
        "url": f"file://{Path(src).parent}",
        "sha256": sha,
        "path": name,
    },
}

plugins = [p for p in plugins if not (isinstance(p, dict) and p.get("id") == entry_id)]
plugins.append(entry)
ip["plugins"] = plugins
ip.setdefault("version", 1)

setting = plug_dir.parent / "setting.json"
legacy = plug_dir.parent / "config.json"
setting_data = read_json(setting, None)
legacy_data = read_json(legacy, None) if legacy.exists() else None
if setting_data is not None and not isinstance(setting_data, dict):
    print(f"[install] WARN {setting} 不是 JSON 对象，将重建为最小结构", file=sys.stderr)
    setting_data = None
if legacy_data is not None and not isinstance(legacy_data, dict):
    print(f"[install] WARN {legacy} 不是 JSON 对象，已跳过同步", file=sys.stderr)
    legacy_data = None
if setting_data is None:
    if legacy_data is not None:
        setting_data = legacy_data       # 老版本只有 config.json：以其结构新建 setting.json
        legacy_data = None
    else:
        setting_data = {"version": 1, "plugins": {"enabledPlugins": {}}}

def enable(data):
    data.setdefault("plugins", {}).setdefault("enabledPlugins", {})[entry_id] = True

enable(setting_data)
if legacy_data is not None:
    enable(legacy_data)

# 先把三份内容全部落到临时文件，再统一备份+替换（失败不留半安装状态）
def file_mode(path):
    try:
        return path.stat().st_mode & 0o7777
    except OSError:
        return None

def stage_json(path, data):
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # 既有文件保留原权限；新建的配置文件用 0600（zcode 配置可能含凭据）
    os.chmod(tmp, file_mode(path) if path.exists() else 0o600)
    return tmp

staged = []
try:
    staged.append((ipf, stage_json(ipf, ip)))
    staged.append((setting, stage_json(setting, setting_data)))
    if legacy_data is not None:
        staged.append((legacy, stage_json(legacy, legacy_data)))
except OSError as exc:
    for _path, tmp in staged:
        try:
            tmp.unlink()
        except OSError:
            pass
    raise SystemExit(f"[install] 失败: 无法写入临时文件（{exc}）")

for path, _tmp in staged:
    if path.exists():
        bak = path.with_name(path.name + f".bak-{ts}")
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        os.chmod(bak, file_mode(path) or 0o600)   # 备份与源文件同权限，避免凭据副本被放宽
for path, tmp in staged:
    os.replace(tmp, path)

print(f"[install] 已注册并启用 {entry_id} → {cache}")
print(f"[install] zip: {zip_path.name} sha256={sha[:12]}…（已排除 tests/、__pycache__ 等）")
PY

# 旧版本缓存目录提示（不删除用户数据）
CACHE_BASE="$HOME/.zcode/cli/plugins/cache/$MARKET/$NAME"
OLD="$(ls -1 "$CACHE_BASE" 2>/dev/null | grep -vx "$VER" || true)"
if [ -n "$OLD" ]; then
  echo "[install] 提示: 缓存中还有旧版本目录（可手动清理）: $(echo "$OLD" | tr '\n' ' ')" >&2
fi

if command -v zcode >/dev/null 2>&1; then
  zcode plugins list || echo "[install] 提示: zcode plugins list 失败（不影响安装结果）" >&2
else
  echo "[install] 提示: 未找到 zcode 命令，跳过插件列表校验" >&2
fi
