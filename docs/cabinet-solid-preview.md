# Source-based solid cabinet previews

The cabinet form dialog defaults to **3D liền khối**. Users can orbit and zoom,
open each available door layer, compare the source CAD lines, or switch to the
existing 2D source viewer. This does not rewrite library DXFs or change DXF export.

## Data and access

`GET /api/v1/analyze/cabinet-templates/{template_id}/preview-3d` requires an active
user. The same handler is available under the existing library-access router at
`/api/v1/cabinet-templates/{template_id}/preview-3d`.

Omit dimensions for the original source size, or supply all three `height`,
`width`, `depth` query parameters. Resize validation and movement use the existing
CAD stretch bands, 75–125% bounds, rigid hardware offsets, and centered-lock rules.
The dialog updates 3D dimensions after **Áp dụng**, alongside the existing CAD
preview. Requests are cancelled on template changes/unmount; superseded results
cannot replace the selected model. GPU resources are disposed when leaving 3D.

Geometry is extracted from the selected template's cleaned DXF. Closed source
outlines, nested leaf contours and named hardware are retained. Curves are flattened
with 0.1 mm tolerance. Original handles, group names and unassigned/unsupported
counts are included for review. Cached results are invalidated by the source,
catalog and resize-profile modification times.

## Geometry limits

These are visual review models, not manufacturing solids or mechanical clearance
certificates. Sheet thickness comes from the catalog (a flagged 1.5 mm fallback
is available for future entries). Nominal closing panels join the enclosure.
Hardware projection depth, door returns, internal offsets and side handedness
require mechanical verification. The two-dimensional footprints of
hardware remain source-based; their depth is provisional.

Schema 2 includes `assembly.roof`, `assembly.base` and `assembly.top_placements`.
Roof and base dimensions come from closed source side profiles, including curves
whose endpoint is closed even when the original DXF polyline flag is false. A
sloping roof contributes to overall height and is not added to the plinth height.
The cap is a hollow folded sheet, and the base uses separate walls rather than a
solid block. Source base inspection-cover contours are retained. Partial-width
removable top covers are positioned by matching vertical bays; separate top frame
pieces can establish the second bay's boundary without cloning its neighbour.
Alternative full-width equipment projections do not become extra physical bays.

Schema 3 also records `panel_layout`, `compartments`, `lifting_eyes`,
`mounting_lugs`, `door_perimeter_details` and `review_issues`. Adjacent source
plates whose widths sum to the enclosure width establish separate horizontal
bays. Stacked source panels retain their vertical origins. Same-size reference
views do not automatically establish another physical bay; ambiguous arrangements
remain flagged. Two door layers alone do not imply two compartments.

Named Lifting Front/Side/Top projections are associated with physical roof eyes.
Connected source arcs and lines recover the outside silhouette; the hole contour,
stem diameter and eye thickness remain source-derived. TOP can establish four
physical eyes despite overlapping pairs in FRONT. Physical roof eyes stay on the
shell when doors open. Wall mounting tabs are separate parts, instantiated once
from one source view. TOP/SIDE disagreements are not silently reconciled: TOP
positions are displayed with a review warning and the measured discrepancy.

Inset outer-door perimeter details remain attached to that leaf's inner face,
not counted as another door, mounting plate or compartment. FRONT geometry alone
does not establish whether they are stiffeners or folded returns, nor their
section depth. The source footprint is retained with `section_verified: false`.

Regression checks: `python -m unittest scripts.test_cabinet_topology -v`.
The current local audit covers 108 native models, 66 physical lifting eyes,
280 wall mounting tabs and two source cabinets with two 900 mm bays. Two sources
retain TOP/SIDE lifting-position conflicts; four retain same-width reference
plate projections which are not taken as additional bays.

For example, source 108CDD4 has a 1465 mm body, 35 mm roof rise and 100 mm base,
totalling 1600 mm. Source 1120763 has a 1900 mm body, 100 mm base and separate top
cover placements for its two 900 mm bays. These are source drawing dimensions,
not an independent mechanical approval. Original library JSON/DXF files are read
without modification.

