---
name: 3d-print-spec-extractor
description: >-
  Extracts physical dimensions, port locations, clearances, and tolerances from reference photos, product pages, and datasheets for 3D printing. Use whenever modeling parts to fit real-world products.
---

# 3D Print Spec & Dimension Extractor

Use this skill to gather and report physical dimensions from manufacturer photos, specifications, or product links. Delegate to a research subagent when one is available; otherwise do the research directly. Distinguish sourced dimensions from estimates, and do not present image-derived estimates as precise measurements.

## Workflow

### 1. Acquire Clean Reference Images
- Prefer manufacturer drawings, datasheets, and direct caliper measurements. If downloading images, use a temporary scratch directory and retain the source URL:
  ```bash
  curl -s -L -o scratch/ref_image.png "<image_url>"
  ```
- Prioritize straight-on orthographic or flat perspective shots over angled hero renders when available.
- A single scale applies only to features on approximately the same plane as the calibration feature. Perspective, lens distortion, and depth differences introduce error. Do not claim precision from an angled image; report the limitation or find a better reference.

### 2. Calibrate Scale (px/mm)
Find a known feature in the image to establish the pixel-to-millimeter ratio:
* **Calibration:** Prefer a dimension stated for the exact product or a clearly visible feature in the same plane. Generic connector dimensions depend on whether the plug, receptacle, or surrounding housing is being measured; use them only as rough checks, not precision calibration.

Resolve the bundled script relative to this skill's directory (the directory containing `SKILL.md`), then calculate the scale:
```bash
python3 <skill-directory>/scripts/measure_reference.py calibrate --px <measured_pixels> --mm <known_mm>
```

### 3. Measure Unknown Features
Crop tightly around the target and measure its selected pixel span. `bbox` finds all non-background pixels in an image; it does not identify a particular feature and may include shadows, labels, or other objects. Use image inspection or explicit coordinates to select the intended feature:
```bash
python3 <skill-directory>/scripts/measure_reference.py bbox --image scratch/crop.png --scale <calibrated_scale>
```

Record the source URL/file, view and measurement plane, calibration feature, pixel span, scale, and estimated uncertainty. Label every value as manufacturer-specified, directly measured, image-derived, or estimated. If perspective or occlusion makes a measurement unreliable, say so and request a better source or direct measurement.

### 4. Apply 3D Printing Tolerances
Convert raw physical measurements into CAD modeling targets using standard 3D print clearances (Prusa Core One / 0.4mm nozzle / PLA):
* **Fit terminology:** Always state whether clearance is per side/radial or total added to a width/diameter. For a round fit, radial clearance `c` means the mating hole diameter is increased by `2c`. Treat values below as starting estimates, not guaranteed printer-specific fits.
* **Tight sliding fit (e.g. cylinder cradle):** $+0.2\text{ mm}$ to $+0.3\text{ mm}$ radial clearance (thus $+0.4$ to $+0.6$ mm on diameter).
* **Cable plug pass-through / cutout:** $+1.5\text{ mm}$ to $+2.0\text{ mm}$ per side (thus $+3$ to $+4$ mm total width; e.g. 12 mm plug to 15–16 mm opening).
* **Self-supporting bridges:** Keep flat spans $\le 15\text{ mm}$, or use $45^\circ$ chamfers / rounded arches for larger spans.

### 5. Standard Output Format
Return **only** the completed Mechanical Spec Sheet table to the caller. Adapt rows to the specific features relevant to the object being measured (e.g. mating contours, ports, buttons, mounting tabs, or clearances).

#### Example: Desk Charger Stand Cutout
```markdown
### Mechanical Spec Sheet: [Product / Component Name]
* **Reference Scale:** 20.23 px/mm (calibrated from 60.0 mm base diameter)

| Feature | Raw Dimension / Evidence | 3D Print Target | Clearance / Tolerance Note |
| :--- | :--- | :--- | :--- |
| Outer Mating Body | 60.0 mm | 60.6 mm | +0.3 mm radial slip clearance |
| Port Height from Base | 1.5 mm – 10.1 mm | 0.0 mm – 12.5 mm | +2.4 mm vertical clearance, flush with base floor |
| Cable Cutout Width | 11.5 mm | 16.0 mm | +2.25 mm per side for plug insertion clearance |
| Retained Wall / Bridge | 18.0 mm (total) | 5.5 mm bridge | Overhang arch R=4mm, self-supporting (no supports needed) |
```
