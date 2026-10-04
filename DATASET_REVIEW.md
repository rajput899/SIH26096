# Local dataset inventory and sample review

All originals retained. No records ingested or published. Provenance and redistribution rights: **Not verified**.

31 files; 1,377,012,050 bytes. 22 PDFs, 8 media files and 1 reference note. No exact checksum duplicates. SHA-256 values for every file are in `outputs/dataset-inventory.json`; all 31 rechecked unchanged.

| File | MiB | Pages | Pages with embedded text (>30 chars) |
|---|---:|---:|---:|
| Br. Ambedkar/book by br. ambedkar/Collected Works of Ambedkar vol 1.pdf | 60.90 | 13824 | 12519 |
| Br. Ambedkar/books on br. ambedkar/1458100632_Ambedkar1.pdf | 5.16 | 127 | 0 |
| Br. Ambedkar/books on br. ambedkar/ambekar-life-mission.pdf | 41.76 | 560 | 0 |
| Br. Ambedkar/refrences.txt | 0.00 | — | — |
| Br. Ambedkar/videos/1946 - Dr. B. R. Ambedkar's Constituent Assembly Speech on Dec 17.mp4 | 30.18 | — | — |
| Br. Ambedkar/videos/BabasahebAmbedkarlife.mp4 | 949.69 | — | — |
| Br. Ambedkar/videos/Bhimrao Ambedkar's rare TV appearance_ 'The social structure must change' _ BBC News India.mp4 | 12.85 | — | — |
| Br. Ambedkar/videos/Dr Ambedkar excellent speech presenting Constitution of India.mp4 | 7.40 | — | — |
| Br. Ambedkar/videos/Dr Bhimrao Ambedkar Interview-1955.mp4 | 35.14 | — | — |
| Br. Ambedkar/videos/DRAMBEDKAR FILMNEW.mp4 | 12.51 | — | — |
| Br. Ambedkar/voice/Dr BRAmbedkar speech at the Constituent Assembly.mp4 | 1.73 | — | — |
| Br. Ambedkar/voice/track_1.mp3 | 1.99 | — | — |
| Volume_01.pdf | 6.04 | 516 | 469 |
| Volume_02.pdf | 8.20 | 829 | 814 |
| Volume_03.pdf | 6.03 | 509 | 495 |
| Volume_04.pdf | 5.55 | 377 | 362 |
| Volume_05.pdf | 6.49 | 511 | 498 |
| Volume_06.pdf | 8.10 | 719 | 697 |
| Volume_07.pdf | 4.92 | 406 | 376 |
| Volume_08.pdf | 7.65 | 511 | 485 |
| Volume_09.pdf | 6.31 | 523 | 504 |
| Volume_10.pdf | 4.71 | 1105 | 1087 |
| Volume_11.pdf | 8.43 | 683 | 605 |
| Volume_12.pdf | 10.32 | 807 | 735 |
| Volume_13.pdf | 16.66 | 1278 | 1248 |
| Volume_14_01.pdf | 8.50 | 805 | 761 |
| Volume_14_02.pdf | 6.09 | 613 | 598 |
| Volume_15.pdf | 9.94 | 1133 | 1103 |
| Volume_16.pdf | 10.73 | 767 | 7 |
| Volume_17_01.pdf | 10.77 | 513 | 490 |
| Volume_17_02.pdf | 8.47 | 577 | 558 |

## Mapping and limitations

Filename mapping detects volumes 1–17, with 14_01/14_02 and 17_01/17_02 (19 files, 13,182 pages). Completeness is **Not verified**: Volume 1 PDF page 5 describes a set of 20 books, whereas only 19 named volume files are present. Do not infer which part is missing without a verified edition index. The additional Collected Works PDF has 13,824 pages and may overlap the volume set; filenames alone cannot establish source identity or duplication. No content-level deduplication or merging was performed.

There are three additional book PDFs, not the two described in the initial estimate. Two have no substantial embedded text. Volume 16 has substantial text on only 7 of 767 pages. Sparse pages may be blank, illustration or scans; page counts do not measure OCR accuracy.

## Sample — Volume_01.pdf

Read-only sample of PDF pages 1, 5, 20 and 100 extracted and rendered in 0.62 seconds. Embedded-text characters: 0, 1084, 2137, 1960. Cover OCR using existing RapidOCR took 3.95 seconds: 538 characters, minimum model confidence 0.95442. Visual comparison confirms main cover headings, but OCR reads Southberough where the scan reads Southborough: confidence does not replace correction. Text remains machine output, not verified transcription. Full-volume OCR and durable review of 516 pages were not run.

PDF page 5 visibly identifies Volume 1, Dr. Ambedkar Foundation, second reprint August 2019, first edition 14 April 1979, ISBN 978-93-5109-172-1. Record these as source-internal statements only. Acquisition URL, independent edition authenticity and redistribution permission remain **Not verified**. Reference notes contain possible government/archive/video URLs but are not a chain of custody or license.

## Media

All 8 files passed FFprobe container inspection in Docker (see `outputs/dataset-media-probe.json`). Seven are H.264/AAC video containers, including one in the voice folder; one is MP3. These checks do not authenticate speakers, establish rights, verify complete decoding or constitute listening/playback acceptance. No transcript or captions were invented.

## Ingestion gate

Existing authenticated upload requires a verified source/permission attestation and limits files to 10 MiB. PDF extraction limits documents to 50 pages. All named volumes exceed that page limit; several files also exceed the upload limit. No workaround split, compression, false attestation, production upload or publication was attempted. Owner approved local inventory/extraction/sample review only until provenance and rights are confirmed. Before bulk ingestion, implement and validate bounded durable page batches, resumability and review navigation against the complete sample; retain original filenames and hashes and prevent duplicate original ingestion.
