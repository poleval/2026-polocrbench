# Quality decisions informed by earlier PolEval editions

Review date: 2026-10-21. The [edition archive](https://poleval.pl/editions/) is the starting point. The decisions below are implementation choices for review, not claims that older organizers endorsed this protocol.

## 2021: OCR post-correction

The [official task repository](https://github.com/poleval/2021-ocr-correction) distinguishes training and labeled development data from Test A and the final Test B. It identifies source books and pages, specifies escaping of line breaks/backslashes, and ranks systems with WER. Its inputs are OCR text, whereas PolOCRBench inputs are images. A post-correction score must therefore not be presented as an image-to-text OCR comparison.

Applied here: stable page IDs, explicit input/output schema, corpus-level CER/WER, strict duplicate-ID handling, separate private references, and deterministic evaluation. The candidate queue tracks source documents and document families. The final test must remain separate from development feedback. Previously published gold text is a contamination consideration; it is not new hidden test ground truth.

## 2025: document layout

The [official layout task](https://github.com/poleval/2025-document-layout) uses manually annotated regions following DocLayNet/COCO conventions, publishes the expected categories and image IDs, and specifies COCO mAP over IoU thresholds 0.50–0.95. The submission convention even specifies a JSON payload with a TSV filename for its platform.

Applied here: distinguish transcription, table structure, and field extraction from region detection. Do not claim layout-detection coverage without region annotations and a matching metric. Publish an executable schema and example payloads, then test the exact platform import path. A filename extension alone does not establish AmuEval compatibility. Our adapter follows the inspected backend interface, but remote registration and an end-to-end platform submission are still pending.

## 2025: Śmigiel

[Śmigiel](https://github.com/poleval/2025-smigiel) separates constrained/open/unsupervised settings, describes its data domains and balancing, and includes held-out genres/models in its test design. It asks for resource disclosure and reproducible descriptions. Its restrictions on proprietary resources are specific to that competition.

Applied here: retain separate training-resource tracks and require model/revision, external-data, prompt, decoding, tool, and hardware disclosures. Do not copy Śmigiel's proprietary-model restriction into the accepted PolOCRBench zero-shot/API proposal. A random split of one source corpus does not demonstrate held-out document types or degradation families. Current Głos Migranta Test B assignments are draft reservations, not evidence of OOD coverage.

## 2024: reading comprehension

The [official repository](https://github.com/poleval/2024-qa-task) supplies an evaluation script, examples, stable question identifiers, and explicit aggregation of two complementary metrics. It distinguishes unanswerable questions from positive answers and describes ordered line-based submissions.

Applied here: provide exact-match and deliberately wrong examples, define missing/extra outputs, report subtask metrics separately, and distinguish unannotated (`null`) from an annotated empty result (`[]` for tables). Missing page predictions are penalized; extra IDs are rejected. Extra KIE fields and extra predicted tables are penalized. Full aggregate scores require A/B/C; partial entrants receive separate subtask scores.

## 2020: information extraction from complex documents

The [task description](https://poleval.pl/2020/tasks/information-extraction/) documents its source formats, output fields, field coverage, and F1 evaluation. That makes the schema and annotation coverage part of the benchmark specification.

Applied here: KIE fields are explicitly typed, `null` means absent, and date/amount/identifier/address normalization is executable. Report per-field F1 and annotate only what is visible on the evaluated page. Do not recover redacted private information. The dataset card must report annotation disagreement and coverage by source/category rather than only total page counts.

## Gates before announcing a competition data release

1. Finish annotation, two independent reviews, and disagreement resolution. A named local identity is an audit aid, not authenticated proof of independence.
2. Audit near duplicates, shared templates, document families, and published-text contamination across splits. Current grouping covers catalog attachments and exact rendered-thumbnail duplicates; near-duplicate review is outstanding.
3. Complete per-item provenance and redistribution review. A publisher's broad license statement is not a substitute for recording third-party exceptions.
4. Fill and measure historical, handwritten, photographed, dense-table, and other promised coverage. The present real-page queue contains official documents from one source only.
5. Freeze normalization, table ordering, missing-output policy, task weighting, and the protocol version before accepting scored competition submissions.
6. Run both local scorer and the actual platform on identical fixtures; verify matching scores and hidden Test B feedback. Remote platform access/configuration remains pending.
7. Release at least one real, reproducible baseline run with pinned model/software, outputs, latency, and bounded cost evidence. A small Tesseract smoke run is tooling validation, not the promised full baseline suite.

The original planned dates must not be shown as completed releases. Publish actual dates, manifests, hashes, versioned artifacts, and an explicit coverage statement when the gates pass.
