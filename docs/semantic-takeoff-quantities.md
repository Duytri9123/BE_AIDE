# Schematic representations and material quantities

Takeoff keeps `drawing_quantity` separate from `procurement_quantity` and
`quantity` (the proposed physical material count). A grouped single-line symbol
can represent multiple lamps, CTs, fuses or repeated branches. A multipole breaker
is still one physical breaker.

The vision prompt requests the symbol classification, connected circuit,
quantity calculation and its source basis in `technical_analysis` and
`quantity_basis`. When engineering assumptions are needed, the proposal retains
them in `quantity_review.assumptions` with status `needs_review`.

Independent counting checks source coverage and panel boundaries. It does not
force material counts to equal symbol counts. Either an observed grouped count
or an expanded count can reconcile when the material count has retained circuit
reasoning. Remaining disagreements trigger bounded re-reading and review metadata,
not rejection of the entire readable page. Unreadable initial extraction still
fails rather than inventing an inventory.

`quantity_review` records the observed count, proposed count, group-level source
count, evidence and differences. Group counts are not per-device quantities.
Failed evidence verification clears unverified bounding boxes and retains a
review note. Matching counts alone do not certify recognition or fabrication.

The workspace shows both quantities and their basis in device details. Completed
results with pending interpretation use an amber review state. Progress events
describe the panel currently being read or reasoned about.

Each PDF panel also receives an independent identity/label read after counting.
It reads each breaker branch separately and retains literal source labels in
`source_observations`. Previous extracted ratings are not included in that
prompt. Parallel outgoing lines can be isolated into row strips; a separate
reading transcribes each strip, so a blank spare cannot inherit a neighboring
rating. Missing row tags or incomplete strip reads remain reviewable. A
separately counted component omitted from the new read is retained with a
review flag rather than silently removed. Source labels and material reasoning
remain separate from manufacturer/SKU selection.
