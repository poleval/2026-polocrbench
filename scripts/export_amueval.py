#!/usr/bin/env python3
"""Write ordered JSON-per-line TSV predictions using a public input manifest."""
import argparse
import json
from pathlib import Path
from polocrbench.evaluate import load_rows
from polocrbench.models import Prediction


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ids = [json.loads(line)["id"] for line in args.inputs.read_text().splitlines()]
    if len(ids) != len(set(ids)):
        raise ValueError("Input manifest contains duplicate IDs")
    predictions = load_rows(args.predictions, Prediction)
    if set(predictions) - set(ids):
        raise ValueError("Predictions contain unknown IDs")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w") as output:
        for sample_id in ids:
            output.write(predictions.get(sample_id, Prediction(id=sample_id)).model_dump_json() + "\n")
    print(f"Wrote {len(ids)} rows in manifest order; missing predictions replaced with null outputs")


if __name__ == "__main__":
    main()
