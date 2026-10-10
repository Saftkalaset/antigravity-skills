# Antigravity Skills & Configuration

Personal skills, workflows, and whitelisted permissions for Google Antigravity / Gemini CLI.

## Skills

### `blender-3d-printing`
Optimized workflow for designing and iterating 3D printable parts in Blender via MCP.
- **Hardware Profile:** Prusa Core One (0.4mm nozzle, PLA)
- **File Management:** Stores projects in `~/Documents/Blender files/<Project Name>/`
- **Versioning:** Sequential `.blend` files (`_v<N>[_<description>].blend`) and matched `.3mf` exports

## Quick Setup (New Machine)

To link all skills and apply the non-destructive whitelist permissions on a new machine:

```bash
git clone git@github.com:Saftkalaset/antigravity-skills.git ~/Documents/antigravity-skills
cd ~/Documents/antigravity-skills
./setup.sh
```

### What `./setup.sh` does:
1. Symlinks all skills in `skills/` to `~/.gemini/config/skills/`
2. Merges the persistent non-destructive commands and MCP functions in `config/permissions.json` into `~/.gemini/antigravity-cli/settings.json`, ensuring uninterrupted agent workflow across all workspaces without clobbering machine-specific settings.
