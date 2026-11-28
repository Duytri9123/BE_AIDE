# Device geometry and door interfaces — 2026-11-28

The audit reads all 2,285 source profiles (5,272 view entries), rather than relying
on the browser's published subset. The existing export contains 1,287 profiles.
257 variants have one front or wire-passage projection and one side projection
within the same variant, with positive millimetre dimensions and compatible heights.
These qualify for source silhouette previews. This does not certify the actual
manufacturer body, mounting datum, terminal clearance or electrical ordering code.

MSQ-60's source envelope is 102 × 128 × 74 mm. Its explicitly labelled wire-passage
projection contains a closed conductor window assembled from the original CAD
segments. The preview retains this aperture through the solid; it is not a panel
opening. The original DXF files and source profiles are unchanged.

The ABB A1 3P body, collar, operating face and lever use the previously reviewed
mechanical decomposition only when both source projection SHA256 values match.
No sibling frame inherits those dimensions. The library 3D dialog selects the
variant containing the currently displayed CAD view.

The cabinet inspector and saved layout report assess each part against the closed
inner and outer door planes: behind, ahead, touching, crossing, outside or unknown.
Clearance includes the mounting-plane offset, support height and sheet thickness.
For the MCCB lever, the side polygon is clipped to the door's thickness before
computing its section. A body/collar crossing indicates a mounting conflict;
an operator crossing requires a model-specific opening. Neither authorizes CNC.

There are currently zero verified model/variant-bound panel-cutout contracts.
Manufacturer dimensions and cutouts across the entire library remain unresolved.
ABB's [XT1 installation instructions](https://library.e.abb.com/public/17e4cc1584684134b8ec5e41883f131d/1SDH000719R0001.pdf)
distinguish configurations with and without a flange; those alternatives must not
be transferred to another MCCB or used as an overall-body opening.
Other manufacturers' MSQ-60 drawings cannot establish dimensions for Morele's model.

Refresh the qualification metadata after exporting CAD:

```powershell
venv/Scripts/python scripts/review_device_geometry.py --exported ../AIDE/packages/cad-viewer-example/public/device-blocks --report docs/device-geometry-review-2026-11-28.json --mechanical-library ../AIDE/tools/cabinet-demo/library.json
```

The full JSON report retains every source profile and its unresolved conditions.
Missing-depth source CAD remains 2D. Explicit draft blocks remain editable drafts.
