"""Auditable local annotation state machine; identities are self-declared."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import Lock
from typing import Literal

from pydantic import Field

from .models import Prediction, StrictModel


class AnnotationAction(StrictModel):
    actor: str = Field(min_length=2, max_length=100)
    action: Literal["save", "submit", "approve", "reject", "exclude"]
    expected_revision: int = Field(ge=0)
    text: str | None = None
    tables: list[str] | None = None
    kie: dict[str, str | None] | None = None
    field_types: dict[str, Literal["text", "date", "amount", "identifier", "address"]] = Field(default_factory=dict)
    note: str = Field(default="", max_length=10000)


class AnnotationStore:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def path(self, sample_id):
        return self.directory / (hashlib.sha256(sample_id.encode()).hexdigest() + ".json")

    def get(self, sample_id):
        path = self.path(sample_id)
        if path.exists():
            return json.loads(path.read_text())
        return {"id": sample_id, "revision": 0, "status": "unstarted", "annotator": None,
                "text": None, "tables": None, "kie": None, "field_types": {}, "reviews": [], "history": []}

    def update(self, sample_id, action):
        with self.lock:
            current = self.get(sample_id)
            if action.expected_revision != current["revision"]:
                raise ValueError("Konflikt wersji: odśwież anotację przed zapisem.")
            actor = action.actor.strip()
            if len(actor) < 2:
                raise ValueError("Podaj identyfikator anotatora lub recenzenta.")
            timestamp = datetime.now(timezone.utc).isoformat()
            if action.action in ("save", "submit"):
                if current["status"] in ("submitted", "reviewed_once", "verified"):
                    raise ValueError("Przed edycją przesłanej anotacji recenzent musi zwrócić ją do poprawy.")
                Prediction(id=sample_id, text=action.text, tables=action.tables, kie=action.kie)
                if action.text is None and action.tables is None and action.kie is None:
                    raise ValueError("Brak anotacji dla któregokolwiek podzadania.")
                if action.action == "submit" and action.text is not None and not action.text.strip() and not action.note.strip():
                    raise ValueError("Pusta transkrypcja wymaga uwagi wyjaśniającej, dlaczego strona nie zawiera czytelnego tekstu.")
                if action.kie is not None and set(action.field_types) != set(action.kie):
                    raise ValueError("Typy pól KIE muszą odpowiadać kluczom KIE.")
                if action.tables:
                    from .metrics import table_tree
                    for table in action.tables:
                        table_tree(table)
                current.update(text=action.text, tables=action.tables, kie=action.kie,
                               field_types=action.field_types, annotator=actor, reviews=[],
                               status="submitted" if action.action == "submit" else "draft")
            elif action.action == "approve":
                if current["status"] not in ("submitted", "reviewed_once"):
                    raise ValueError("Do przeglądu można przyjąć tylko przesłaną anotację.")
                identities = [current["annotator"], *[r["actor"] for r in current["reviews"]]]
                if actor.casefold() in [identity.strip().casefold() for identity in identities if identity]:
                    raise ValueError("Dwa przeglądy muszą wykonać różne osoby, inne niż autor anotacji.")
                current["reviews"].append({"actor": actor, "revision_reviewed": current["revision"], "at": timestamp, "note": action.note})
                current["status"] = "verified" if len(current["reviews"]) >= 2 else "reviewed_once"
            elif action.action == "reject":
                if not action.note.strip():
                    raise ValueError("Opisz, co należy poprawić.")
                current.update(status="draft", reviews=[])
            elif action.action == "exclude":
                if not action.note.strip():
                    raise ValueError("Podaj powód wykluczenia strony.")
                current.update(status="excluded", reviews=[])
            current["revision"] += 1
            current["updated_at"] = timestamp
            current["history"].append({"action": action.action, "actor": actor, "at": timestamp,
                                       "revision": current["revision"], "note": action.note})
            # Preserve full previous revisions; changes invalidate prior approvals.
            revisions = self.directory / "revisions"
            revisions.mkdir(exist_ok=True)
            name = self.path(sample_id).stem
            snapshot = revisions / f"{name}-{current['revision']:05d}.json"
            snapshot.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n")
            path = self.path(sample_id)
            temp = path.with_suffix(".part")
            temp.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n")
            temp.replace(path)
            return current
