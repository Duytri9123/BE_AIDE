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
