import pytest
from pydantic import ValidationError

from polocrbench.annotation import AnnotationAction, AnnotationStore
from polocrbench.evaluate import evaluate, load_rows
from polocrbench.metrics import kie_counts, normalize_field, normalize_text, teds
from polocrbench.models import Prediction, Reference


def ref(**kwargs):
    return Reference(id="x", split="smoke", status="programmatic", **kwargs)


def test_perfect_all_tasks():
    reference = ref(text="# Żółć\n\nZażółć gęślą jaźń.", tables=["<table><tr><td>ą</td></tr></table>"], kie={"date":"21.10.2026"}, field_types={"date":"date"})
    pred = Prediction(id="x", text=reference.text, tables=reference.tables, kie={"date":"2026-10-21"})
    result = evaluate({"x":reference}, {"x":pred})
    assert result["aggregate"] == 1
    assert not result["eligible_for_official_ranking"]


def test_missing_prediction_is_penalized_and_extra_ids_rejected():
    reference = ref(text="Zażółć gęślą jaźń")
    result = evaluate({"x":reference}, {}, tasks=["A"])
    assert result["metrics"]["cer"] == 1
    assert result["aggregate"] is None
    with pytest.raises(ValueError, match="Unknown"):
        evaluate({"x":reference}, {"other":Prediction(id="other")}, tasks=["A"])


def test_cer_above_one_not_hidden_by_score_clamp():
    result = evaluate({"x":ref(text="a")}, {"x":Prediction(id="x",text="abcdef")}, tasks=["A"])
    assert result["metrics"]["cer"] == 5
    assert result["subtask_scores"]["A"] == 0


def test_unicode_normalization_preserves_case_and_diacritics():
    assert normalize_text("\u007a\u0307ółć\n„tekst”") == 'żółć "tekst"'
    assert normalize_text("ŁÓDŹ") != normalize_text("lodz")


def test_teds_structure_vs_content_and_spans():
    a = "<table><tr><th>Kwota</th><td>10</td></tr></table>"
    b = "<table><tr><th>Kwota</th><td>90</td></tr></table>"
    c = "<table><tr><th colspan='2'>Kwota</th></tr></table>"
    assert teds(a,a) == 1
    assert 0 < teds(a,b) < 1
    assert teds(a,b,True) == 1
    assert teds(a,c,True) < 1
    assert teds(a,"<p>oops</p>") == 0
    assert teds(a,"") == 0


def test_extra_tables_cannot_be_ignored():
    table = "<table><tr><td>a</td></tr></table>"
    result = evaluate({"x":ref(tables=[table])},{"x":Prediction(id="x",tables=[table,table])},tasks=["B"])
    assert result["metrics"]["teds"] == .5


def test_field_normalization_and_hallucinated_keys():
    assert normalize_field("1 234,50 zł","amount") == "1234.5"
    assert normalize_field("-1.234,50","amount") == "-1234.5"
    assert normalize_field("PL 123-456","identifier") == "PL123456"
    assert normalize_field("31.02.2026","date") != "2026-02-28"
    assert kie_counts({"a":"1"},{"a":"2","hallucinated":"x"},{}) == {"tp":0,"fp":2,"fn":1}


def test_unverified_references_blocked_and_distinct_reviews_required():
    with pytest.raises(ValidationError):
        Reference(id="x",text="a",split="test_b",status="verified",reviewers=["same","same"])
    pending = Reference(id="x",text="a",split="test_a",status="preannotation")
    with pytest.raises(ValueError,match="Unverified"):
        evaluate({"x":pending},{},tasks=["A"])
    assert evaluate({"x":pending},{},tasks=["A"],allow_provisional=True)["provisional"]


def test_duplicate_ids_rejected(tmp_path):
    file=tmp_path/"pred.jsonl"
    file.write_text('{"id":"x","text":"a"}\n{"id":"x","text":"b"}\n')
    with pytest.raises(ValueError,match="Duplicate"):
        load_rows(file,Prediction)


def test_review_state_machine_and_optimistic_lock(tmp_path):
    store=AnnotationStore(tmp_path)
    row=store.update("page",AnnotationAction(actor="author",action="submit",expected_revision=0,text="Zażółć"))
    with pytest.raises(ValueError,match="różne osoby"):
        store.update("page",AnnotationAction(actor="author",action="approve",expected_revision=1))
    row=store.update("page",AnnotationAction(actor="reviewer1",action="approve",expected_revision=1))
    with pytest.raises(ValueError):
        store.update("page",AnnotationAction(actor="reviewer1",action="approve",expected_revision=2))
    row=store.update("page",AnnotationAction(actor="reviewer2",action="approve",expected_revision=2))
    assert row["status"]=="verified"
    with pytest.raises(ValueError,match="Konflikt"):
        store.update("page",AnnotationAction(actor="author",action="save",expected_revision=0,text="edited"))
    row=store.update("page",AnnotationAction(actor="reviewer1",action="reject",expected_revision=3,note="Fix typo"))
    assert row["status"]=="draft" and not row["reviews"]
