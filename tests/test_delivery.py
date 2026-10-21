import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from polocrbench.evaluate import load_rows, score_files
from polocrbench.models import Reference

ROOT = Path(__file__).resolve().parents[1]


def test_published_fixture_score():
    result=score_files(ROOT/"examples/references.jsonl",ROOT/"examples/predictions.jsonl")
    assert result["aggregate"]==1
    assert result["eligible_for_official_ranking"] is False


def test_synthetic_labels_validate_and_generator_is_reproducible(tmp_path):
    spec=importlib.util.spec_from_file_location("synthetic_generator",ROOT/"scripts/generate_synthetic.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for index in range(4):
        image, public, reference=module.generate(index,20261021,ROOT/"assets/NotoSans-Regular.ttf")
        second, public2, reference2=module.generate(index,20261021,ROOT/"assets/NotoSans-Regular.ttf")
        Reference.model_validate(reference)
        assert image.tobytes()==second.tobytes() and reference==reference2 and public==public2
        assert reference["status"]=="programmatic" and reference["split"]=="train"
        assert "text" not in public and "kie" not in public


def test_release_blocks_unreviewed_pages_before_writing_files(tmp_path):
    workspace=tmp_path/"workspace";workspace.mkdir()
    (workspace/"annotation-queue.jsonl").write_text(json.dumps({"id":"x","planned_split":"test_a"})+'\n')
    audit=tmp_path/"audit.json"
    audit.write_text(json.dumps({"license_review_complete":True,"near_duplicate_review_complete":True,"coverage_review_complete":True,"approved_ids":["x"],"reviewer":"test-only","evidence":"test fixture"}))
    public=tmp_path/"public";private=tmp_path/"private"
    result=subprocess.run([sys.executable,str(ROOT/"scripts/export_reviewed.py"),"--workspace",str(workspace),"--dataset",str(tmp_path),"--public-output",str(public),"--private-output",str(private),"--split","test_a","--audit",str(audit)],capture_output=True,text=True)
    assert result.returncode != 0 and "Release blocked" in result.stderr
    assert not public.exists() and not private.exists()


def test_schema_rejects_extra_keys_and_numeric_kie_values():
    from pydantic import ValidationError
    from polocrbench.models import Prediction
    with pytest.raises(ValidationError):Prediction(id="x",typo="text")
    with pytest.raises(ValidationError):Prediction(id="x",kie={"amount":12.5})


def test_amueval_export_preserves_manifest_order_and_escapes_lines(tmp_path):
    inputs=tmp_path/"in.jsonl";preds=tmp_path/"pred.jsonl";output=tmp_path/"out.tsv"
    inputs.write_text('{"id":"b"}\n{"id":"a"}\n')
    preds.write_text(json.dumps({"id":"a","text":"line1\nline2\ttab"})+'\n')
    subprocess.run([sys.executable,str(ROOT/"scripts/export_amueval.py"),"--inputs",str(inputs),"--predictions",str(preds),"--output",str(output)],check=True,capture_output=True)
    rows=[json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows)==2 and [r["id"] for r in rows]==["b","a"]
    assert rows[1]["text"]=="line1\nline2\ttab"


def test_amueval_adapter_score_parity_with_local_scorer(monkeypatch):
    import types
    from pydantic import BaseModel
    from polocrbench.evaluate import evaluate
    from polocrbench.models import Prediction
    # Exercise the inspected MetricBase API without claiming remote integration.
    backend=types.ModuleType("metrics.metric_base");backend.MetricBase=BaseModel
    monkeypatch.setitem(sys.modules,"metrics",types.ModuleType("metrics"))
    monkeypatch.setitem(sys.modules,"metrics.metric_base",backend)
    spec=importlib.util.spec_from_file_location("amueval_adapter",ROOT/"scripts/amueval_adapter.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    reference=Reference(id="x",text="Żółć",split="test_a",status="verified",reviewers=["reviewer1","reviewer2"])
    prediction=Prediction(id="x",text="Żółc")
    adapter=module.PolOCRBench(tasks=["A"])
    local=evaluate({"x":reference},{"x":prediction},tasks=["A"])
    assert adapter.calculate([reference.model_dump_json()],[prediction.model_dump_json()])==local["partial_score"]
    with pytest.raises(ValueError):adapter.calculate([reference.model_dump_json()],[Prediction(id="wrong").model_dump_json()])
