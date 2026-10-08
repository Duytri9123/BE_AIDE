# CatalogTB CAD and quotation deployment

Deploy app code together with data/CatalogTB from the managed installation. CAD profiles and manufacturer DXF files are deployment data, not bundled in this code change. Preserve profile-relative paths; asset IDs derive from these paths. The tracked JSON rule files in data/CatalogTB are required by the AI prompt builder.

Selected CAD assets must be explicitly provided in device.cad.asset_id. For the reviewed TĐT layout set device.cad.branch_arrangement=two_vertical_banks and distribution_method=fabricated_fishbone. Geometry is a review drawing, not a fabrication approval. The neutral bar is custom geometry alongside the main breaker and extends to the branch-bank bottom. Its layout length flows into cad_layout.material_rows and the quotation; section and price remain pending.

The source shell library needs data/CatalogTB/Form tủ/catalog.json and its referenced files. Missing or unreviewed shells must not become fabrication-approved drawings. The fallback produces a downloadable review DXF and a quotation draft.

Run: python -m unittest scripts.test_selection_knowledge scripts.test_catalogtb_layout scripts.test_takeoff_integrity scripts.test_circuit_review scripts.test_cad_layout_regressions.MultiPanelQuotationTests

CatalogTB integration tests require the deployed catalog dataset. Do not commit runtime .env, databases, uploads, or generated project files.
