# Application architecture

Rounds is a static React and TypeScript INICET study app. Imported papers are the complete active question source. The PDF extraction and year-wise data model are documented in [PDF import and verification](PDF_IMPORT.md).

## Architecture decisions

- Annual library modules combine May and November sittings while keeping each question’s printed sitting and printed question number.
- A single frozen schedule cycles through all 1,983 imported questions. Five distinct subjects are selected per day; the final day uses two repeats after complete coverage.
- Dates are ISO calendar days in the user’s saved IANA study timezone. Travel does not change the saved timezone, and date arithmetic uses UTC ordinals.
- Daily attempts record completion timestamps and streak eligibility. Only same-day completion earns streak credit; catch-up remains available without repairing a missed streak.
- Browser time is not authenticated. Persisted rollback and in-session clock jumps are detected, but deliberate clock or local-storage edits cannot be prevented in a static app.
- The archive begins 1 January 2026. Earlier challenge dates are retrospective practice.
- Progress is stored in IndexedDB with a localStorage fallback, backup import/export, and explicit degraded-storage messaging.
- The deployed app is static output in `dist/`; there is no application server, remote question generation, or authentication dependency.
