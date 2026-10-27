# Design costs and the commercial quotation

Assembly requirements (rail, duct, terminals, wire, labels, PE/N and fixings)
remain in the design BOM. The commercial quotation groups fabrication into
enclosure, busbar, auxiliary materials and assembly labor. It does not append
the design checklist or technical proposals.

For the local Windows calculator, install Microsoft Excel and place the supplied
`Bao gia v6.0 - 2021.xlsm` at `storage/cost_templates/` relative to the backend.
The private workbook is excluded from Git. The service opens it read-only with
macros and external-link updates disabled, fills VT/Busbar inputs in memory,
recalculates using Excel, reads the totals, and closes without saving.

`POST /api/v1/export/design-cost` accepts actual enclosure dimensions and/or up
to 40 copper segment groups. Segment dimensions are millimeters and quantities
are integers. An omitted segment list leaves copper unpriced; an explicit empty
list means the design uses no copper bars. Rates per kg may be supplied or use
the workbook rates. Missing dimensions never fall back to the sample enclosure.
The response includes input values, source SHA-256, masses and calculator totals.
With a project-owned iteration ID, enclosure/busbar package prices are saved
for that panel. Other fabrication prices remain unpriced until supplied.

The workspace exposes these inputs under Design. Customer-entered manufacturer
discounts live beside the quotation and pass through to Excel export; the
default is zero. No CHINT discount is inferred from reference screenshots.

If Excel or the workbook is unavailable, the calculator returns an unavailable
status. It never substitutes cached workbook prices or guessed design costs.
