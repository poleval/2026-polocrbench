# Executable evaluation protocol v0.1 (review draft)

This document specifies implemented behavior. It is not an announcement that a verified test set or the remote competition platform is live.

Each UTF-8 JSONL/TSV line contains one object, with literal newlines/tabs escaped by JSON. No header. Prediction keys: `id`, optional `text` (Markdown string), `tables` (ordered HTML string array), `kie` (string/null field object). Unknown top-level keys, duplicate IDs, and unknown IDs fail validation. A missing page prediction is scored as empty output. The AmuEval adapter additionally requires the exact public input order and one line per sample.

Reference-only keys: `status`, `split`, `reviewers`, `field_types`. Unverified preannotations are rejected unless the explicit diagnostic flag is set; diagnostic results are ineligible for competition ranking. Synthetic programmatic labels cannot be assigned to Test A/B. Verified tests require two distinct review identities.

## A: transcription

Normalize prediction and reference identically: NFC, curly double/single quotation marks to ASCII quotes, then all whitespace runs to a single space. Preserve case, diacritics, punctuation, digits, and Markdown syntax. Corpus CER is total character edit distance divided by total reference characters. WER is the equivalent word-token calculation. Empty reference denominator uses 1. Raw CER may exceed 1; the normalized A score is `max(0, 1-CER)`. Markdown structure error is additional token edit distance on heading levels, list markers, table rows, blockquotes and code fences, divided by reference structure-token count (minimum 1).

## B: tables

Each HTML output contains one non-nested table. Cells retain text, inline markup, `rowspan`, and `colspan`. Cell-aware APTED tree distance follows PubTabNet's TEDS approach; the denominator counts descendants of the table root. The implementation explicitly extends cell handling to `th`, preserving tag identity. Invalid prediction markup scores zero; invalid references are errors. TEDS-struct ignores cell contents. Tables are paired in page reading order. Missing or extra tables score zero; page score averages over the longer table list. Annotated empty/empty pages score 1. B is the mean page score. Reference table conventions must be consistent before release.

## C: KIE

Normalize typed fields with executable rules: NFC/whitespace/quotes for text; ISO or day-first dotted/slashed/hyphenated dates to ISO when valid; supported decimal formats and currency suffixes to Decimal; identifier whitespace/hyphens removed, case uppercased; addresses casefolded with commas/full stops removed. Values that fail typed parsing remain text and do not receive permissive fuzzy matching. Polish letters and meaningful address separators/digits remain.

Count exact non-null `(field, normalized value)` pairs per page. Correct pairs are TP, unsupported/wrong predicted pairs FP, missing/wrong expected pairs FN. A wrong value therefore contributes both FP and FN. Micro field F1 is `2TP/(2TP+FP+FN)`; all-empty count denominator yields 1. Report F1 by field as well.

## Aggregation

Score only requested subtasks with available annotation. Requested tasks with no reference coverage are errors. Report separate A/B/C scores. Full aggregate exists only when all three tasks are scored: equal mean of normalized A, TEDS, and KIE F1. Partial submissions have a `partial_score`, not a comparable full aggregate. Track declarations and any official per-subtask leaderboard setup are separate from these calculations.

An official ranking eligibility flag additionally requires verified Test A/B reference rows. The organization must choose a single intended test split per platform challenge; this scorer does not establish submission provenance or resource-track compliance.
