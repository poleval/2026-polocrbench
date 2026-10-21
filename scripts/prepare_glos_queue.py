#!/usr/bin/env python3
"""Prepare private candidate/annotation manifests; publisher text is unverified."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path
import tomllib
from urllib.parse import urlsplit

from PIL import Image
import pymupdf
from pydantic import Field
from polocrbench.models import StrictModel


class ReleaseConfig(StrictModel):
    require_two_reviewers: bool = True
    allow_preannotations: bool = False


class DatasetConfig(StrictModel):
    seed: int
    real_train_pages: int = Field(gt=0)
    test_a_pages: int = Field(gt=0)
    test_b_pages: int = Field(gt=0)
    synthetic_train_pages: int = Field(ge=0)
    render_dpi: int = Field(ge=72, le=300)
    max_pages_per_document: int = Field(gt=0)
    release: ReleaseConfig


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_jsonl(path, rows):
    with path.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "config/dataset.toml")
    args = parser.parse_args()
    config = DatasetConfig.model_validate(tomllib.loads(args.config.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {r["id"]: r for r in read_csv(args.dataset / "dane/dokumenty.csv")}
    table_catalog = defaultdict(list)
    for r in read_csv(args.dataset / "dane/skany-tabele-katalog.csv"):
        table_catalog[(r["dokument_id"], int(r["strona"]))].append(r)
    measurements = [json.loads(line) for line in (args.dataset / "classification/pdf-measurements.jsonl").read_text().splitlines()]
    parents = {Path(r["path"]).stem: Path(r["path"]).stem for r in measurements}

    def root(key):
        parents.setdefault(key, key)
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    def union(a, b):
        a, b = root(a), root(b)
        if a != b:
            parents[max(a, b)] = min(a, b)

    for key, row in metadata.items():
        if row["zalacznik_do"]:
            union(key, row["zalacznik_do"])
    cache_path = args.output / "candidate-pages-cache.jsonl"
    cached = {r["id"]: r for r in map(json.loads, cache_path.read_text().splitlines())} if cache_path.exists() else {}
    candidates = []
    fingerprint_owner = {}
    with cache_path.open("a") as cache:
        for n, measured in enumerate(measurements, 1):
            if "error" in measured:
                continue
            doc_id = Path(measured["path"]).stem
            meta = metadata.get(doc_id, {})
            with pymupdf.open(args.dataset / measured["path"]) as pdf:
                for page in measured["page_measurements"]:
                    if not page["scan_evidence"]:
                        continue
                    page_number = page["page"]
                    sample_id = f"gm_{measured['sha256'][:16]}_p{page_number:04d}"
                    row = cached.get(sample_id)
                    if row is None:
                        source_page = pdf[page_number - 1]
                        preview = source_page.get_pixmap(matrix=pymupdf.Matrix(.25, .25), colorspace=pymupdf.csGRAY, alpha=False)
                        # Exact rendered-thumbnail equality groups repeated visual pages;
                        # near-duplicate/template auditing remains a release requirement.
                        thumb = Image.open(BytesIO(preview.tobytes("png"))).resize((128, 180))
                        fingerprint = hashlib.sha256(thumb.tobytes()).hexdigest()
                        text = source_page.get_text(sort=True)
                        row = {"id": sample_id, "document_id": doc_id, "document_path": measured["path"],
                               "document_sha256": measured["sha256"], "page": page_number,
                               "organization": meta.get("organ", ""), "topic": meta.get("temat", ""),
                               "description": meta.get("opis", ""), "source_url": meta.get("url", ""),
                               "license_status": "publisher_official_document_claim_pending_per_item_review",
                               "thumbnail_sha256": fingerprint, "page_metrics": page,
                               "preannotation": {"text": text, "provenance": "embedded_pdf_text_unverified", "status": "preannotation"},
                               "table_preannotation_sources": table_catalog.get((doc_id, page_number), []),
                               "annotation_status": "unstarted", "required_reviewers": 2}
                        cache.write(json.dumps(row, ensure_ascii=False) + "\n")
                        cache.flush()
                    owner = fingerprint_owner.setdefault(row["thumbnail_sha256"], doc_id)
                    union(doc_id, owner)
                    candidates.append(row)
            if n % 100 == 0:
                print(f"Inspected {n}/{len(measurements)} documents; {len(candidates)} raster pages", flush=True)
    groups = defaultdict(list)
    seen = set()
    unique = []
    for row in candidates:
        row["group_id"] = "family_" + hashlib.sha256(root(row["document_id"]).encode()).hexdigest()[:16]
        row["duplicate_visual_page"] = row["thumbnail_sha256"] in seen
        seen.add(row["thumbnail_sha256"])
        if not row["duplicate_visual_page"]:
            unique.append(row)
            groups[row["group_id"]].append(row)
    targets = {"train": config.real_train_pages, "test_a": config.test_a_pages, "test_b": config.test_b_pages}
    counts, assignments, selected = Counter(), {}, set()
    group_order = sorted(groups, key=lambda group: hashlib.sha256(f"{config.seed}:{group}".encode()).hexdigest())
    for group in group_order:
        pages, per_doc = [], Counter()
        for row in sorted(groups[group], key=lambda row: (not bool(row["table_preannotation_sources"]), row["document_id"], row["page"])):
            if per_doc[row["document_id"]] < config.max_pages_per_document:
                pages.append(row)
                per_doc[row["document_id"]] += 1
        split = max(targets, key=lambda name: targets[name] - counts[name])
        remaining = targets[split] - counts[split]
        if remaining <= 0:
            assignments[group] = "reserve"
            continue
        chosen = pages[:remaining]
        assignments[group] = split
        selected.update(row["id"] for row in chosen)
        counts[split] += len(chosen)
    for row in candidates:
        row["planned_split"] = assignments.get(row["group_id"], "reserve")
        row["selected_for_annotation"] = row["id"] in selected
        row["split_status"] = "draft_requires_near_duplicate_and_coverage_review"
    selected_rows = [row for row in candidates if row["selected_for_annotation"]]
    write_jsonl(args.output / "candidate-pages.jsonl", candidates)
    write_jsonl(args.output / "annotation-queue.jsonl", selected_rows)
    for split in targets:
        write_jsonl(args.output / f"{split}-candidates.jsonl", [r for r in selected_rows if r["planned_split"] == split])
    group_splits = defaultdict(set)
    for row in selected_rows:
        group_splits[row["group_id"]].add(row["planned_split"])
    if any(len(splits) > 1 for splits in group_splits.values()):
        raise ValueError("Document family leakage across splits")
    summary = {"candidate_scan_pages": len(candidates), "unique_visual_thumbnails": len(unique),
               "duplicate_visual_pages": len(candidates) - len(unique), "document_family_groups": len(groups),
               "selected_counts": dict(counts), "target_counts": targets,
               "table_page_candidates_selected": sum(bool(r["table_preannotation_sources"]) for r in selected_rows),
               "source": "glos-migranta", "status": "annotation_pending_not_a_released_benchmark",
               "remaining_release_requirements": ["Manual annotation and two distinct reviews", "Near duplicate and template leakage audit", "Per-item redistribution/license review", "Historical, handwritten, photo and OOD Test B coverage", "Platform integration and baseline runs"],
               "config": config.model_dump()}
    (args.output / "preparation-summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
