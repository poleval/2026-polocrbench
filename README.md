# PolOCRBench: Polish Document Understanding

**PolEval 2026 shared task**

PolOCRBench evaluates transcription, table extraction, and key information extraction from challenging Polish document images. It provides a common evaluation setting for vision-language models, dedicated OCR systems, and models developed for Polish.

**Organizers:** Kacper Wikieł ([Slayer AI Lab](https://slayer.fabryka.ai)) and Piotr Senkus (WNE), Warsaw, Poland.

**Contact:** [k.wikiel@gmail.com](mailto:k.wikiel@gmail.com). Questions about the task can also be raised through [GitHub Issues](https://github.com/poleval/2026-polocrbench/issues).

## Task description

The input is an image of a document page in PNG or JPEG format. Participants may enter any subset of the following subtasks:

| Subtask | Required output |
| --- | --- |
| **A. Full-page transcription** | Markdown text preserving reading order, headings, lists, and paragraphs. |
| **B. Table extraction** | HTML tables preserving both table structure and cell contents. |
| **C. Key Information Extraction (KIE)** | JSON conforming to the schema for the document type, such as an invoice, contract, official letter, or form. |

The benchmark focuses on difficult documents rather than clean, digitally generated PDF pages. The intended coverage includes:

- Contemporary printed documents: official correspondence, invoices, contracts, forms, and administrative decisions.
- Historical prints from Polona: Fraktur and Schwabacher typefaces, nineteenth-century spelling, and two-column layouts.
- Handwriting: completed forms and handwritten notes.
- Phone photographs with perspective distortion, shadows, blur, or low resolution.
- Dense financial and technical tables, mixed Polish/English text, and mathematical expressions.

## Motivation

PolOCRBench brings an OCRBench/OmniDocBench-style evaluation to Polish document understanding. Its goal is to support comparable measurements of frontier models such as GPT, Gemini, Claude, and Qwen-VL; open OCR systems such as Surya, Chandra, PaddleOCR, olmOCR, and dots.ocr; and Polish-focused model families such as Bielik-V and PLLuM. These are examples of systems of interest, not a list of evaluated submissions.

Polish introduces specific challenges: diacritics such as ą, ł, ż, and ź; inflection in table headings and extracted fields; historical spelling and typefaces; and local conventions for dates, monetary amounts, NIP tax identifiers, and PESEL identifiers. End-to-end document understanding must recover both the text and its structure.

The task is relevant to document workflows in businesses and public administration, including invoices, official correspondence, and archive digitization. It also enables research on cross-lingual transfer in vision-language models and on supervised fine-tuning and reinforcement learning for Polish document understanding.

## Data

### Sources and annotation

The planned dataset combines:

- Public-domain historical documents from Polona / the National Library of Poland.
- Public documents and official form templates from sources such as BIP, ISAP, and KRS, subject to checking their suitability for redistribution and commercial use.
- Synthetic invoices, contracts, and letters generated with randomized content and degraded through scanning, photography, print-and-scan, and compression transformations.
- Handwritten material contributed by volunteers with written consent, without personal data, under CC BY 4.0.

Test references are to be manually transcribed and independently checked twice. Training annotations may use model-assisted pre-annotation followed by human verification and correction.

### Planned splits

| Split | Target size | Purpose |
| --- | --- | --- |
| Training | Approximately 2,000 pages, including approximately 1,200 synthetic pages | Training and adaptation. |
| Test A | Approximately 500 pages | Development evaluation. |
| Test B | Approximately 500 pages | Final evaluation and the main ranking. |

Test B will include document types and degradations absent from the training set and Test A to assess generalization.

The intended data license is **CC BY 4.0**; evaluation scripts are intended to use the **MIT license**. Datasets are planned for publication under [SlayerLab on Hugging Face](https://huggingface.co/SlayerLab).

### Release status

This checkout includes a **v0.1 evaluation and annotation toolkit**: deterministic A/B/C scoring, strict schemas, a local PDF/text explorer, two-reviewer annotation workflow, candidate preparation, synthetic training generation, and guarded release export. See the [delivery guide](docs/delivery-guide.md), [protocol](docs/protocol-v0.1.md), [annotation guide](docs/annotation-guide.md), and [review of earlier PolEval editions](docs/historical-quality-review.md).

**Verified competition data are not released yet.** Candidate test assignments and references remain private. Current preparation covers official-document scans from one source; historical, handwritten, photographed, and OOD coverage still requires work. Synthetic training examples are candidates, not replacements for reviewed real tests. A local adapter or smoke baseline does not establish that the remote platform is configured.

The split sizes above remain targets. Actual releases will include versioned manifests, hashes, annotation coverage, reproducible baseline evidence, and an announcement after the review and audit gates pass.

## Evaluation

Evaluation is designed to be fully automatic and deterministic, without LLM judges. The public evaluation script and submission format will be compatible with AmuEval.

| Subtask | Primary metric | Additional reporting and normalization |
| --- | --- | --- |
| A. Transcription | Character Error Rate (CER) | Word Error Rate (WER); NFC Unicode, whitespace, and quotation-mark normalization; additional edit-distance evaluation of Markdown structure, including headings and lists. |
| B. Tables | Tree Edit Distance-based Similarity (TEDS) | TEDS-struct reported as an auxiliary metric. |
| C. KIE | Field-level F1 | Exact match after normalization of dates, monetary amounts, NIP identifiers, and addresses; results reported by field type. |

The aggregate score is the mean of the normalized subtask scores: **1 − CER**, **TEDS**, and **F1**. The main ranking uses Test B; Test A supports development. Participants may enter individual subtasks. Detailed handling of partial-subtask submissions and executable normalization rules will accompany the evaluation release.

## Participation tracks

Separate rankings are planned for three tracks:

1. **Constrained:** training uses only organizer-provided data; any pretrained open-weight model is allowed.
2. **Open:** any data and models may be used, including fine-tuning.
3. **Zero-shot / API:** closed and open models without fine-tuning, using a uniform organizer-provided prompt. This track allows frontier API models and Polish models to be compared under a common prompting protocol.

Participants should identify the subtasks and track of their submission. The organizers plan to provide baselines for each track, including Surya, Qwen-VL, and an API model, together with inference cost per page.

## Schedule

All dates of PolEval 2026 are listed on the [PolEval dates page](https://poleval.pl/dates/).

Release announcements will be published in this repository.

## After the shared task

The organizers plan to maintain a public leaderboard at [CodeSOTA OCR](https://codesota.com/ocr) and publish the datasets on Hugging Face. Academic collaboration is welcome, particularly for historical-document annotation and reviewing.
