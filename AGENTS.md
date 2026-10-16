# Repository guidance

This repository contains reusable agent skills and optional Antigravity configuration.

- Shared skills belong in `.agents/skills/<skill-name>/`; keep each skill's `SKILL.md`, scripts, and resources together.
- Keep skill instructions usable across agents. Name product-specific tools only when documenting a conditional tool path, and state what to do when that tool is unavailable.
- Keep Antigravity settings and permissions optional and separate from the shared skill content. Review permission changes for their actual scope before applying them.
- Keep `.agents/skills/` as the only checked-in skill source; do not add duplicate platform-specific copies.