Repeated hardware projections create one physical lug set. Duplicate TOP views
do not create a second roof or get silently relabeled as a bottom. Small details
retain CAD comparison lines, with closed recognizable footprints rendered as
meshes. Source drawings remain available for details not assigned to a solid face.
Multiple indexed bays are kept distinct. Missing door outlines and title/source
dimension mismatches are disclosed in the viewer.

## Validation

From `BE_AIDE`:

```powershell
python scripts/check_cabinet_3d.py --output ../reports/cabinet-3d-validation
```

The check covers every library entry, rejects invalid sizes/unknown templates,
checks finite geometry and group references, and resizes supported sources while
verifying that named hardware retains its dimensions. The 2026-11-15 audit passed
108 native models and 96 resized models; 39 sources have body/title dimension
differences and two lack a front-door outline. All 108 models were rendered in
browser QA, including available door openings and resource disposal. The Vue
preview was also checked for rapid template changes, mobile overflow and unmount.
# Local equipment mounting trial (2026-11-16)

The earlier 52 × 72 mm trial window and automatic support offset have been removed
after the user's visual review. Those earlier screenshots and `cutout-tests.json`
are historical evidence only. The current renderer refuses a cutout unless the
device carries a model/variant-bound `verified_installation.panel_cutout` contract.
There is no rectangular/front-bbox fallback. A contract must include finite simple
polygon points in mm, operation origin relative to the source front, a source
reference and an existing source artifact with a matching SHA256. The renderer also
checks the selected model/variant, source identity fields, door containment and
window overlap. Windows belong to the moving inner leaf; the body stays inside.
No depth offset is inferred from the outer envelope. Manual support offsets remain
review-only, and door sweep, frame conflicts, real operation and strength are unverified.

`scripts/audit_device_installation.py` reads all current profiles recursively,
independent of old index snapshots. The current audit covers 2,077 profiles / 4,973
CAD entries, including 27 profiles with possible cutout labels. None has the complete
verified model-bound cutout contract; this does not mean every device needs a cutout.
It means no automatic hole can be justified by this audit. Source profiles/DXFs are
unchanged. The live local page includes searchable installation review rows for all
profiles, with unresolved/reference families kept explicit.

Installation review metadata is attached to CAD assets, automatic selections,
equipment records and browser metadata. Internal device bodies cannot be assigned
to a door by an operator-face label. MCCB current no longer implies a DIN adapter.
Panel-device categories require the project's owner face instead of defaulting to
the outer door; an explicit internal mounting-plate face is respected.

Validation: `venv/Scripts/python -m unittest scripts.test_device_installation -q`,
strict renderer TypeScript check, and `scratch/check_installation_policy.cjs`.
The browser check covers all 108 cabinets, no unverified holes/default offsets,
rejection of stale cutout requests and searchable whole-library coverage. Current
screenshots and results are `installation-policy-*` in the review report directory.

The standalone local viewer supports 1–6 copies of the library ABB XT1 3P fixed-F
supplier projection, mounted to an identified equipment plate, including selection
between the two physical plates in the multi-bay samples. X/Y offsets and inter-device
gap are editable; the CB stays on the plate when doors open. No CB body is attached to a door.

`scratch/build_equipment_trial.py` checks both source DXF hashes against the stored
unit verification and extracts the original front and side curves without modifying
the library. The blue translucent envelope is 78.3 × 180.6092 × 109.1677 mm, including
source protrusions; it is not a reconstructed supplier solid or an exact electrical
variant. Projection origins are normalized to their own bounds, not verified mounting datums.

The trial checks device envelope corners against the plate contour, pair overlap for
the horizontal row, and nominal front envelope distance to the closed inner-door plane
(outer plane when no inner leaf exists). This does not verify the swept door volume,
source hardware, stiffeners, mounting holes, rear mounting datum, terminal clearance,
or installation suitability. `release_ready=false` and missing evidence are retained
in local `equipment.json`. Existing perimeter candidates remain unverified.

Validation: isolated renderer strict TypeScript check passed. Browser trial rendered
all 108 templates without page errors, exercised plate overflow, pair overlap,
remove/re-add, door closing, and second-bay selection. Evidence is under
`reports/cabinet-3d-20261115/topology-review-final/equipment-*`.

