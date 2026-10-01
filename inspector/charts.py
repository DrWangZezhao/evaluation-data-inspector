"""Deterministic chart selection and thread-safe Matplotlib rendering."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from threading import Lock

import matplotlib

matplotlib.use("Agg")
from matplotlib import font_manager
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from analysis import categorical_summary
from .models import ChartSpec, ColumnMeta, Language


TEAL = "#167D7F"
LIGHT_TEAL = "#86C5C5"
FONT_PATH = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "NotoSansCJKsc-Regular.otf"
FONT = font_manager.FontProperties(fname=str(FONT_PATH)) if FONT_PATH.exists() else font_manager.FontProperties(family="sans-serif")
_RENDER_LOCK = Lock()


def compatible_chart_kinds(roles: list[ColumnMeta]) -> list[str]:
    kinds = ["missingness"]
    if any(column.role == "numeric" for column in roles):
        kinds.append("histogram")
    if any(column.role in {"categorical", "ordinal"} for column in roles):
        kinds.append("bar")
    return kinds


def select_charts(
    data: pd.DataFrame,
    columns: list[ColumnMeta],
    *,
    depth: str = "standard",
    primary: ChartSpec | None = None,
    manual_kind: str | None = None,
) -> tuple[list[ChartSpec], list[str]]:
    budget = {"brief": 3, "standard": 5, "detailed": 8}.get(depth, 5)
    selected: list[ChartSpec] = []
    by_id = {column.id: column for column in columns}
    if primary:
        selected.append(primary)
    missing_n = sum(column.missing for column in columns)
    if missing_n and len(selected) < budget and not any(spec.kind == "missingness" for spec in selected):
        selected.append(ChartSpec(id="chart_missingness", kind="missingness", variable_ids=[column.id for column in columns], title="Missingness by variable", x_label="Missing (%)", y_label="Variable", valid_n=len(data)))
    candidates: list[ChartSpec] = []
    for column in columns:
        if column.role == "numeric":
            candidates.append(ChartSpec(id=f"chart_hist_{column.id}", kind="histogram", variable_ids=[column.id], title=f"Distribution of {column.label}", x_label=column.label, y_label="Count", valid_n=column.nonmissing - column.nonfinite))
        elif column.role in {"categorical", "ordinal"} and column.unique_nonmissing <= 20:
            candidates.append(ChartSpec(id=f"chart_bar_{column.id}", kind="bar", variable_ids=[column.id], title=f"Frequency of {column.label}", x_label=column.label, y_label="Count", valid_n=column.nonmissing))
    if manual_kind:
        candidates.sort(key=lambda spec: spec.kind != manual_kind)
    existing = {spec.id for spec in selected}
    for candidate in candidates:
        if len(selected) >= budget:
            break
        if candidate.id not in existing:
            selected.append(candidate)
            existing.add(candidate.id)
    omitted = [by_id[spec.variable_ids[0]].label for spec in candidates if spec.id not in existing and spec.variable_ids[0] in by_id]
    return selected, omitted


def _style_figure(fig: Figure) -> None:
    fig.patch.set_facecolor("white")
    for ax in fig.axes:
        ax.set_facecolor("white")
        ax.grid(axis="y", color="#DCE4E4", linewidth=0.7, alpha=0.8)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for text in [ax.title, ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()]:
            text.set_fontproperties(FONT)


def render_chart(spec: ChartSpec, data: pd.DataFrame, columns: list[ColumnMeta]) -> bytes:
    id_to_label = {column.id: column.label for column in columns}
    labels = [id_to_label[column_id] for column_id in spec.variable_ids if column_id in id_to_label]
    with _RENDER_LOCK:
        fig = Figure(figsize=(7.2, 4.2), dpi=140, layout="constrained")
        ax = fig.subplots()
        if spec.kind == "missingness":
            plotted = [(column.label, column.missing / max(1, len(data)) * 100) for column in columns if column.missing]
            plotted = plotted[:30]
            ax.barh([label for label, _ in reversed(plotted)], [value for _, value in reversed(plotted)], color=TEAL)
            ax.set_xlim(left=0)
        elif spec.kind == "histogram":
            values = pd.to_numeric(data[labels[0]], errors="coerce").astype(float)
            values = values[np.isfinite(values)]
            bins = min(20, max(5, int(np.sqrt(max(1, len(values))))))
            ax.hist(values, bins=bins, color=TEAL, edgecolor="white")
        elif spec.kind == "bar":
            summary = categorical_summary(data, labels[0])
            categories = summary["categories"]
            ax.bar([str(row["label"]) for row in categories], [int(row["count"]) for row in categories], color=TEAL)
            ax.tick_params(axis="x", rotation=35)
        elif spec.kind == "box":
            outcome, group = labels
            values = pd.to_numeric(data[outcome], errors="coerce").astype(float)
            group_order = list(pd.unique(data.loc[data[group].notna(), group]))
            arrays = [values[(data[group] == name) & np.isfinite(values)].to_numpy() for name in group_order]
            ax.boxplot(arrays, tick_labels=[str(name) for name in group_order], patch_artist=True, boxprops={"facecolor": LIGHT_TEAL})
        elif spec.kind == "scatter":
            first, second = labels
            x = pd.to_numeric(data[first], errors="coerce").astype(float)
            y = pd.to_numeric(data[second], errors="coerce").astype(float)
            valid = pd.DataFrame({"x": x, "y": y})[np.isfinite(x) & np.isfinite(y)]
            if len(valid) > 5000:
                valid = valid.sample(5000, random_state=20261001)
            ax.scatter(valid["x"], valid["y"], s=18, alpha=0.65, color=TEAL)
        elif spec.kind == "date_line":
            date_label, outcome = labels
            dates = pd.to_datetime(data[date_label], errors="coerce")
            values = pd.to_numeric(data[outcome], errors="coerce").astype(float)
            valid = pd.DataFrame({"date": dates, "value": values})[dates.notna() & np.isfinite(values)]
            grouped = valid.groupby("date")["value"].mean().sort_index()
            ax.plot(grouped.index, grouped.values, marker="o", color=TEAL)
            fig.autofmt_xdate()
        elif spec.kind == "paired":
            pre, post = labels
            before = pd.to_numeric(data[pre], errors="coerce").astype(float)
            after = pd.to_numeric(data[post], errors="coerce").astype(float)
            valid = np.isfinite(before) & np.isfinite(after)
            ax.plot([0, 1], [float(before[valid].mean()), float(after[valid].mean())], marker="o", linewidth=2.5, color=TEAL)
            ax.set_xticks([0, 1], [pre, post])
        ax.set_title(spec.title)
        ax.set_xlabel(spec.x_label)
        ax.set_ylabel(spec.y_label)
        _style_figure(fig)
        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=140, metadata={"Software": "Evaluation Data Inspector"})
        fig.clear()
        return buffer.getvalue()
