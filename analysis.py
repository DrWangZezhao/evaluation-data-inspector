"""Reusable validation and statistical analysis for Evaluation Data Inspector."""

from __future__ import annotations

from io import BytesIO

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_numeric_dtype


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 250


class AnalysisError(ValueError):
    """Raised when data cannot be safely analysed as requested."""


def validate_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Validate basic dataset shape and return the original data frame.

    Limits are intentionally conservative for a small public demonstration app.
    They keep an accidental large upload from monopolising the single process.
    """

    if not isinstance(data, pd.DataFrame):
        raise AnalysisError("The supplied data is not a table.")
    if data.empty or data.shape[0] == 0:
        raise AnalysisError("The CSV must contain at least one data row.")
    if data.shape[1] == 0:
        raise AnalysisError("The CSV must contain at least one column.")
    if data.shape[0] > MAX_ROWS:
        raise AnalysisError(f"The dataset exceeds the {MAX_ROWS:,}-row demo limit.")
    if data.shape[1] > MAX_COLUMNS:
        raise AnalysisError(f"The dataset exceeds the {MAX_COLUMNS}-column demo limit.")
    if any(not str(column).strip() for column in data.columns):
        raise AnalysisError("Every column must have a non-empty name.")
    return data


def read_csv_bytes(content: bytes, *, max_bytes: int = MAX_UPLOAD_BYTES) -> pd.DataFrame:
    """Parse in-memory CSV bytes and convert predictable parser failures to safe errors."""

    if not isinstance(content, bytes):
        raise AnalysisError("The uploaded content must be a CSV file.")
    if not content:
        raise AnalysisError("The uploaded CSV is empty.")
    if len(content) > max_bytes:
        raise AnalysisError(f"The CSV exceeds the {max_bytes // (1024 * 1024)} MB upload limit.")
    if b"\x00" in content[:4096]:
        raise AnalysisError("The upload appears to be a binary file, not a CSV.")

    try:
        data = pd.read_csv(BytesIO(content))
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise AnalysisError(
            "The file could not be read as a UTF-8 CSV. Check its encoding and row structure."
        ) from exc
    except ValueError as exc:
        raise AnalysisError("The CSV contains unsupported or malformed data.") from exc

    return validate_dataframe(data)


def numeric_columns(data: pd.DataFrame) -> list[str]:
    """Return numeric column names, excluding booleans."""

    validate_dataframe(data)
    return [
        str(column)
        for column in data.columns
        if is_numeric_dtype(data[column]) and not is_bool_dtype(data[column])
    ]


def dataset_summary(data: pd.DataFrame) -> dict[str, object]:
    """Return dimensions, schema, missing counts, and duplicate-row count."""

    validate_dataframe(data)
    return {
        "rows": int(data.shape[0]),
        "columns": int(data.shape[1]),
        "variable_names": [str(column) for column in data.columns],
        "data_types": {str(column): str(dtype) for column, dtype in data.dtypes.items()},
        "missing_values": {
            str(column): int(count) for column, count in data.isna().sum().items()
        },
        "duplicate_rows": int(data.duplicated().sum()),
    }


def descriptive_statistics(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate N, mean, sample SD, minimum, and maximum for numeric variables."""

    columns = numeric_columns(data)
    if not columns:
        return pd.DataFrame(columns=["variable", "N", "mean", "std", "min", "max"])

    rows = []
    for column in columns:
        series = data[column].dropna()
        rows.append(
            {
                "variable": column,
                "N": int(series.count()),
                "mean": float(series.mean()) if not series.empty else np.nan,
                "std": float(series.std(ddof=1)) if len(series) > 1 else np.nan,
                "min": float(series.min()) if not series.empty else np.nan,
                "max": float(series.max()) if not series.empty else np.nan,
            }
        )
    return pd.DataFrame(rows)


def missingness(data: pd.DataFrame) -> pd.DataFrame:
    """Return missing-value count and percentage for every variable."""

    validate_dataframe(data)
    counts = data.isna().sum()
    result = pd.DataFrame(
        {
            "variable": [str(column) for column in data.columns],
            "missing_count": counts.astype(int).to_numpy(),
            "missing_percent": (counts / len(data) * 100).to_numpy(dtype=float),
        }
    )
    return result


def _validate_analysis_columns(data: pd.DataFrame, outcome: str, group: str) -> None:
    validate_dataframe(data)
    if outcome not in data.columns:
        raise AnalysisError(f"Outcome variable '{outcome}' was not found.")
    if group not in data.columns:
        raise AnalysisError(f"Grouping variable '{group}' was not found.")
    if outcome == group:
        raise AnalysisError("Outcome and grouping variables must be different.")
    if not is_numeric_dtype(data[outcome]) or is_bool_dtype(data[outcome]):
        raise AnalysisError("The selected outcome variable must be numeric.")


def group_statistics(data: pd.DataFrame, outcome: str, group: str) -> pd.DataFrame:
    """Calculate descriptive outcome statistics for each non-missing group."""

    _validate_analysis_columns(data, outcome, group)
    valid = data[[outcome, group]].dropna()
    if valid.empty:
        raise AnalysisError("No complete outcome/group observations are available.")
    if valid[group].nunique() < 1:
        raise AnalysisError("The grouping variable has no valid groups.")

    result = (
        valid.groupby(group, sort=False, observed=True)[outcome]
        .agg(N="count", mean="mean", std="std", min="min", max="max")
        .reset_index()
        .rename(columns={group: "group"})
    )
    result["N"] = result["N"].astype(int)
    return result


def cohens_d(data: pd.DataFrame, outcome: str, group: str) -> dict[str, object]:
    """Calculate the two-group mean difference and pooled-SD Cohen's d.

    The difference and effect-size direction are ``first group - second group``.
    Groups follow their first appearance in the complete-case data. The pooled
    standard deviation uses the conventional sample-variance formula.
    """

    _validate_analysis_columns(data, outcome, group)
    valid = data[[outcome, group]].dropna()
    groups = list(pd.unique(valid[group]))
    if len(groups) != 2:
        raise AnalysisError("Cohen's d requires exactly two valid groups.")

    first = valid.loc[valid[group] == groups[0], outcome].astype(float)
    second = valid.loc[valid[group] == groups[1], outcome].astype(float)
    if len(first) < 2 or len(second) < 2:
        raise AnalysisError("Each group needs at least two valid outcome values.")

    first_variance = first.var(ddof=1)
    second_variance = second.var(ddof=1)
    pooled_variance = (
        (len(first) - 1) * first_variance + (len(second) - 1) * second_variance
    ) / (len(first) + len(second) - 2)
    if not np.isfinite(pooled_variance) or pooled_variance <= 0:
        raise AnalysisError("Cohen's d is undefined because the pooled variance is zero.")

    mean_difference = float(first.mean() - second.mean())
    return {
        "group_1": groups[0],
        "group_2": groups[1],
        "n_1": int(len(first)),
        "n_2": int(len(second)),
        "mean_difference": mean_difference,
        "cohens_d": float(mean_difference / np.sqrt(pooled_variance)),
    }
