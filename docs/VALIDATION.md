# Data and application checks

## Extracted edition

The current source is the MEDINK *INICET Yearwise Exam Papers 2025–2020* PDF. The extractor identifies ten May/November sittings, pairs question pages with their answer pages, and retains both the year-wide library number and the printed question number. The generated bank contains 1,983 questions across 19 subjects. Figure extraction produced 409 figure files linked to 404 questions.

Nine entries are marked read-only because the PDF has image-based answer choices, duplicate choices, or damaged source text. One image-based item has no usable figure extraction. These questions remain available for review and are excluded from scoring.

## Reproduce and check

Run the extraction pipeline from the repository root:

```powershell
python scripts/pyq/extract.py "INICET Yearwise Exam Papers 2025-2020_unlocked.pdf"
python scripts/extract-pyq-images.py "INICET Yearwise Exam Papers 2025-2020_unlocked.pdf"
python scripts/pyq/populate.py
node scripts/freeze-full-pyq-schedule.mjs
```

The generated data gate checks annual question counts, sitting assignments, subject coverage, answer shape, figure links, read-only entries, and the 397-day schedule:

```powershell
npm run validate:bank
```

The repository also contains domain, browser, and production-build checks (`npm test`, `npm run test:e2e`, and `npm run build`). They were not run during this conversion.

## Source limits

The source is an exam-preparation compilation, not an authenticated exam archive. Extraction preserves its printed keys and explanations; neither the keys nor the medical content received independent clinical review here. Figure-to-question placement is inferred from the page columns and printed question anchors, so image-based items should be checked against the PDF when precision matters. See [PDF import notes](PDF_IMPORT.md) for the page-pairing rules and known source exceptions.
