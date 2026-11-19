# Takeoff processing corrections and command-line validation — 19 November 2026

The reported Anh Hao kitchen-panel failure combined different problems: the
inventory had readable ratings, but generic equipment categories prevented catalog
matching, source crops clipped the load column, and the UI described processing
failures as missing source evidence. A saved partial result was also presented as
a completed run.

## Changes

- Preserve source ratings separately from phase labels, measurement markings,
  circuit functions, crop diagnostics and engineering assumptions. Saving a lamp
  must not manufacture a rating or erase its analysis.
- Bind horizontal CAD rows to native label identities; propose complete symbol,
  rating, tag and load crops from native geometry. Independent pixel checking is
  still required. Vertical mechanical-linkage seeds are preserved.
- Keep all columns of a circuit-table band, including photographed/rotated
  schedules. Merge duplicate observations only when equipment claims and source
  geometry support the same identity; repeated spare tags alone are insufficient.
- Compact whole-source coverage requests, retaining source facts rather than
  repeated diagnostics. One recorded prompt shrank from 39,499 to 18,958 characters;
  this is a payload measurement, not a runtime guarantee.
- When coverage already identifies missing/duplicate equipment, defer detailed
  crop auditing. Repair the inventory first instead of spending a complete crop
  audit/recovery cycle on a known invalid list.
- Recover missing image locations in bounded groups with stable row IDs, correct
  coordinate transforms and sufficient context for distant tags and loads.
- Reread empty PDF discovery pages once and explicitly report unresolved pages.
- Catalog proposals distinguish 1P+N from 2P and phase count from pole count;
  match fuse currents and residual-current ratings. A 30 mA source must not receive
  100/300 mA proposals as matching variants.
- Retry interrupted transport reads once using the same configured model and
  request ID, within the total configured wall-time deadline. Cancellation stops
  stalled requests; the read timeout is no longer treated as a total deadline.
- Saved results with unresolved processing return `saved_needs_review`. The
  frontend keeps their result link while reporting an incomplete run.
- A failed provider call in a crop-audit batch retains successful checks from
  other batches. Provider interruptions are identified as unfinished processing;
  they do not trigger another source-location recovery cycle. Recovery outages
  also retain previously checked rows and stop further attempts.
- Region reading and inventory review retain successfully read regions after a
  provider outage and mark coverage unresolved. A failed provider call must not
  discard sibling regions or be described as a missing label on the drawing.

## Validation and limitations

An isolated export of the staged backend passed 136 tests. This includes native
symbol extents, coordinate transforms, source-identity deduplication, equipment
category/rating normalization, catalog filtering, PDF page coverage, bounded
recovery, failed-coverage deferral, transport retry, cancellation and partial-batch
provider failure and partial-region retention tests. Frontend type checking, production build and focused
device presentation, evidence, saved-review response and worker-summary checks
also passed. Vite reports a bundle-size advisory.

Earlier live UI validation of Anh Hao TĐ-BEP produced 21 rows with all source
image checks and the independent inventory review passing in 116.556 seconds.
That measurement precedes the subsequent corrections and is not a final-version
performance claim.

Photographed mist-panel PDF trials exposed unresolved omissions, duplicated rows,
shared 220/24 V supply ratings and load relationships. A 286.1-second trial checked
31 symbol crops but still failed inventory coverage and two load relationships;
it is explicitly not a successful extraction. Another trial was stopped when its
coverage review identified 56 rows with duplicates and a missing nine-button
group. A later command-line retry encountered provider transport failure before
returning a complete list. No perfect autonomous PDF extraction is claimed.

A final native Anh Hao retry reached independent image auditing for 21 rows,
but one provider request hit its 60-second deadline and aborted that run. This
exposed the partial-batch failure corrected above. It does not establish a
successful final extraction or a final runtime improvement.
The following cold retry hit the 60-second deadline in one region while three
other region reads completed in 30.2, 30.7 and 40.4 seconds. Region-retention
handling was added in response, with independent regression coverage.
The final retry with region retention returned four pending source rows in 66.0
seconds after other provider calls timed out. It retained the readable region
instead of throwing away the whole extraction. This validates failure retention,
not inventory completeness: zero rows completed independent crop verification.
The deferred status now explicitly attributes this case to unfinished Agent
processing following provider interruption.

The final work proceeds through command-line tests and live provider calls at the
user's request. Browser control became unavailable; HTTP 200 health responses do
not establish UI correctness. Raw source files, provider credentials, databases,
trace payloads and source images are kept out of the commit.
