# Device price books

The customer page `/device-catalog` is labelled **Bảng giá**. Software
subscriptions at `/pricing` are labelled **Gói dịch vụ**.

## Identity and provenance

`item_name` (Tên hàng) identifies a model inside its manufacturer. A model can
have multiple rated-current ranges, voltages, prices and source offers.
`model_key` combines manufacturer and item name; variant `id` values identify
individual source rows and must not replace the model identity or collapse
different configurations.

Price books are independent of the equipment/CAD library. The catalog endpoint
does not import the library's internal prices into the price-book page.
`equipment_catalog_id` is nullable on each price row. Explicit reviewed links
in `app/data/pricebook_library_links.json` implement one library device to many
price rows; a price row can reference only one device. Publish links only after
the complete data review, with exact model/configuration evidence. A family CAD
match or similar name alone is insufficient. `pricebook_library_links.py` validates
the references and returns the existing complete library record to future drawing
consumers. No automatic linking or drawing-library import occurs during ingestion.

The user-supplied `catalog_data.json` has 1,498 technical reference rows. Run
`scripts/import_catalog_reference.py <JSON path>` to stage them separately in
`app/data/catalog_reference_candidates.json`. These retain dimensions, electrical
ratings and mounting information but do not publish the unprovenanced `g` price,
create library devices or mark dimensions ready for drawing. Even `_verified`
requires manufacturer evidence before approval. After review, use available CAD
from the linked library record; without CAD, drawing must use verified dimension
and mounting specifications. Missing dimensions must not be guessed.

The read-only API returns public commercial information, never the editor's
email or filesystem paths. PDF price-list amounts, seller prices and admin
prices retain separate source labels. Unknown VAT and effective dates remain
unknown; a document's posting/update date is not an effective date.

Customer API responses now use `customer_catalog_page` as an explicit allowlist.
Supplier URLs, labels, document lists, source pages, provenance notes and internal
library associations remain server-side. Public row/book identifiers are opaque.
Source PDF downloads require an administrator, even if the customer knows a URL.
The customer UI exposes neither source links nor PDF/document controls.

The customer's revised cabinet-equipment scope is exactly the 32 makers in
`customer_manufacturers.py`. This overrides the earlier broad discovery list
for the price-book browser. Documents, historical supplier rows, web offers and
admin prices cannot add another maker back into the public dropdown or results.
Historical source records remain internal. Membership is not approval of a SKU,
price, country, certificate or marketing quality claim. Requested manufacturers
without verified prices stay visible with zero price rows. Aliases collapse
Idec Izumi/IDEC, Mitsubishi, EPCOS/TDK and the other supplied names into one identity.

The price-book browser now follows the library's three-panel navigation:
manufacturer/category scope, model list, then prices and specifications. All
device rows remain visible as one grouped table until a specific model is chosen.
Selecting a model reads all returned configurations for its exact model key.
Changing scope clears the selected model; stale detail responses cannot overwrite
another selection. Customer manufacturer dropdowns and top brand tabs are removed.

Additional source reviews cover all 32 requested manufacturers, with findings in
the INTERNAL `app/data/catalog_coverage_review.json`. This is not sent to customers.
`scripts/discover_scoped_pricebooks.py` finds observed links in seven supplier
indexes; `scripts/review_catalog_sources.py` checks an external candidate for each
manufacturer. Fetched documents are candidates, not approved price rows. Quotation-
only products, unsupported currencies, historical editions and ambiguous supplier
identities remain pending; complete market-wide coverage is explicitly false.

`scripts/import_mitsubishi_pricebook.py` imports 3,026 explicit model/material/
numeric-price rows from the June-2026 workbook's 21 sheets. All numeric prices are
kept, including repeated model names with distinct material/configuration rows.
MCB India says "Please contact"; MV Relays has no price column: neither is assigned
a price. The posting date does not establish an effective date; VAT stays unknown.
The stored headers include rated current, poles and local Icu/voltage conditions,
without arbitrary forward-fill of row specifications.

`scripts/refresh_additional_seller_prices.py` reads eight observed Etinco collection
pages. It imports explicit SKU-before-pipe product titles and one live VND amount,
excluding crossed prices, ranges and "Liên hệ". The initial snapshot has 108 priced
rows in five manufacturers; other fetched collections have no eligible price row.
The original bounded seller importer also checks the observed Yaskawa collection.
These are partial seller snapshots, not manufacturer-wide price books. Dimensions
and CAD associations are not inferred from selling prices or a similar name.

