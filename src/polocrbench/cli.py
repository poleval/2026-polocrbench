import argparse
import json
from pathlib import Path

from .evaluate import score_files


def main():
    parser = argparse.ArgumentParser(description="PolOCRBench deterministic scorer")
    commands = parser.add_subparsers(dest="command", required=True)
    score = commands.add_parser("score")
    score.add_argument("--references", type=Path, required=True)
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--tasks", nargs="+", choices=["A", "B", "C"], default=["A", "B", "C"])
    score.add_argument("--allow-provisional", action="store_true")
    score.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = score_files(args.references, args.predictions, tasks=args.tasks, allow_provisional=args.allow_provisional)
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded)
