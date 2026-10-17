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

### 4. Apply 3D Printing Tolerances (Prusa Core One / 0.4mm Nozzle / PLA)
Convert raw physical measurements into CAD modeling targets:
* **Fit terminology:** Always state both per-side (radial) and total (diametral) clearance (`ID = OD + 2c`). Distinguish the **CAD target** from the **as-printed dimension**: enclosed circular bores in PLA shrink by $\sim 0.15\text{–}0.20\text{ mm}$ on the Prusa Core One due to chordal facet approximation and thermal contraction.
* **Snug locating slip fit (e.g. cylinder collar):** $+0.20\text{ mm}$ radial ($+0.40\text{ mm}$ diametral; e.g., $60.0\text{ mm}$ column $\rightarrow 60.40\text{ mm}$ CAD ID $\rightarrow \approx 60.20\text{ mm}$ as-printed ID, leaving $\sim 0.10\text{ mm}$ physical clearance per side).
* **Loose clearance fit:** $+0.30\text{ mm}$ radial ($+0.60\text{ mm}$ diametral).
* **Uncertain nominal dimensions ($\pm 0.3\text{ mm}$ or image-derived):** Recommend printing a fast $5\text{ mm}$-tall fit-test ring coupon before printing the full body.
* **Cable plug pass-through / cutout:** $+1.5\text{ mm}$ to $+2.25\text{ mm}$ per side ($+3.0$ to $+4.5\text{ mm}$ total width).
* **Horizontal arches & bridges:** A $45^\circ$ peaked/teardrop roof is self-supporting; a smooth rounded arch with a flat center tangent requires slicer supports (or accepts minor inner-layer sag) on spans $> 10\text{ mm}$.

### 5. Standard Output Format (Matches `PROJECT.md` Section 2)
Return **only** the completed Mechanical Spec Sheet table in the exact 5-column format used by `PROJECT.md` so the caller can paste it directly without reformatting:

```markdown
### Mechanical Spec Sheet: [Product / Component Name]
* **Reference Scale:** 20.23 px/mm (calibrated from 60.0 mm base diameter)

| Feature | Nominal | Clearance | **CAD Target** | Source / Confidence |
| :--- | ---: | ---: | ---: | :--- |
| Stand Base Column Ø | 60.0 | +0.20 /side (+0.40 Ø) | **60.40 ID** | Product spec + Core One PLA shrinkage compensation (med-high) |
| Cable Cutout (W × H) | 11.5 × 7.0 | +2.25 /side, +5.5 H | **16.0 × 12.5** | USB-C housing + strain relief boot (high; rounded arch w/ support) |
```
