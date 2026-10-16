# Shared Agent Skills & Antigravity Configuration

Personal skills and configuration shared by Codex and Google Antigravity.

## Skills

Skills live in `.agents/skills/`, which Codex and Antigravity discover when this repository is open.

### `3d-print-blender`
Workflow for designing, validating, and iterating 3D printable parts in Blender, using MCP when available.
- **Hardware Profile:** Prusa Core One (0.4mm nozzle, PLA)
- **File Management:** Stores projects in `~/Documents/Blender files/<Project Name>/`
- **Versioning:** Sequential `.blend` files (`_v<N>[_<description>].blend`) and matched `.3mf` exports
- **Mesh Validation:** 3D-Print Toolbox extension and `MANIFOLD` solver verification

### `3d-print-spec-extractor`
Extracts physical dimensions, port heights, and clearances from manufacturer photos, datasheets, and web links for 3D modeling.
- **Role:** Typically delegated to a `research` subagent to prevent context bloat
- **Toolkit:** Bundled CLI tool `scripts/measure_reference.py` using Pillow & NumPy for pixel-to-millimeter scaling
- **Output:** Standardized mechanical spec sheets with 3D print fit tolerances

## Quick Setup (New Machine)

Prerequisites for the optional Antigravity setup: Bash, Python 3, and the Antigravity CLI configuration layout expected by this repository. The image measurement helper additionally requires Pillow and NumPy (`python3 -m pip install Pillow numpy`). The shared workspace skills need no setup when you open this repository in Codex or Antigravity.

To link all skills and apply the non-destructive whitelist permissions on a new machine:

```bash
git clone git@github.com:Saftkalaset/antigravity-skills.git ~/Documents/antigravity-skills
cd ~/Documents/antigravity-skills
./setup.sh
```

### What `./setup.sh` does:
1. Symlinks all skills in `.agents/skills/` to Antigravity's existing global IDE/App location, `~/.gemini/config/skills/`. Antigravity CLI also discovers the workspace skills directly from `.agents/skills/`.
2. Merges the command and MCP allow-list entries in `config/permissions.json` into `~/.gemini/antigravity-cli/settings.json` without removing unrelated machine-specific settings.

Codex discovers these skills and `AGENTS.md` from the repository without setup. Codex-specific Blender MCP and external project-folder access are documented in [docs/codex-setup.md](docs/codex-setup.md); they require local connection details and are not added to Antigravity's permissions file.

Setup refuses to replace a non-symlink at a skill destination and refuses malformed settings JSON. Existing settings are backed up before they are updated. Permissions are broad command/tool allow-list entries; review `config/permissions.json` against your CLI's permission semantics before applying it, especially shell, network, Docker, and write-capable Git commands.

## Workflow

For each model: capture requirements and sourced dimensions in `PROJECT.md`, model and inspect in Blender, run and report available mesh checks, export 3MF, confirm the file exists, and update the project log with validation results and remaining uncertainties. Image-based dimensions remain estimates unless independently verified.

## Undo Setup

Remove the skill symlinks created under `~/.gemini/config/skills/` to disable the global Antigravity IDE/App copies. The repository skills remain available to Codex and Antigravity while this repository is open. To revert the settings merge, restore the desired timestamped `settings.json.bak.*` file from `~/.gemini/antigravity-cli/`.
