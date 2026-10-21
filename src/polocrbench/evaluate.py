from collections import Counter
import json
from pathlib import Path
from statistics import mean

from rapidfuzz.distance import Levenshtein

from .metrics import kie_counts, markdown_structure, teds, text_counts
from .models import Prediction, Reference


def load_rows(path, model):
    rows = {}
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"Blank line at {path}:{number}")
            if len(line.encode()) > 5_000_000:
                raise ValueError(f"Row exceeds 5 MB at line {number}")
            row = model.model_validate_json(line)
            if row.id in rows:
                raise ValueError(f"Duplicate sample ID: {row.id}")
            rows[row.id] = row
    if not rows:
        raise ValueError("Input contains no samples")
    return rows


def evaluate(references, predictions, tasks=("A", "B", "C"), allow_provisional=False):
    if not tasks or set(tasks) - {"A", "B", "C"}:
        raise ValueError("Choose one or more subtasks A/B/C")
    extra = set(predictions) - set(references)
    if extra:
        raise ValueError(f"Unknown prediction IDs: {sorted(extra)[:5]}")
    provisional = [r.id for r in references.values() if r.status == "preannotation"]
    if provisional and not allow_provisional:
        raise ValueError("Unverified preannotations cannot be used for official scoring; use --allow-provisional for diagnostics")
    text_totals, kie_totals = Counter(), Counter()
    table_scores, structure_scores, markdown_edits, page_scores = [], [], [], []
    field_scores = {}
    coverage = Counter()
    for sample_id, reference in references.items():
        pred = predictions.get(sample_id, Prediction(id=sample_id))
        row = {"id": sample_id, "missing_prediction": sample_id not in predictions}
        if "A" in tasks and reference.text is not None:
            counts = text_counts(reference.text, pred.text or "")
            text_totals.update(counts)
            coverage["A"] += 1
            row["cer"] = counts["char_edits"] / max(1, counts["reference_chars"])
            ref_structure, pred_structure = markdown_structure(reference.text), markdown_structure(pred.text or "")
            edits = Levenshtein.distance(ref_structure, pred_structure)
            markdown_edits.append((edits, len(ref_structure)))
        if "B" in tasks and reference.tables is not None:
            ref_tables, pred_tables = reference.tables, pred.tables or []
            n = max(len(ref_tables), len(pred_tables))
            scores, structures = [], []
            for index in range(n):
                if index >= len(ref_tables) or index >= len(pred_tables):
                    scores.append(0.0)
                    structures.append(0.0)
                else:
                    scores.append(teds(ref_tables[index], pred_tables[index]))
                    structures.append(teds(ref_tables[index], pred_tables[index], structure_only=True))
            row["teds"] = mean(scores) if n else 1.0
            table_scores.append(row["teds"])
            structure_scores.append(mean(structures) if n else 1.0)
            coverage["B"] += 1
        if "C" in tasks and reference.kie is not None:
            counts = kie_counts(reference.kie, pred.kie or {}, reference.field_types)
            kie_totals.update(counts)
            for field in set(reference.kie) | set(pred.kie or {}):
                stats = field_scores.setdefault(field, Counter())
                stats.update(kie_counts({field: reference.kie.get(field)}, {field: (pred.kie or {}).get(field)}, reference.field_types))
            coverage["C"] += 1
            row["kie"] = counts
        page_scores.append(row)
    missing_tasks = set(tasks) - set(coverage)
    if missing_tasks:
        raise ValueError(f"No references for requested subtasks: {sorted(missing_tasks)}")

    def f1(counts):
        denominator = 2 * counts["tp"] + counts["fp"] + counts["fn"]
        return 2 * counts["tp"] / denominator if denominator else 1.0

    metrics, scores = {}, {}
    if coverage["A"]:
        cer = text_totals["char_edits"] / max(1, text_totals["reference_chars"])
        metrics.update(cer=cer, wer=text_totals["word_edits"] / max(1, text_totals["reference_words"]),
                       markdown_structure_error=sum(x[0] for x in markdown_edits) / max(1, sum(x[1] for x in markdown_edits)),
                       text_counts=dict(text_totals))
        scores["A"] = max(0.0, 1 - cer)
    if coverage["B"]:
        metrics.update(teds=mean(table_scores), teds_struct=mean(structure_scores))
        scores["B"] = metrics["teds"]
    if coverage["C"]:
        metrics.update(kie_f1=f1(kie_totals), kie_counts=dict(kie_totals),
                       kie_by_field={field: {**counts, "f1": f1(counts)} for field, counts in sorted(field_scores.items())})
        scores["C"] = metrics["kie_f1"]
    return {"protocol": "polocrbench-v0.1", "provisional": bool(provisional),
            "eligible_for_official_ranking": not provisional and all(r.split in ("test_a", "test_b") and r.status == "verified" for r in references.values()),
            "tasks": sorted(set(tasks)), "coverage": dict(coverage), "pages": len(references),
            "missing_predictions": len(set(references) - set(predictions)), "metrics": metrics,
            "subtask_scores": scores, "aggregate": mean(scores.values()) if set(scores) == {"A", "B", "C"} else None,
            "partial_score": mean(scores.values()), "per_page": page_scores}


def score_files(reference_path, prediction_path, **kwargs):
    return evaluate(load_rows(reference_path, Reference), load_rows(prediction_path, Prediction), **kwargs)
