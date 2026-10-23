# ABB CAD import — 2026-10-20

Downloaded official supplier DXF sheets through the current ABB Library after checking ABB PARTcommunity/CADENAS, ABB US Empower, ABB Connect NL and ABB Turkey drawing references. TraceParts search did not yield a suitable Tmax XT source.

| Family | Supplier document | Extracted views |
| --- | --- | --- |
| XT1 | 1SDH000719R0100 | 3P front, 4P front, common side |
| XT2 | 1SDH000721R0100 | 3P front, 4P front, common side |
| XT3 | 1SDH000720R0100 | 3P front, 4P front, common side |
| XT4 | 1SDH000722R0100 | 3P front, 4P front, common side |

12 unique supplier projections are published as 16 views across the 8 existing 3P/4P profiles. Each uses the native supplier block geometry, with sheet insertion scale reversed to millimetres. Screw/detail inserts inside each block envelope are retained; text, dimension and callout groups are excluded. Original files and SHA-256 provenance are retained under data/CatalogTB/ABB/NguonBenNgoai.

The views describe fixed devices with front terminals, including accessories shown by the manufacturer drawing. They establish a reference geometry, not an approved order code or electrical rating. In, Icu/Ics, operating voltage, trip unit, mounting and terminal accessories must be selected separately. Side pairing now requires the same geometry variant.

Reproduce from the BE_AIDE directory:

```powershell
./venv/Scripts/python.exe scripts/update_abb_cad_configurations.py
./venv/Scripts/python.exe scripts/import_abb_official_faces.py
./venv/Scripts/python.exe scripts/publish_abb_official_faces.py
```

Publication adds only the ABB view entries to the existing equipment index. It preserves unrelated catalog records. CAD data is ignored by Git in this workspace; run these scripts when preparing another deployment.

Validation: 12 parsed DXFs pass ezdxf audit; 16 asset preview/download paths resolve; 8 front/side envelopes resolve in millimetres. Regression test covers independent fixed and withdrawable side variants.
