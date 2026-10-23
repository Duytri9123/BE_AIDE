# Library browsing and ABB CT update — 2026-10-20

The frontend now shares duplicate requests, caches metadata for 15 seconds and previews for 5 minutes within the current authentication session, limits library requests to three in flight, skips abandoned queued work, and pauses each request category according to HTTP Retry-After. Metadata is debounced during rapid device changes. The list preserves already loaded devices on a rate-limit error and explains that they are previous results.

The backend keeps a 120/minute quota for each of the preview and metadata categories instead of combining both into one per-user queue. Authentication, paid CAD-download entitlement and per-category rate limits remain enforced. Retry-After reflects the remaining sliding-window time.

ABB CT1M source packages: 12 official ABB Library ZIPs, containing supplier DWG and PDF. DWG conversion uses installed AutoCAD Core Console. Derived views preserve source geometry and carry package/source/derived SHA-256 evidence. Millimetre scale is derived from dimension geometry versus published dimension values; the original drawing headers alone do not establish its physical scale. Inconsistent source dimension annotations are retained in the evidence counts. Geometry is a reference, not an approved electrical variant.

Families: CT1M-2/3/4/5/6/7/8/10/12 and CT1M-S-30/80/120. Each has a wire-passage view, side view, top view and isometric view. Isometric views are for inspection, not automatic insertion. CT ratio, class and burden remain unselected at family level. The CT price matcher now rejects metering/ZCT substitutions and mismatched primary/secondary ratios.

Sources: ABB Library https://library.abb.com/ and ABB current transformer technical overview https://new.abb.com/low-voltage/cs/nizke-napeti/produkty/modularni-pristroje/merici-pristroje/proudove-transformatory .

Reproduce from BE_AIDE: run scripts/download_abb_ct_sources.py, scripts/convert_abb_ct_sources.py, scripts/import_abb_ct_faces.py and scripts/publish_abb_ct_index.py in that order using venv/Scripts/python.exe. CAD data is ignored by Git; retain source packages and profiles for deployment.

Validation outcome: 48 DXF audits and all preview/download paths passed. All 12 families are searchable by CT1M; model matching keeps CT1M-2 distinct from CT1M-20. Seven families have matching front/side reference envelopes. CT1M-2, CT1M-3, CT1M-5, CT1M-12 and CT1M-S-30 remain subject to mounting-variant review before automatic 3D sizing. Their reference projections stay available for visual review and downloading.
