# Spider data quality fixes

## P0

- Sylvie's: use the real lot title from the page instead of an internal `sylvies_*` identifier; derive usable lot detail metadata from the visible lot title/appellation; store absolute lot URLs.
- Steinfels: do not run wine LWIN metadata inference on whisky/spirit lots; use parsed API description fields first and only infer wine metadata for wine lots.

## P1

- WineAuctioneer: remove the first-page `break` so every lot link is crawled; verify authenticated lot pages for region/country fields and backfill from LWIN where the site does not provide them.
- Tajan: parse explicit producer/vintage/unit from the lot title before fuzzy LWIN metadata inference; avoid overwriting title evidence with weak fuzzy matches.
- Zachys: store `lot_type` as an array, build real auction/lot URLs, and avoid persisting Excel display labels such as `Lot 2541` as URLs.

## Follow-up

- Re-run affected spiders after each fix.
- Re-run `npm run match -- --no-resume` only after source data is corrected.
- Regenerate sales stats, export zip, and Chinese data quality report.
