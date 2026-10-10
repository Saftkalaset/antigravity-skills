# Antigravity Skills

Personal skills and workflows for Google Antigravity / Gemini CLI.

## Skills

### `blender-3d-printing`
Optimized workflow for designing and iterating 3D printable parts in Blender via MCP.
- **Hardware Profile:** Prusa Core One (0.4mm nozzle, PLA)
- **File Management:** Stores projects in `~/Documents/Blender files/<Project Name>/`
- **Versioning:** Sequential `.blend` files (`_v<N>[_<description>].blend`) and matched `.3mf` exports

## Installation / Linking

To link these skills into Antigravity on a new machine:

```bash
# Link the skills directory or individual skills into ~/.gemini/config/skills/
mkdir -p ~/.gemini/config/skills
ln -s "$(pwd)/skills/blender-3d-printing" ~/.gemini/config/skills/blender-3d-printing
```
