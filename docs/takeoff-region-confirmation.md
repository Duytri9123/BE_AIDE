# Confirm drawing regions before takeoff

The EL workspace now separates source discovery, confirmed takeoff and product CAD lookup.

1. A takeoff request with selected files first returns `requires_confirmation` and `detected_panels`. Each panel includes its source file, PDF page (when applicable), normalized region, position description and an overview with a red rectangle. Discovery does not persist devices.
2. The user selects panels and explicitly confirms. The client sends their signed `scope_token` values in `context.takeoff_scope`; tokens are bound to the project, file, page and region and expire after one hour. History is sent as role/content only, excluding preview images.
3. Extraction and verification are restricted to those panels. Rows preserve panel, tag/lane, location and source evidence. A panel-level fallback region is explicitly labelled as such; it is not an exact device position.
4. The result table's **Bảng giá & CAD** action searches the published price catalog and opens the existing product-row CAD detail. Exact SKU plus brand can open an unambiguous result automatically; otherwise the user selects a product. Missing product CAD is not synthesized from drawing labels.

Deploy the frontend and backend together: older clients do not submit confirmation tokens.

CAD source overviews include distant panels rather than an automatically chosen horizontal band. Rendering preserves the viewport and figure dimensions, and filters geometry outside it. A quoted native CT ratio cannot be silently rewritten in the returned specification.

Validation (from the backend directory, with its environment activated):

```powershell
python -m unittest discover -s tests -p 'test_*takeoff*.py'
python -m unittest discover -s tests -p 'test_cad_source_scope.py'
```

The live local test identified six panels in a real PDF, saved nothing before confirmation, rejected a modified token, and saved only the confirmed MDB-102 panel with positions and evidence. The existing price-row detail returned linked CAD without another DWG scan.

Whole-project TypeScript checking still has unrelated existing errors; the Vite production build and the touched Vue component compilation checks pass. Native Explorer-to-browser drag could not be verified because Computer Use could not establish the browser URL; handler-level tests cover file routing and bubbling separately.
