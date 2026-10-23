# <Project Name>
Status: v1 | Updated: YYYY-MM-DD | Blender: 5.2+ | Printer: Prusa Core One (0.4mm, PLA)

## 1. Goal & Constraints
- **Function:** <1-2 sentences on what the part does and what it mates with>
- **Fit & Print:** <bed orientation, support strategy, critical load direction>

## 2. Dimensions & Clearances (mm)
| Feature | Nominal | Clearance | **CAD Target** | Source / Confidence |
| :--- | ---: | ---: | ---: | :--- |
| <e.g. Stand column OD> | 60.0 | +0.20 /side (+0.40 Ø) | **60.40 ID** | <spec / caliper / photo (high/med/low)> |

## 3. Scene Map (all local meshes centered on `(0,0,0)`; positioned via `obj.location`)
- `1_Printable_Parts`: `<Main_Part>` (`0, 0, 0`)
- `2_Boolean_Cutters` (`hide_set(True)`, `hide_viewport=False`): `Cutter_<Feature>` (`x, y, z`)
- `3_References`: `<Ref_Object>` (`x, y, z`), `KeepOut_<Feature>` (wireframe clearance volumes)
- **In-File Cache:** Detailed port/vent coordinates cached in `scene["cad_specs"]` (`get_specs()`); parametric rebuild script stored in `bpy.data.texts["parametric_recipe.py"]` (`get_recipe()`).

## 4. Active Decisions (current rules only — history in `LOG.md`)
- <Active design constraint or rule>

## 5. Latest Audit & Next Actions
- `AUDIT <Main_Part>`: `size=(...) vol=...cm3 shells=1 nonmanifold=0 zero_area=0 overhang>45deg=...mm2 keepout_hits=0 -> PASS`
- [ ] <Next concrete step>
