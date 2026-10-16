#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Setting up Antigravity Skills & Whitelist ==="

# 1. Symlink shared workspace skills to the existing global Antigravity IDE/App config
mkdir -p "$HOME/.gemini/config/skills"
for skill in "$SCRIPT_DIR"/.agents/skills/*; do
  if [ -d "$skill" ]; then
    name="$(basename "$skill")"
    target="$HOME/.gemini/config/skills/$name"
    if [ -e "$target" ] && [ ! -L "$target" ]; then
      echo "[!] Refusing to replace existing non-symlink: $target" >&2
      exit 1
    fi
    ln -sfn "$skill" "$target"
    echo "[✓] Linked skill: $name -> ~/.gemini/config/skills/$name"
  fi
done

# 2. Merge permissions whitelist into ~/.gemini/antigravity-cli/settings.json
mkdir -p "$HOME/.gemini/antigravity-cli"
SETTINGS_FILE="$HOME/.gemini/antigravity-cli/settings.json"
PERMISSIONS_FILE="$SCRIPT_DIR/config/permissions.json"

python3 - <<EOF
import json, os, shutil, sys, tempfile, time

settings_path = "$SETTINGS_FILE"
permissions_path = "$PERMISSIONS_FILE"

if not os.path.exists(permissions_path):
    print("[!] No permissions.json found.")
    exit(0)

with open(permissions_path, 'r') as f:
    allowed = json.load(f)
if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
    raise SystemExit("permissions.json must contain a JSON array of strings")

if os.path.exists(settings_path):
    with open(settings_path, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON in {settings_path}; left unchanged: {exc}")
else:
    data = {}

if not isinstance(data, dict):
    raise SystemExit(f"Expected a JSON object in {settings_path}; left unchanged")
if "permissions" in data and not isinstance(data["permissions"], dict):
    raise SystemExit(f"Expected permissions to be an object in {settings_path}; left unchanged")
permissions = data.setdefault("permissions", {})
if "allow" in permissions and (not isinstance(permissions["allow"], list) or not all(isinstance(x, str) for x in permissions["allow"])):
    raise SystemExit(f"Expected permissions.allow to be an array of strings in {settings_path}; left unchanged")

current_perms = set(permissions.get("allow", []))
current_perms.update(allowed)
permissions["allow"] = sorted(current_perms)

if os.path.exists(settings_path):
    backup = settings_path + ".bak." + time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(settings_path, backup)
    print(f"[i] Backup: {backup}")
fd, temp_path = tempfile.mkstemp(prefix="settings.", suffix=".tmp", dir=os.path.dirname(settings_path))
try:
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    with open(temp_path, 'r') as f:
        json.load(f)
    os.replace(temp_path, settings_path)
except Exception:
    try: os.unlink(temp_path)
    except FileNotFoundError: pass
    raise

print(f"[✓] Whitelist updated: {len(data['permissions']['allow'])} permissions active in {settings_path}")
EOF

echo "=== Setup complete! ==="
