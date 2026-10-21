# Delivery toolkit

Executable preparation infrastructure; verified competition data release remains gated on human review, coverage, provenance, leakage checks, baseline coverage, and platform setup. See `historical-quality-review.md`.

## Installation and scoring

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest -q
.venv/bin/polocrbench score --references examples/references.jsonl \
  --predictions examples/predictions.jsonl --tasks A B C --output /tmp/score.json
```

Python 3.11+ is required. The fictitious examples score 1.0 for A/B/C; they are smoke fixtures, not competition answers. Schemas are in `schemas/`. See `protocol-v0.1.md` for exact behavior. The explorer, annotation workflow, generator and scorer do not use hosted model credentials.

## Private candidate selection

```sh
python scripts/prepare_glos_queue.py --dataset /path/to/glos-migranta \
  --output /private/path/2026-polocrbench-secret/workspace
```

Validated TOML controls deterministic draft selection. Catalog attachments and exact rendered-thumbnail duplicates stay within document families. Targets: 800 real training pages, 500 Test A reservations, 500 Test B reservations. Source text is unverified preannotation; Test B assignments do not establish OOD coverage. Near-duplicate/template auditing remains required.

## Local annotation explorer

```sh
polocrbench-explorer --workspace /path/to/OCR_WORK --port 8941
```

Expected layout: `OCR_WORK/glos-migranta/` and `OCR_WORK/benchmark/2026-polocrbench-secret/workspace/`. Choose the annotation queue/stage in the sidebar, then **Anotacja i przegląd**. See `annotation-guide.md`. Use one server per annotation directory. Identities are self-declared; organize actual independent reviewers separately. Full revisions remain private. Stale revisions are rejected. Browser drafts protect unsaved work but do not count as submitted annotations.

## Synthetic training candidates

```sh
python scripts/generate_synthetic.py --output /tmp/synthetic-train \
  --references /private/path/synthetic-references.jsonl --count 1200
```

Four simple document families and scanner/JPEG/blur variants produce image hashes, inputs and separate source-exact A/B/C labels. Layout diversity still needs expansion and auditing. 1,200 pages does not mean 1,200 independent layouts. These are training candidates, not real scans or programmatic Test A/B references.

## Optional OCR smoke baseline

```sh
python scripts/run_tesseract.py --inputs /tmp/synthetic-train/inputs.jsonl \
  --output /tmp/tesseract/predictions.jsonl --tessdata-dir /path/to/tessdata --limit 12
```

Requires system Tesseract and Polish traineddata. Records version, image hashes, timings, scope and raw outputs. It supports A only: no Markdown reconstruction, table HTML or KIE. Score using the matching subset of references and `--tasks A`. A small run validates tooling; it is not a full-dataset baseline.

## Guarded release export

```sh
python scripts/export_reviewed.py --workspace /private/path/workspace \
  --dataset /path/to/glos-migranta --split test_a \
  --audit /private/path/release-audit.json \
  --public-output /release/inputs/test-a --private-output /private/answers/test-a
```

Audit JSON requires `reviewer`, `evidence`, `approved_ids`, and true `license_review_complete`, `near_duplicate_review_complete`, `coverage_review_complete` fields recording actual completed checks. All selected pages need two reviews and item approval; otherwise export fails before writing a release. Source PDF hashes are rechecked.

Publish approved images/input manifests separately from private test answers, source mappings, split assignments, reviews and audits. Publicly available source text is a contamination consideration, so do not promise undiscoverable answers.

## AmuEval handoff

`export_amueval.py` writes one JSON object per TSV line, no header, in input-manifest order. `amueval_adapter.py` targets the inspected backend `MetricBase` interface. Platform owners still need to install/register it, create track/subtask challenges, upload private references, check score parity, and configure hidden Test B feedback. Remote setup has not been performed.
