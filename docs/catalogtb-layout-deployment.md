# CatalogTB CAD and quotation deployment

Deploy app code together with data/CatalogTB from the managed installation. CAD profiles and manufacturer DXF files are deployment data, not bundled in this code change. Preserve profile-relative paths; asset IDs derive from these paths. The tracked JSON rule files in data/CatalogTB are required by the AI prompt builder.

Selected CAD assets must be explicitly provided in device.cad.asset_id. For the reviewed TĐT layout set device.cad.branch_arrangement=two_vertical_banks and distribution_method=fabricated_fishbone. Geometry is a review drawing, not a fabrication approval. The user-requested neutral bar is custom geometry immediately right of the main breaker, extending 20 mm above/below its envelope for review, without descending along the branch banks. Its layout length flows into cad_layout.material_rows and the quotation; width, section, terminals, supports and price remain pending.

The source shell library needs data/CatalogTB/Form tủ/catalog.json and its referenced files. Missing or unreviewed shells must not become fabrication-approved drawings. The fallback produces a downloadable review DXF and a quotation draft.

Run: python -m unittest scripts.test_selection_knowledge scripts.test_catalogtb_layout scripts.test_takeoff_integrity scripts.test_circuit_review scripts.test_cad_layout_regressions.MultiPanelQuotationTests

CatalogTB integration tests require the deployed catalog dataset. Do not commit runtime .env, databases, uploads, or generated project files.

## Published device information (2026-10-16)

`app/data/catalogtb_published_information.json` now ships the price-free information tables with BE code. The browser and AI reference search apply this information to the matching profile-relative paths in the managed CAD installation. It includes manufacturer web references and library classification; it cannot change source manufacturer, CAD geometry, electrical facts or insertion approval. Missing prices and unresolved ordering codes do not suppress information tables.

After editing source profiles, regenerate with `python -m scripts.complete_catalog_references`, then `python -m scripts.export_published_catalog_information`. Regenerate the browser display snapshot after exporting, and run the catalog tests. The complete CAD dataset must still be present in the installation; this information bundle does not supply DXF/SVG files for a server that lacks them. Restart backend workers after deployment and publish the new FE build to replace the old price-dependent library page.
