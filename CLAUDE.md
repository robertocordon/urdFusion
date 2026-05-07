# urdFusion

A Fusion 360 add-in (Python) that exports robot models to URDF. See `README.md` for the full roadmap.

## Architecture

Thin entry point + modules pattern:

- `urdFusion.py` — Fusion add-in entry point. Owns the toolbar button, command/event handler scaffolding, and module reloads. The Fusion-required `run(context)` and `stop(context)` live here. Does **not** contain export logic.
- `modules/urdFusionMain.py` — Top-level orchestrator (`execute(ui)`). Owns the export pipeline: shows dialog, runs validation, exports. New steps in the pipeline get added here.
- `modules/linkSelectionDialog.py` — UI module. Builds the Fusion command dialog (Export mode, Links selection input, Base Link dropdown, Export STLs checkbox, Link Colors dropdown). Async by Fusion's design — exposes `show(ui, on_complete)` where `on_complete(components, base_link, export_stls, color_choice)` is a callback fired on OK. `color_choice` is either `COLOR_MODE_MATERIAL`, `COLOR_MODE_RAINBOW`, or a palette color name string.
- `modules/linkSelection.py` — Validation and naming logic on selected components. `checkAllBodiesSelected` verifies all visible bodies are covered. `getUniqueLinkNames` returns a `{link_name: occurrence}` dict where keys are sanitized, unique, ROS-legal names. `getRootLinkName` returns the sanitized design name (strips Fusion's trailing ` v<n>` version suffix before sanitizing). No UI ownership; shows its own dialogs for validation failures.
- `modules/urdfLink.py` — Data model and collection logic. Defines `URDFLink` and its nested dataclasses (`Naming`, `Point3`, `Inertia`). Exposes `collectLinksData(link_names, base_link)` which returns a list of `URDFLink` objects — base link first (named `base_link`), remainder sorted by link name. All values in SI units (m, kg, kg·m²). This is the module exporters (CSV, URDF XML, etc.) should call.
- `modules/urdfExport.py` — Export orchestration. `selectExportFolder(ui)` asks the user for a folder once; `exportCsv`, `exportStls`, and `exportUrdf` all take that folder. CSV is saved as `<robot_name>.csv` directly in the folder. STLs are saved into an `STL/` subdirectory (wiped clean before each export to remove stale files). STL export warns if any link has hidden bodies (they are excluded from the mesh but their mass is still counted). URDF is saved as `<robot_name>.urdf`.
- `modules/urdfJoint.py` — Joint data model and collection logic. Defines `JointData`. Exposes `collectJointsData(link_names, base_link)` which returns `(joints, child_visual_origins)` — `joints` is a list of `JointData` in BFS order from base_link; `child_visual_origins` is `{link_name: (xyz_tuple, rpy_tuple)}` giving the visual mesh origin for each non-base link in its joint frame.
- `modules/urdfMaterials.py` — Material color assignment. Exposes `getAvailableColors()` (deterministic list of `(name, rgba)` palette entries), `populateMaterials(links, joints, color_choice, link_names, base_link)` which assigns `lnk.material` on every `URDFLink` and returns a deduplicated list of `MaterialData(name, rgba)` for the materials actually used. Three modes: `COLOR_MODE_MATERIAL` (dominant physical material by mass per link; ties broken alphabetically; falls back to a palette color when Fusion can't expose an RGBA), `COLOR_MODE_RAINBOW` (depth from base_link via joints, palette wraps with modulo), or any palette color name (uniform single color).

Modules in `modules/` should:
- Not import `urdFusion.py` (it's the entry point, not a library)
- Be safe to `importlib.reload` (no module-level side effects beyond defining things)
- Expose camelCase public functions; helpers prefixed with `_`
- Receive `ui` as a parameter rather than reaching for `adsk.core.Application.get().userInterface` (except where unavoidable, e.g. inside event handlers)

## Development workflow

Fusion caches imported modules. There are two reload paths:

1. **Changes to `urdFusion.py`** — toggle the add-in off/on via Shift+S → Add-Ins. Fusion holds references to the loaded `run()` and `stop()`, so `importlib.reload` can't replace them.
2. **Changes to anything in `modules/`** — just press the toolbar button. `urdFusion.py`'s `reloadModules()` reloads every module before calling `urdFusionMain.execute(ui)`.

Reload order in `reloadModules()` matters: deepest dependencies first. `urdFusionMain` is reloaded last because it imports the others. When adding a new module:

1. Add it to `from modules import ...` in `urdFusion.py`
2. Add `importlib.reload(...)` in `reloadModules()` — before `urdFusionMain` if it's a leaf module

## Fusion 360 API gotchas

### Event handlers must be retained

Fusion's event system uses weak references — handlers get garbage collected if nothing holds a strong reference. Each module that wires up handlers keeps a module-level `_handlers = []` list. Handlers are appended on registration and cleared in the command's destroy event (or in `_unregister`).

### `Occurrence.entityToken` only works on root proxies

`entityToken` raises `RuntimeError` on native sub-occurrences (e.g., the items in `someComponent.occurrences` when `someComponent` is not the root). It only works on root proxies — i.e., occurrences obtained from `rootComponent.allOccurrences` or from selection inputs.

To traverse the assembly when you need tokens, use `rootComponent.allOccurrences` (flat list of all root proxies) and `Occurrence.assemblyContext` to walk up the hierarchy. Do **not** recurse via `occ.component.occurrences` if you need to compare entity tokens — it returns native sub-occurrences.

### `CommandDefinition` is dual-use

The same `CommandDefinition` API powers both toolbar buttons and modal dialogs:

- Toolbar button: `panel.controls.addCommand(cmd_def)` — visible, persistent, user-triggered
- Modal dialog: `cmd_def.execute()` — fired programmatically, not added to any panel

The dialog's inputs are built in the `commandCreated` handler (`cmd.commandInputs.addSelectionInput(...)`, etc.).

### Material appearance color: use `ColorProperty`, not `AppearanceColorProperty`

To extract a flat color from a material appearance, cast each property to `adsk.core.ColorProperty` (not `adsk.core.AppearanceColorProperty` — that class exists in the API but `.cast()` always returns `None` in practice). The value is an `adsk.core.Color` with `.red/.green/.blue` in 0–255.

```python
color_prop = adsk.core.ColorProperty.cast(prop)
if color_prop:
    c = color_prop.value  # adsk.core.Color
    rgba = (c.red / 255.0, c.green / 255.0, c.blue / 255.0, 1.0)
```

### `print()` is unreliable

Output to Fusion's Text Commands panel is flaky. Use `ui.messageBox(...)` for anything you need to actually see. All exception handlers in the codebase route to `messageBox(traceback.format_exc())`.

## Style conventions

- camelCase for function names (`checkAllBodiesSelected`, `reloadModules`)
- snake_case for local variables (`selected_tokens`, `uncovered`)
- Helper functions and module-level state prefixed with `_`
- `ui` is module-level in `urdFusion.py`; passed to modules that need it

## Testing

Manual only. The add-in must be loaded into Fusion 360 to exercise. Workflow:

1. Edit code
2. Reload (toggle for entry point, button press for modules)
3. Verify behavior in Fusion 360 directly

There is no headless test harness — Fusion's API is only available when running inside Fusion.

## URDF link naming

`getUniqueLinkNames(components)` returns `{link_name: occurrence}` or `None` on any error. The occurrence values are the same object references that were passed in via `components`, so the dict makes the original list redundant once naming is resolved.

Names are sanitized via `_sanitizeName`:
1. Lowercased
2. Any character outside `[a-z0-9_]` replaced with `_`
3. Runs of `_` collapsed to one
4. Leading digits and underscores stripped
5. Trailing underscores stripped

This enforces the strict ROS convention: names must match `[a-z][a-z0-9_]*`. A component that produces an empty string after sanitization is a hard error — the user is told to rename it.

Duplicate detection runs on sanitized base names (the part before `:` in Fusion's `occurrence.name`). When the same base appears more than once, the raw suffix (the instance counter after `:`, e.g. `1`, `2`) is appended with `_`. If two components still collide after that, it's an error.

## Export pipeline

`urdFusionMain.execute` runs this sequence after the dialog:
1. `checkAllBodiesSelected` — validates coverage
2. `getUniqueLinkNames` — resolves sanitized link names
3. `getRootLinkName` — gets the sanitized design name for file naming
4. `selectExportFolder` — asks user for output directory once
5. `collectLinksData` — builds `URDFLink` list (material field left `None`)
6. `collectJointsData` — builds joint list and child visual origins
7. `populateMaterials` — fills `lnk.material` on each link and returns `[MaterialData]`
8. `exportCsv` → `<folder>/<robot_name>.csv`
9. `exportStls` → `<folder>/STL/<link_name>.stl` for each link (only if "Export STLs" checkbox is checked)
10. `exportUrdf` → `<folder>/<robot_name>.urdf`
11. "URDF export complete" message

## STL export

STLs are exported via `design.exportManager.createSTLExportOptions(occ.component, filename)`. Passing `occ.component` (not the occurrence) gives coordinates in the component's local frame, so the mesh origin matches the link origin. Settings: `MeshRefinementHigh`, binary format, `unitType = MeterDistanceUnits`, `sendToPrintUtility = False`.

`component.allOccurrences` is a flat list of all nested occurrences at every depth — no manual recursion needed when checking bodies across the whole hierarchy.

## Current roadmap position

Completed: Hello World scaffold → toolbar button → link selection dialog → validation → `getUniqueLinkNames` with ROS name sanitization → CSV export → STL export (meters, local frame, hidden-body warning) → URDF XML export with links and joints → "Export STLs" checkbox to skip slow STL export when not needed → material color assignment (material/rainbow/single-color modes) with URDF `<material>` elements.

Next: see README roadmap.

## Joint export

Joints use **Option B** placement: the URDF joint frame is at the Fusion joint geometry origin (the physical pivot/slide point in world space), and the child link frame adopts the child component's orientation. This means:

- `origin_rpy` = RPY of child component frame relative to parent component frame = `matToRPY(R_parent^T * R_child)`
- `origin_xyz` = joint geometry world position expressed in the **parent's URDF link frame** (not the parent component frame). The parent's URDF link frame origin is its own incoming joint's world position — not its component origin. `link_frame_world` is tracked through the BFS to accumulate these correctly.
- `axis` = joint axis expressed in child component frame = `R_child^T * axis_world`
- `vis_xyz` (visual/collision origin for the child link) = child component origin expressed in joint frame = `R_child^T * (child_component_origin - joint_world)`, converted to meters

Supported joint types: `fixed` (RigidJoint), `revolute` (RevoluteJoint, limits enabled), `continuous` (RevoluteJoint, no limits), `prismatic` (SliderJoint), `revolute` ignoring translation (CylindricalJoint). PinSlot, Planar, and Ball joints are skipped.

Joints are collected from all components (not just root level) because joints in sub-assemblies connect sub-component actuators to structural links. BFS from base_link token determines parent→child direction regardless of how Fusion ordered the joint's occurrenceOne/Two.

`_findContainingLinkToken` resolves a native occurrence (from `joint.occurrenceOne/Two`) to the selected link it belongs to by walking up `assemblyContext`. It tries `entityToken` first (works on root proxies), then falls back to `occ.name` lookup (works on native sub-occurrences).

`_getJointOriginWorld` returns the joint geometry origin in world coordinates (cm). For as-built joints it uses `joint.geometry.origin`; for regular joints it uses `joint.geometryOrOriginTwo.origin`, falling back to `geometryOrOriginOne.origin`, then the child component translation.

## Mirrored components

Fusion bakes the mirror into the component geometry — mirrored occurrences have det(R) = +1, indistinguishable from non-mirrored occurrences by transform alone. The STL exported via `occ.component` already contains the mirrored vertices. Mirrored components work without special handling.

## Physical properties and unit conversion

All Fusion API distances are in **cm**; mass is in **kg**; `getXYZMomentsOfInertia` returns **kg·cm²**. Convert to SI by multiplying lengths by `0.01` and inertia by `0.0001`.

`getXYZMomentsOfInertia` returns a tuple `(bool, xx, yy, zz, xy, yz, xz)` — note `yz` before `xz`, not alphabetical. Values are about the **component origin**, not the CoM. Apply the parallel axis theorem to shift to CoM before exporting:

```
Ixx_com = Ixx_origin - m*(y² + z²)   # diagonal: subtract
Ixy_com = Ixy_origin + m*(x*y)        # off-diagonal: add (because translation term is -x*y)
```

`component.physicalProperties.centerOfMass` returns the CoM in the component's local frame (relative to component origin), consistent with the inertia origin.

## Material colors

`urdfMaterials.py` assigns one material per link and emits `<material>` elements at the top of the URDF robot element, plus a `<material name="..."/>` reference inside each link's `<visual>`.

**`COLOR_MODE_MATERIAL`** — dominant physical material by accumulated body mass within the component hierarchy. Ties broken alphabetically by material name (deterministic). Color extracted via `material.appearance.appearanceProperties` looking for `AppearanceColorProperty`. Many Fusion materials use textures or complex appearances where this API returns nothing; in that case a deterministic palette color is used instead (`sum(ord(c) for c in material_name) % len(_COLORS)`), so different Fusion materials still get visually distinct colors.

**`COLOR_MODE_RAINBOW`** — BFS depth from `base_link` through joints. Base link gets palette index 0, depth-1 links get index 1, etc.; wraps with modulo when depth exceeds palette size.

**Single color** — all links get the chosen palette color name.

`populateMaterials` returns a deduplicated `[MaterialData]` list (only materials actually assigned to at least one link), which is passed into `exportUrdf` for the top-level definitions.

## Coordinate frames

Z-up is assumed in Fusion. The add-in does not currently transform coordinates. A future option will let users with Y-up models reorient ("keep up up" vs "keep Z up"), but for now everything is exported as-is.
