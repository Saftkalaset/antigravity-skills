# Overhangs, Build-Plate Bevels & Mesh Validation

## 1. Support-Free Overhangs & Build-Plate Bevels
- **Build-Plate Bevel Rule ($\le 30^\circ\text{–}35^\circ$ from vertical):** Avoid $45^\circ$ bottom chamfers starting directly at the build plate ($Z = Z_{\min}$), which are prone to upward perimeter curling on the first 10–15 layers. Use either a vertical landing band at $Z = 0$ or steeper **$\le 30^\circ\text{–}35^\circ$ from vertical** ($55^\circ\text{–}60^\circ$ from horizontal) bottom bevels computed along the continuous 2D perimeter normal.
- **Secondary Parts & Tabs:** On secondary parts (such as locking wedges or clips with grip tabs), chamfer overhanging flanges at $\le 35^\circ$ from vertical so they print support-free.
- **Horizontal Tunnels, Hook Slots & Boss Tapers ($\le 43^\circ$ from vertical):** For horizontal pass-through tunnels, J-hook slot roofs, and localized boss tapers, use a **$\le 43^\circ$-from-vertical** ($\text{rise}/\text{run} \ge 1.07$) peaked/teardrop roof for support-free printing (avoiding exact $45.0^\circ$ floating-point boundary false positives in `audit()`), or use a rounded arch and explicitly document required slicer supports in `PROJECT.md`.

## 2. Evaluated Mesh Audit (`lib.audit` & `lib.toolbox_check`)
- Always validate the **evaluated** mesh (modifiers included) using `audit(obj)` and `toolbox_check(obj)` from [`scripts/lib.py`](../scripts/lib.py):
  ```python
  exec(open('<skill-directory>/scripts/lib.py').read(), globals())
  cleanup_mesh(obj)
  audit(obj, overhang_deg=45.0)
  toolbox_check(obj)
  ```
- **Pass Criteria:**
  - `shells == 1` (single connected manifold shell per printable part)
  - `nonmanifold == 0` (zero open boundary or non-manifold edges)
  - `zero_area == 0` (zero degenerate sliver faces $< 10^{-6}\text{ mm}^2$)
  - `overhang_mm2 == 0.0` (or matches only intentional supported regions listed in `PROJECT.md`)
- **3D-Print Toolbox (`toolbox_check(obj)`):** Always use `toolbox_check(obj)` rather than `temp_override(active_object=obj)`. The extension reads `view_layer.objects.active` directly and ignores live modifiers unless baked to a temporary mesh first. If the extension is unavailable, rely on `audit(obj)`.
