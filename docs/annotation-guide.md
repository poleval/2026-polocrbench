# Annotation and review guide

One sample is one page image. The current queue is a candidate selection, not a finished test. Test A/B reservations remain private until provenance, leakage and coverage audits are complete.

## Transcription (A)

Transcribe what is visible, in reading order. Preserve Polish diacritics, capitalization, punctuation, headings, lists, paragraphs, and visible redaction markers. Use Markdown headings and lists; use Markdown tables for visible tabular text. Do not modernize historical spelling. Do not infer information hidden by redaction. Flag illegible pages for adjudication rather than silently guessing. A finalized illegibility convention requires agreement before test references are frozen.

Embedded PDF text and publisher/model extracts are preannotations. They can contain OCR errors, incorrect reading order, or a text layer that does not match the displayed page. Compare every reference against the page image.

## Tables (B)

Provide a JSON array of HTML table strings in reading order, one string per visible table. Preserve every row, column, cell text, and meaningful `rowspan`/`colspan`. Use consistent `thead`/`tbody` wrappers. Empty array `[]` means the annotator checked and found no tables. `null` means B is not annotated for this page. CSV exports do not preserve merged-cell structure and cannot be accepted as verified HTML without inspecting the source image.

## Key information (C)

Use only fields supported by the document type and visible on this page. Give a JSON object of strings/nulls plus a matching `field_types` map (`text`, `date`, `amount`, `identifier`, `address`). Missing visible information is `null`; never consult another page to fill an absent value. The public input manifest will include the requested field schema. Actual date/value strings are private reference material for tests.

## Workflow

1. Choose a page in the explorer's annotation queue and enter your stable identity.
2. Correct the preannotation against the image, fill the applicable A/B/C outputs, and save a draft.
3. Submit the page for review. The submitted content is frozen for review.
4. A different person checks all annotated subtasks and approves or returns the page with a specific correction note.
5. A third person performs the second review. The store rejects the annotator's own approval and repeated approvals by the same identity.
6. A rejection clears prior approvals. Corrections must go through both reviews again.

Excluded pages require a reason and must be replaced before the split target is met. The exporter requires two reviews plus item approval and completed license/near-duplicate/coverage audits. It refuses to create release files when any selected page remains blocked.

Local identities are self-declared; assign real reviewers organizationally. Revision history records complete content snapshots, author, action, note, timestamps, and approval state. A version check prevents stale browser tabs from silently overwriting newer work. Browser drafts protect unsaved edits but do not count as submitted annotations.
