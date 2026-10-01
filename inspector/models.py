"""Validated contracts shared by analysis, narrative, charts, and exporters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Language = Literal["en", "zh-CN", "es", "fi"]
VariableRole = Literal["identifier", "numeric", "categorical", "ordinal", "date", "text"]
ReportType = Literal[
    "automatic", "descriptive", "data_quality", "group", "relationships", "change", "time"
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ColumnMeta(StrictModel):
    id: str
    label: str
    role: VariableRole
    role_uncertain: bool = False
    dtype: str
    nonmissing: int
    unique_nonmissing: int
    missing: int
    nonfinite: int = 0
    notes: list[str] = Field(default_factory=list)


class EvidenceFact(StrictModel):
    id: str
    kind: str
    variable_ids: list[str] = Field(default_factory=list)
    group_labels: list[str] = Field(default_factory=list)
    denominator: int | None = None
    values: dict[str, str | int | float | None] = Field(default_factory=dict)
    method: str
    direction: str | None = None
    sentence: str
    allowed_interpretation_codes: list[str] = Field(default_factory=list)


class ChartSpec(StrictModel):
    id: str
    kind: Literal["histogram", "bar", "missingness", "box", "scatter", "date_line", "paired"]
    variable_ids: list[str]
    title: str
    x_label: str
    y_label: str
    valid_n: int
    source_fact_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    sampling: str | None = None


class TableBlock(StrictModel):
    id: str
    title: str
    columns: list[str]
    rows: list[list[str]]
    note: str | None = None


class FigureBlock(StrictModel):
    id: str
    title: str
    caption: str
    alt_text: str
    png: bytes
    source_fact_ids: list[str] = Field(default_factory=list)


class ReportSection(StrictModel):
    id: str
    heading: str
    paragraphs: list[str] = Field(default_factory=list)
    tables: list[TableBlock] = Field(default_factory=list)
    figures: list[FigureBlock] = Field(default_factory=list)


class ReportDocument(StrictModel):
    schema_version: str
    language: Language
    title: str
    subtitle: str
    mode: Literal["template", "ai_assisted"]
    status_note: str
    generated_at_utc: datetime
    sections: list[ReportSection]
    facts: list[EvidenceFact]
    reproducibility: list[str]


class AnalysisResult(StrictModel):
    schema_version: str
    language: Language
    report_type: ReportType
    rows: int
    columns: int
    column_metadata: list[ColumnMeta]
    settings: dict[str, Any]
    parsing_notes: list[str]
    quality: dict[str, Any]
    descriptives: list[dict[str, Any]]
    selected_analyses: dict[str, Any]
    limitations: list[str]
    facts: list[EvidenceFact]
    chart_specs: list[ChartSpec]
    reproducibility: list[str]


class NarrativeBlock(StrictModel):
    section_id: str
    fact_ids: list[str] = Field(default_factory=list, max_length=30)
    interpretation_code: str | None = None
    prose: str = Field(max_length=3000)


class NarrativeResponse(StrictModel):
    language: Language
    blocks: list[NarrativeBlock] = Field(min_length=1, max_length=8)
