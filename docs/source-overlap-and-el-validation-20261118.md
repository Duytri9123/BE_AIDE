# Source overlap, linked annotations and EL validation — 18 November 2026

This continues `regional-takeoff-validation-20261118.md`. Its earlier P19/P20 rejection is historical, rather than the final interpretation below.

## Source interpretation and evidence

- JOSEON MDB: the horizontal arrow is a common-rating annotation. The same convention spans six and ten separate branches elsewhere in the source, exceeding the label's two-pole count. Native CAD geometry identifies comparison groups; an independent image check determines the relationship. P19 and P20 each remain one RCBO, and both exported positions passed independent crop checks. A collapsed multi-load row is split only provisionally until the independent relationship check agrees. A genuine mechanical group still requires explicit visual evidence and matching pole count.
- DOL remains a starter assembly even if an extraction labels it a functional block. It retains its own upstream breaker/load context. Motor current, power, supply/control voltage and overload sizing cannot be inferred from the upstream breaker rating. Proposed internal components do not create additional priced rows.
- Both photographed mist-panel pages retain the written `9 NÚT ẤN` note; a branch count does not replace the written number. A focused image check must confirm the actual disputed field, so a matching rating cannot clear a quantity dispute. MDK/MĐK is recorded as a verified functional note, without asserting an independently purchased controller. Repeated installation notes on different pages are not automatically additive material quantities.
- Source positions, symbols and text may overlap. Crops retain the target's own ink instead of being clipped at neighboring boxes. A crop can pass with neighboring/shared text when the reviewer confirms its identity, complete symbol/label and required tag/wire relationship. Explicitly ambiguous identity fails. Geometric overlap alone does not merge unnamed equipment rows.
- A rejected location keeps the read device, candidate coordinates and reasons. EL returns those rows for review instead of hiding them. Verified source notes are visible in the device review UI.

## Completed source-level checks

Original DWG/PDF bytes were unchanged. Fresh production rendering covered the confirmed JOSEON MDB region and both mist PDF pages. The inventory/coverage runs and subsequent focused corrections used real configured Vision requests. Successful intermediate work was resumed after provider failures using exact request/source-pixel matches; their accumulated wall times are not all-fresh benchmarks.

| Source | Inventory rows | Targeted exported positions checked |
| --- | ---: | --- |
| JOSEON MDB | 42 | P19/P20 2/2; DOL ×2, contactor and timer 4/4 |
| Mist panel page 1 | 37 | 9/9 after one timer-location recovery |
| Mist panel page 2 | 21 | 8/8 after two contactor-location recoveries |

These are 23 targeted positions, not independent crop approval of every inventory row. Rechecking page 2's saved duplicate-note warning against its actual device and note observations classified that one warning as a repeated reference: 1/1. The guard requires the warning to identify the exact nonmaterial text already represented by an equipment row. It cannot clear a material duplicate or an unrelated note. Live EL validation is reported separately.

## Speed changes and safeguards

- Crop review batches up to three devices, with at most two concurrent batches per extraction operation. This does not establish a system-wide concurrent-user capacity.
- Recovery first inspects an expanded local region when existing source anchors are usable, maps the returned coordinates back, and falls back to the full source if necessary. Failed recovery retains existing anchors. Identical failed full-source requests are not repeated.
- Positive crop checkpoints require the same source pixels, claims, proposed geometry, project/model scope and evidence-rule revision. Failed or incomplete checks are not cached as successes.
- Candidate-cache keys include file content, selected region/page/panel, request, model scope, prompt and extraction-rule revision. Real database UUID identities are supported.
- EL can reuse completed independent coverage and crop checks within the same server operation, rather than adding another whole-panel model pass. Reuse requires a server-owned Python proof, all selected scopes and exact claim multisets, complete evidence, successful coverage, and unchanged source bytes. Dropped/changed rows, changed files/regions and client-supplied JSON cannot authorize reuse.
- Native CAD context is reused within extraction. Generation requests retain unlimited HTTP time; reducing latency must not truncate extraction or silently change the selected model.

## Validation

The isolated backend snapshot passed 106 tests and contains only the proposed takeoff changes over repository HEAD, including the selected EL endpoint hunks. Regression tests cover source disputes, coordinate transforms/recovery, overlapping symbols, native group interpretation, retained review rows, cache UUIDs, proof invalidation, client proof rejection and joining failed parallel checks before deleting temporary images. Frontend presentation/evidence scripts, a production build and a browser-mounted source-note fixture were also checked. Raw sources, AI responses, report images and the isolated database remain local and are not committed.

Actual authenticated EL HTTP measurements use a minimal isolated SQLite database, signed confirmed scopes, the configured provider and the real save/review path. Import/startup, browser upload, production proxy/queue time and catalog pricing are outside these local HTTP measurements. Failed provider/timeout attempts are retained separately and never counted as successful processing.
