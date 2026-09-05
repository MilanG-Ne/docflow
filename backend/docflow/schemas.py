import hashlib
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Text80 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def safe_xml_text(cls, value):
        if isinstance(value, str) and re.search(
            r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value
        ):
            raise ValueError("Text contains characters that cannot appear in a document")
        return value


class LineItem(InputModel):
    description: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    quantity: Decimal = Field(gt=0, le=1000, max_digits=6, decimal_places=2)
    unit_cents: int = Field(ge=0, le=10_000_000, strict=True)

    @property
    def total_cents(self) -> int:
        return int((self.quantity * self.unit_cents).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class ProposalContent(InputModel):
    title: Text80
    client_name: Text80
    client_contact: Text80
    summary: Annotated[str, StringConstraints(min_length=20, max_length=2000)]
    deliverables: Annotated[str, StringConstraints(min_length=10, max_length=3000)]
    timeline: Annotated[str, StringConstraints(min_length=5, max_length=500)]
    assumptions: Annotated[str, StringConstraints(max_length=1500)] = ""
    currency: Literal["EUR", "USD", "GBP"] = "EUR"
    line_items: list[LineItem] = Field(min_length=1, max_length=20)

    @property
    def total_cents(self) -> int:
        return sum(item.total_cents for item in self.line_items)

    def fingerprint(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


class NewRevision(InputModel):
    expected_number: int = Field(ge=1)
    content: ProposalContent


class ReviewInput(InputModel):
    decision: Literal["approved", "changes_requested"]
    comment: Annotated[str, StringConstraints(min_length=5, max_length=1500)]
    content_hash: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


class LoginInput(InputModel):
    email: Annotated[str, StringConstraints(min_length=3, max_length=254)]
    password: Annotated[str, StringConstraints(min_length=1, max_length=200)]
