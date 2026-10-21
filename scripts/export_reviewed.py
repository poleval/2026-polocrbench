#!/usr/bin/env python3
"""Export only reviewed pages. Public inputs and private answers stay separate."""
import argparse
import hashlib
import json
from pathlib import Path

import pymupdf

from polocrbench.annotation import AnnotationStore
from polocrbench.models import Reference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "test_a", "test_b"], required=True)
    parser.add_argument("--audit", type=Path, required=True, help="JSON with approved_ids and completed audits")
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text())
    for gate in ("license_review_complete", "near_duplicate_review_complete", "coverage_review_complete"):
        if audit.get(gate) is not True:
            raise ValueError(f"Release gate is not complete: {gate}")
    if not audit.get("reviewer") or not audit.get("evidence"):
        raise ValueError("Audit needs named reviewer and evidence references")
    allowed = set(audit["approved_ids"])
    selected = [json.loads(line) for line in (args.workspace / "annotation-queue.jsonl").read_text().splitlines()]
    selected = [r for r in selected if r["planned_split"] == args.split]
    store = AnnotationStore(args.workspace / "annotations")
    references, inputs, blocked = [], [], []
    for row in selected:
        annotation = store.get(row["id"])
        if row["id"] not in allowed or annotation["status"] != "verified":
            blocked.append(row["id"])
            continue
        reference = Reference(id=row["id"], text=annotation["text"], tables=annotation["tables"],
                              kie=annotation["kie"], field_types=annotation["field_types"],
                              status="verified", split=args.split,
                              reviewers=[r["actor"] for r in annotation["reviews"]])
        references.append(reference.model_dump())
        inputs.append({"id": row["id"], "image": f"images/{row['id']}.png",
                       "subtasks": [task for task, value in (("A", reference.text), ("B", reference.tables), ("C", reference.kie)) if value is not None],
                       "kie_schema": annotation["field_types"] if annotation["kie"] is not None else None})
    if blocked:
        raise ValueError(f"Release blocked: {len(blocked)}/{len(selected)} pages lack two reviews and/or item approval. No release files written.")
    if not selected:
        raise ValueError("Selected split contains no pages")
    # Validate everything before producing any release files.
    for row in selected:
        source = args.dataset / row["document_path"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["document_sha256"]:
            raise ValueError(f"Changed source PDF: {row['id']}")
    image_dir = args.public_output / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    args.private_output.mkdir(parents=True, exist_ok=True)
    for row in selected:
        with pymupdf.open(args.dataset / row["document_path"]) as pdf:
            pix = pdf[row["page"] - 1].get_pixmap(matrix=pymupdf.Matrix(150/72,150/72), alpha=False)
            pix.save(image_dir / f"{row['id']}.png")
    for directory, filename, rows in [(args.public_output, "inputs.jsonl", inputs), (args.private_output, "references.jsonl", references)]:
        (directory / filename).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"Exported {len(inputs)} public page images; answers written only to {args.private_output}")


if __name__ == "__main__":
    main()
