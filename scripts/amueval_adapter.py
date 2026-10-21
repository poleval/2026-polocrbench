"""AmuEval MetricBase adapter: one JSON object per TSV line, no header.

Install alongside AmuEval's backend and register PolOCRBench in its metrics
registry. This repository does not claim that the remote platform is configured.
"""
import json
from pydantic import Field
from metrics.metric_base import MetricBase
from polocrbench.evaluate import evaluate
from polocrbench.models import Prediction, Reference


class PolOCRBench(MetricBase):
    sorting: str = "descending"
    tasks: list[str] = Field(default_factory=lambda: ["A", "B", "C"])

    def info(self):
        return {"name": "PolOCRBench v0.1", "link": "https://github.com/poleval/2026-polocrbench", "parameters": []}

    def calculate(self, references: list[str], hypotheses: list[str]) -> float:
        if len(references) != len(hypotheses):
            raise ValueError("Expected one prediction per reference row")
        refs, preds = {}, {}
        for reference, prediction in zip(references, hypotheses):
            ref = Reference.model_validate_json(reference)
            pred = Prediction.model_validate_json(prediction)
            if ref.id != pred.id or ref.id in refs:
                raise ValueError("AmuEval rows must have matching unique IDs in reference order")
            refs[ref.id], preds[pred.id] = ref, pred
        result = evaluate(refs, preds, tasks=self.tasks)
        if not result["eligible_for_official_ranking"]:
            raise ValueError("Only verified test references are eligible on the competition platform")
        return result["aggregate"] if set(self.tasks) == {"A", "B", "C"} else result["partial_score"]
