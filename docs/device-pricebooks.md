# Device price books

The customer page `/device-catalog` is labelled **Bảng giá**. Software
subscriptions at `/pricing` are labelled **Gói dịch vụ**.

## Identity and provenance

`item_name` (Tên hàng) identifies a model inside its manufacturer. A model can
have multiple rated-current ranges, voltages, prices and source offers.
`model_key` combines manufacturer and item name; variant `id` values identify
individual source rows and must not replace the model identity or collapse
different configurations.

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
