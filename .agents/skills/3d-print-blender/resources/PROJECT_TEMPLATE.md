# <Project Name>

> **Status:** [In Progress | Prototype vX | Ready to Print | Validated]  
> **Last Updated:** YYYY-MM-DD  
> **Blender Version:** [version]  

---

## 1. Goal & Requirements
- **Core Function:** What this part does, who/what it connects with, and primary design constraints.
- **Ergonomics & Usage:** How it is handled, grabbed, or placed (one-handed operation, clearances, visibility).
- **Physical Environment:** Tabletop, mount, cable routing, desk stability.

---

## 2. Hardware Specs & References

### References Used
- **[Device / Part 1]:** Datasheet URL, product page, or reference photo path.
- **[Device / Part 2]:** Teardown link, caliper measurements, or user verification.

### Critical Dimensions & Clearances

| Component / Feature | Nominal / Evidence Type | Source / Method / Uncertainty | Toleranced CAD Target | Fit / Clearance Convention |
| :--- | :--- | :--- | :--- |
| **Feature 1** | 0.0 mm | **0.0 mm** | Clearance notes (slip fit, press fit, etc.) |
| **Feature 2** | 0.0 mm | **0.0 mm** | ... |

### Scene Structure & Coordinate Origins

| Collection | Object Name | Role / Modifiers | Functional Origin `(X, Y, Z)` | Notes |
| :--- | :--- | :--- | :--- | :--- |
| `1_Printable_Parts` | `<Main_Part>` | Primary printable body (`MANIFOLD` booleans) | `(0.0, 0.0, 0.0)` | Exported to `<Project_Name>.3mf` |
| `2_Boolean_Cutters` | `Cutter_<Feature>` | Analytical cutter (`Mirror` if symmetric) | Feature axis center | Hidden via `hide_set(True)` (`hide_viewport=False`) |
| `3_References` | `Ref_<Product>` | Consolidated multi-material reference / scan | Mating interface center | Non-printable verification reference |

---

## 3. Key Decisions & Lessons Learned
*Log of design choices and rejected approaches (prevents repeating discarded mistakes).*

- **[DEC-001] [Topic]:**
  - *Conflict / Problem:* Description of the initial issue or conflict.
  - *Resolution / Rationale:* Why the chosen direction was selected and what was abandoned.

---

## 4. Iteration Log
*Archive map of versions in `history/`.*

| Version | File / Snapshot | Key Changes | Status / Outcome |
| :--- | :--- | :--- | :--- |
| **v1** | `history/<Project_Name>_v1.blend` | Initial prototype. | Superseded. |
| **v2** | `history/<Project_Name>_v2.blend` | Refined geometry. | Current release. |

---

## 5. Print Guidelines & Next Steps

- **Printer:** Prusa Core One (0.4mm nozzle).
- **Material:** PLA.
- **Print Bed Orientation:** Recommended resting face on build plate ($Z = 0$).
- **Supports:** None / Specific overhang details.
- **Slicer Settings:** Perimeters (walls), infill pattern and density.
- **Mesh Status:** Manifold shell, 0 non-manifold edges.
- **Validation Performed:** List checks and results; distinguish automated checks from visual review and physical test prints.
- **Export Status:** File path, date, and whether the 3MF was confirmed to exist and be non-empty.
- **Known Limitations:** Uncertain measurements, untested fits, or unsupported validation claims.

### Next Actions
- [ ] Task 1.
- [ ] Task 2.
