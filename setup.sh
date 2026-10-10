#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Setting up Antigravity Skills & Whitelist ==="

# 1. Symlink skills to global Antigravity config
mkdir -p "$HOME/.gemini/config/skills"
for skill in "$SCRIPT_DIR"/skills/*; do
  if [ -d "$skill" ]; then
    name="$(basename "$skill")"
    ln -sfn "$skill" "$HOME/.gemini/config/skills/$name"
    echo "[✓] Linked skill: $name -> ~/.gemini/config/skills/$name"
  fi
done

# 2. Merge permissions whitelist into ~/.gemini/antigravity-cli/settings.json
mkdir -p "$HOME/.gemini/antigravity-cli"
SETTINGS_FILE="$HOME/.gemini/antigravity-cli/settings.json"
PERMISSIONS_FILE="$SCRIPT_DIR/config/permissions.json"

python3 - <<EOF
import json, os

settings_path = "$SETTINGS_FILE"
permissions_path = "$PERMISSIONS_FILE"

if not os.path.exists(permissions_path):
    print("[!] No permissions.json found.")
    exit(0)

with open(permissions_path, 'r') as f:
    allowed = json.load(f)

if os.path.exists(settings_path):
    with open(settings_path, 'r') as f:
        try:
            data = json.load(f)
        except Exception:
            data = {}
else:
    data = {}

current_perms = set(data.get("permissions", {}).get("allow", []))
current_perms.update(allowed)

if "permissions" not in data:
    data["permissions"] = {}
data["permissions"]["allow"] = sorted(list(current_perms))

with open(settings_path, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')

print(f"[✓] Whitelist updated: {len(data['permissions']['allow'])} permissions active in {settings_path}")
EOF

echo "=== Setup complete! ==="
