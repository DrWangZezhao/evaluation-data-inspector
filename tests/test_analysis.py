"""Tests for the reusable Evaluation Data Inspector analysis layer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis import (
    AnalysisError,
    cohens_d,
    dataset_summary,
    descriptive_statistics,
    group_statistics,
    missingness,
    read_csv_bytes,
    validate_dataframe,
)


@pytest.fixture
def evaluation_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": [1, 2, 3, 4, 3],
            "group": ["Intervention", "Intervention", "Comparison", "Comparison", "Comparison"],
            "score": [80.0, 90.0, 70.0, np.nan, 70.0],
            "comment": ["a", None, "b", "c", "b"],
        }
    )


def test_dataset_summary_reports_shape_schema_missing_and_duplicates(
    evaluation_data: pd.DataFrame,
) -> None:
    summary = dataset_summary(evaluation_data)

    assert summary["rows"] == 5
    assert summary["columns"] == 4
    assert summary["variable_names"] == ["participant_id", "group", "score", "comment"]
    assert summary["data_types"]["score"] == "float64"
    assert summary["missing_values"] == {
        "participant_id": 0,
        "group": 0,
        "score": 1,
        "comment": 1,
    }
    assert summary["duplicate_rows"] == 1


def test_missingness_reports_counts_and_percentages(evaluation_data: pd.DataFrame) -> None:
    result = missingness(evaluation_data).set_index("variable")

    assert result.loc["score", "missing_count"] == 1
    assert result.loc["score", "missing_percent"] == pytest.approx(20.0)
    assert result.loc["group", "missing_percent"] == pytest.approx(0.0)


def test_descriptive_statistics_use_non_missing_n_and_sample_sd() -> None:
    data = pd.DataFrame({"score": [1.0, 2.0, 3.0, np.nan], "label": ["a", "b", "c", "d"]})

    result = descriptive_statistics(data).set_index("variable")

    assert result.loc["score", "N"] == 3
    assert result.loc["score", "mean"] == pytest.approx(2.0)
    assert result.loc["score", "std"] == pytest.approx(1.0)
    assert result.loc["score", "min"] == pytest.approx(1.0)
    assert result.loc["score", "max"] == pytest.approx(3.0)


def test_group_statistics_drop_incomplete_rows() -> None:
    data = pd.DataFrame(
        {"group": ["A", "A", "B", "B", None], "score": [1.0, 3.0, 5.0, np.nan, 99.0]}
    )

    result = group_statistics(data, "score", "group").set_index("group")

    assert result.loc["A", "N"] == 2
    assert result.loc["A", "mean"] == pytest.approx(2.0)
    assert result.loc["B", "N"] == 1
    assert result.loc["B", "mean"] == pytest.approx(5.0)


def test_cohens_d_uses_pooled_sample_standard_deviation() -> None:
    data = pd.DataFrame(
        {"group": ["A", "A", "A", "B", "B", "B"], "score": [2.0, 4.0, 6.0, 1.0, 2.0, 3.0]}
    )

    result = cohens_d(data, "score", "group")
    expected_pooled_sd = np.sqrt(((3 - 1) * 4.0 + (3 - 1) * 1.0) / (3 + 3 - 2))

    assert result["group_1"] == "A"
    assert result["group_2"] == "B"
    assert result["mean_difference"] == pytest.approx(2.0)
    assert result["cohens_d"] == pytest.approx(2.0 / expected_pooled_sd)


@pytest.mark.parametrize(
    "payload",
    [b"", b"\x00\x01binary", b'one,two\n"unterminated,3\n'],
)
def test_invalid_csv_inputs_raise_safe_errors(payload: bytes) -> None:
    with pytest.raises(AnalysisError):
        read_csv_bytes(payload)


def test_valid_csv_is_parsed() -> None:
    result = read_csv_bytes(b"group,score\nA,10\nB,20\n")
    assert result.shape == (2, 2)
    assert result["score"].tolist() == [10, 20]


def test_empty_dataframe_is_rejected() -> None:
    with pytest.raises(AnalysisError, match="at least one data row"):
        validate_dataframe(pd.DataFrame(columns=["score"]))


def test_group_analysis_rejects_non_numeric_outcome() -> None:
    data = pd.DataFrame({"group": ["A", "B"], "outcome": ["high", "low"]})
    with pytest.raises(AnalysisError, match="must be numeric"):
        group_statistics(data, "outcome", "group")


def test_cohens_d_requires_exactly_two_groups() -> None:
    data = pd.DataFrame({"group": ["A", "A", "B", "B", "C", "C"], "score": range(6)})
    with pytest.raises(AnalysisError, match="exactly two"):
        cohens_d(data, "score", "group")


def test_cohens_d_rejects_zero_pooled_variance() -> None:
    data = pd.DataFrame({"group": ["A", "A", "B", "B"], "score": [1.0, 1.0, 2.0, 2.0]})
    with pytest.raises(AnalysisError, match="pooled variance is zero"):
        cohens_d(data, "score", "group")
