#!/usr/bin/env python3
"""Measured transcription-only baseline; B/C outputs are intentionally absent."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", default="pol")
    parser.add_argument("--tessdata-dir", type=Path)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.inputs.read_text().splitlines()]
    if args.limit:
        rows = rows[:args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    version = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    timings = []
    with args.output.open("w") as output:
        for row in rows:
            image = (args.inputs.parent / row["image"]).resolve()
            if not image.is_relative_to(args.inputs.parent.resolve()):
                raise ValueError("Image path escapes input directory")
            command = ["tesseract", str(image), "stdout", "-l", args.language, "--psm", "3"]
            if args.tessdata_dir:
                command += ["--tessdata-dir", str(args.tessdata_dir)]
            start = time.monotonic()
            process = subprocess.run(command, capture_output=True, text=True, timeout=120)
            elapsed = time.monotonic() - start
            if process.returncode:
                raise RuntimeError(process.stderr)
            output.write(json.dumps({"id": row["id"], "text": process.stdout}, ensure_ascii=False) + "\n")
            timings.append({"id": row["id"], "seconds": elapsed, "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest()})
            print(f"{len(timings)}/{len(rows)}: {row['id']} ({elapsed:.2f}s)", flush=True)
    metadata = {"engine": version, "language": args.language, "psm": 3, "tasks": ["A"],
                "created_at": datetime.now(timezone.utc).isoformat(), "pages": len(rows),
                "seconds_total": sum(t["seconds"] for t in timings), "timings": timings,
                "scope": "smoke_subset" if args.limit else "full_provided_input_manifest",
                "note": "Plain OCR text; no Markdown layout reconstruction, table HTML, or KIE. No hardware-cost estimate."}
    args.output.with_suffix(".run.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
