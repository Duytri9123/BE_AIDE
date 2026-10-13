# Manufacturer discovery and category evidence

The takeoff product search uses `app/services/ai/manufacturer_registry.py`.
The registry was reviewed on 2026-10-13. It contains category evidence for 23
manufacturers and 35 product groups. The supplied Vietnamese brand article is
only a discovery source; names from that article do not imply category coverage.

Each verified category records its official product/category/catalogue URL and
review date. A category not recorded for a manufacturer is **unknown**, never
proof that the manufacturer does not sell that product. Product availability in
Vietnam and suitability for a particular circuit still require model-level web
research and technical comparison. The registry does not approve SKUs or assign
market segments/prices to entire brands.

Search routing distinguishes on-delay, off-delay, cyclic, star-delta and calendar
timers from pump alternating relays. For example Finder 72.42 and Carlo Gavazzi's
pump alternating category are discovery anchors for pump alternation; a generic
delay or twin timer is not automatically a replacement. For voltmeters/ammeters,
search includes confirmed meter makers plus the specific measurement category.

To maintain the registry, inspect official category pages or catalogues, add only
the categories explicitly supported by those sources, and record subtype evidence
before adding a maker to `TIMER_FUNCTIONS`. Keep unrelated categories unknown.
Do not replace model-level specification checks with manufacturer coverage.

Behavioural regressions are in `tests/test_manufacturer_registry.py`.

Native source-image grounding uses RapidOCR/ONNX Runtime; both dependency files
include the tested runtime. RapidOCR also depends on OpenCV. Linux installations
using the full OpenCV wheel need its system libraries (`libGL` and `libglib`);
the Windows localhost verification used the existing headless OpenCV runtime.
