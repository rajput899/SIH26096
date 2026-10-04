# Phase 2 fixture provenance

No historical archival document is bundled or seeded.

`tests/test_processing.py::scanned_fixture` generates a two-page, image-only PDF locally
using Pillow. Each page is explicitly labeled `SYNTHETIC LOCAL TEST FIXTURE` and
`This is not historical archival material`. Page one contains the test token ALPHA;
page two contains BETA. All wording was authored solely for this project's automated
processing tests. It is available for this project's testing without external rights
or acquisition claims. The generator is the provenance; bytes can vary with Pillow
versions, so each test computes and checks the actual original's SHA-256.

The fixture exercises raster PDF recognition, distinct physical page locators,
PostgreSQL persistence, review/correction snapshots, verification and publication
separation. Isolated PostgreSQL schemas and temporary storage prevent it from
becoming an archival holding. Invalid-PDF and unpaginated plain-text fixtures test
failure and locator handling; these are also explicitly synthetic.

Source assessment on 2026-09-27: Project Gutenberg lists *Castes In India* by
B. R. Ambedkar (ebook 63231) at https://www.gutenberg.org/ebooks/63231 with a
public-domain-in-the-USA statement. That catalog listing was inspected, but no
suitable original paginated scan and applicable reuse decision were established in
this task. No copy was downloaded/imported and no claim of Indian reuse permission
or of acquisition from SRC-01/02/03 is made. The owner-authorized local-fixture
fallback is used. A permitted real scan remains required for historical-document
OCR quality acceptance, including any manuscript or Indian-script claims.
