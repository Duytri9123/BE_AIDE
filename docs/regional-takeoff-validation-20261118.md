# Regional takeoff validation — 18 November 2026

Confirmed-panel extraction now discovers up to six image regions before reading them, with at most two concurrent region reads per request. Each crop keeps its actual pixel bounds and quarter-turn transform; evidence coordinates are mapped back to the selected panel image before auditing. The independent coverage review checks omitted controls and real quantity discrepancies. At most two flagged regions are reread. Unresolved results remain visible with a review status.

No local OCR model is loaded by default. The legacy image pipeline can opt in with `AI_LOCAL_OCR_ENABLED=true`. This is a per-request concurrency bound, not a measured system-wide throughput guarantee. Vision HTTP calls and Celery generation tasks retain their existing unlimited generation timeout.

## Evidence and commercial behavior

- Repeated tags at distinct source positions remain separate. Overlapping region observations require matching source specifications, quantity and symbol geometry before deduplication.
- A shared rating header has separate exported evidence and requires an independent branch/group relationship check. Reused text coordinates trigger this check even if the extraction omitted the shared-header flag.
- A rejected location retains candidate coordinates and the rejection reason without displaying it as verified evidence or removing the device row.
- Source interfaces, functional blocks, installation notes, enclosure/cable/busbar information remain notes in this equipment-only extraction scope. Unknown quantities and unresolved coverage cannot produce confirmed priced totals.
- DOL assemblies retain their own load and upstream breaker candidate. A shared load alone does not verify the wire relationship. Contactor, overload protection and control operators are functional proposals, with missing motor/control inputs shown. They do not create separately priced component rows or duplicate the upstream breaker. Assembly units remain `Bộ`.
- Provider values such as `25A`, `6kA` and `2P` are normalized before schema validation; original strings remain in source observations. A live run exposed this failure before the regression fix.

## Live samples

These are individual local measurements using the configured Vision connection, not latency guarantees. Source DWG/PDF files were not uploaded to Git or modified. Raw responses, images and timing logs remain in the local workspace reports.

| Sample / measured phase | Wall time | Vision calls | Result |
| --- | ---: | ---: | --- |
| Fresh JOSEON test harness, including native preparation and additional checks | 182.535 s | 10 | Completed; review items retained |
| Production regional helper, JOSEON MDB schematic | 195.360 s | 7 | 42 observations; 31 breaker-symbol observations (30 outgoing anchors + 1 incoming), two DOL assemblies, separate contactor and timer |
| Production regional helper, photographed mist-panel PDF page 1 | 233.311 s | 9 | Six DC power supplies retained; review still flagged button-note interpretation and a control functional block |
| Independent exported-crop audit of JOSEON controls | 15.781 s | 2 | Both DOL assemblies, contactor and timer passed: 4/4 |
| Additional P19/P20 audit with native CAD candidates, source close-ups and labeled evidence parts | 33.727 s | 1 | Neither position passed; both remain unverified |

The regional-helper times exclude per-device crop auditing, web upload, production queueing, database persistence, catalog selection and pricing. The first harness measurement also excludes the production web/quotation workflow. They are different procedures and must not be compared as a performance improvement claim. An earlier timing attempt failed during rendering and is excluded from successful timings.

The mist source visibly says `9 NÚT ẤN` while six pump branches are shown. The whole-page reviewer incorrectly proposed reading that note as six. The implementation retains original observations and review state, and its prompts now explicitly prioritize written source quantities over inferred branch counts. It does not silently apply that review as a source correction. Subsequent regression guards also exclude an enclosure row that a reread had incorrectly added to the equipment scope. This sample does not establish perfect autonomous extraction accuracy.

P19/P20 require further source interpretation: the crop reviewer considers the two drawn glyphs mechanically linked parts of one RCBO, while region extraction returned separate device rows. Native INSERT counts prove source anchors, not the number of independently purchasable devices. The 31-observation count above must therefore not be presented as a verified physical breaker quantity. Both rows and rejected candidate regions remain available for review; their crop status was not forced to pass. Audit sheets now separate the local source-symbol view from distant load/wire context, and label exported context parts so repeated views are not counted as extra devices.

## Checks

- 73 backend unit/async tests passed against an isolated copy of repository HEAD plus only the proposed changes. Concurrent endpoint/catalog workspace changes were excluded.
- Regression coverage includes rotation/crop coordinate transforms, quantity recovery, shared headers, overlap deduplication, retained rejected coordinates, DOL upstream candidates/verified relationships, missing sizing inputs, assembly units and pending quotation quantities.
- Frontend source-presentation and device-evidence regression scripts passed.
- Production frontend build passed. The full build also prerendered 16 public pages; the article API returned HTTP 502 and the existing bundled-article fallback completed successfully.
- A browser-mounted `DeviceReview` fixture displayed the DOL load, upstream breaker, missing motor/control information, proposed components and coverage warning without page errors.

No concurrent-user load test, complete production quotation timing or full-floor-plan takeoff is claimed. Remaining ambiguous source interpretations are review items, not verified procurement facts.