The portfolio registry has 31 manufacturers with category evidence as of
2026-10-13, including newly reviewed TECO, WAGO, Delta, Socomec, Crouzet,
Littelfuse, Rittal and Samwha. Discovered names are not equivalent to verified
categories or available price rows. No prices are fabricated for these makers.

Run `scripts/enrich_verified_pricebook_specs.py` after reimporting a price book.
It classifies only established LS Metasol/Susol model families into standard/
premium lines, preserving LS Electric as the manufacturer. Unknown LS families
remain unclassified. The CHINT European March-2026 drawing was visually reviewed
for NXB-63 C-curve 6kA variants: 36 price rows receive verified nominal envelope
dimensions, installation and electrical details. NXB-63H/10kA and other similar
names are excluded. Dimensions alone do not establish a library CAD association.
The Metasol technical manual's pages 8–9 also verify 22 exact LS c-series rows.
The displayed overall depth includes the handle envelope (dimension d); body
and casing depths c1/c2 are kept separate so drawing consumers do not confuse
installation clearance with the body dimensions in the unverified reference JSON.
Internal evidence URLs are retained in the raw dataset and excluded from customer
responses. Price freshness means the latest dated revision actually checked,
not an assertion that every manufacturer has a complete current price book.
LA63N is assigned to the customer's standard segment; LA63H/LA63L to the premium
segment, after cross-checking their actual model/rating combinations against the
external April-2026 LS book. These L-series labels are not called Metasol/Susol.
Prices retain the later effective October-2026 revision already imported; an
older April price is not allowed to replace a newer October price.

## Sources checked on 2026-10-13

- User-supplied LS price book, effective 2026-10-01: 517 price rows across all
  eight pages. Prices exclude VAT. Each page's imported price multiset was
  checked against the original PDF.
- CHINT 2026 price book from the DGP article's public Drive link: explicit
  model/material-code/VND-price sequences, with source page and VAT status.
  `-` material codes are retained for models whose source does not provide one.
  Native PDF header/row geometry adds poles, rated current and breaking capacity;
  packing quantity (SL/Thùng) is intentionally excluded from customer columns.
- Hyundai book hosted by Điện Sài Gòn, effective 2026-04-20: 79 protection-device
  rows from the five-column tables on pages 2, 3 and 6 of 11. This is partial
  coverage, not the entire manufacturer's book. VAT is excluded. Merged cells
  are resolved only through actual source cell boundaries, never by arbitrary
  forward-filling. Import with `scripts/import_hyundai_pricebook.py <PDF path>`.
- Seller offers from Cơ Điện Hải Âu: exact product pages, VND only, current sale
  price rather than crossed-out original price. Ranges are not single prices.
- DGP's 152 source documents were discovered through its five pagination links.
  Older documents remain references. The inspected ABB PDF contains switches
  and sockets; the Hager PDF largely contains image pages and is not asserted
  to have verified product prices.

## Refresh and import

Run `scripts/refresh_web_catalog.py` to update the bounded seller source set.
Failed sources keep their previous offers and original check dates. The script
atomically replaces `app/data/web_catalog_offers.json` only after successful
reads. It does not affect automatic takeoff price resolution.

Run `scripts/import_ls_pricebook.py <PDF path>` or
`scripts/import_chint_pricebook.py <PDF path>` for the respective validated
layouts. These are layout-specific importers, not a universal PDF parser.
Review source identity, dates, page totals and sample rows before publishing a
new document revision. Do not silently apply them to another manufacturer's PDF.

The browser datasets are `app/data/supplier_pricebooks.json`,
`app/data/web_catalog_offers.json` and `app/data/catalog_documents.json`.
They are intentionally versioned public catalog data; do not include secrets or
customer project information in them.

To serve local PDF downloads after deployment, provision the two source files as
`storage/catalog-pricebooks/ls-2026-10-01.pdf` and
`storage/catalog-pricebooks/chint-2026.pdf`. Source PDFs are not committed to Git.
The document endpoint uses a fixed allowlist and authenticated access.

`import_invt_pricebook.py` imports 102 complete model/kW/HP/current/price
sequences from the observed three-page Vietnamese INVT supplier PDF. Incomplete
sequences are omitted; source current and power values are not corrected or
inferred. Upload-folder dates do not establish the price effective date or VAT.
The completed internal review currently counts 5,297 eligible public price rows
across 14 manufacturers; 18 requested manufacturers have no approved numeric
price row. This is not complete price coverage for all 32 makers.
