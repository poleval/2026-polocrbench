from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Prediction(StrictModel):
    id: str = Field(min_length=1)
    text: str | None = None
    tables: list[str] | None = None
    kie: dict[str, str | None] | None = None


class Reference(Prediction):
    status: Literal["preannotation", "verified", "programmatic"]
    split: Literal["train", "test_a", "test_b", "smoke"]
    reviewers: list[str] = Field(default_factory=list)
    field_types: dict[str, Literal["text", "date", "amount", "identifier", "address"]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def review_policy(self):
        if self.status == "verified" and self.split in ("test_a", "test_b") and len(set(self.reviewers)) < 2:
            raise ValueError("Test references require two distinct reviewers")
        if self.status == "programmatic" and self.split in ("test_a", "test_b"):
            raise ValueError("Programmatic synthetic references are training/smoke material only")
        if self.text is None and self.tables is None and self.kie is None:
            raise ValueError("A reference must annotate at least one subtask")
        if self.kie is not None and set(self.field_types) != set(self.kie):
            raise ValueError("KIE field_types must match the annotated field schema")
        return self
