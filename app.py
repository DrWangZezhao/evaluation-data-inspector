"""Streamlit interface for Evaluation Data Inspector."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from analysis import (
    AnalysisError,
    cohens_d,
    dataset_summary,
    descriptive_statistics,
    group_statistics,
    missingness,
    numeric_columns,
    read_csv_bytes,
)


APP_DIR = Path(__file__).resolve().parent
SAMPLE_PATH = APP_DIR / "sample_data" / "sample_evaluation_data.csv"
NO_GROUP = "No grouping variable"


def load_data() -> tuple[pd.DataFrame, str]:
    """Render source controls and load data without writing uploaded content to disk."""

    st.sidebar.header("Data source")
    source = st.sidebar.radio(
        "Choose a dataset",
        ("Synthetic sample", "Upload CSV"),
        help="The included sample is entirely synthetic.",
    )

    if source == "Synthetic sample":
        content = SAMPLE_PATH.read_bytes()
        st.sidebar.download_button(
            "Download sample CSV",
            data=content,
            file_name=SAMPLE_PATH.name,
            mime="text/csv",
        )
        return read_csv_bytes(content), "Synthetic sample dataset"

    upload = st.sidebar.file_uploader("Upload an evaluation dataset", type=("csv",))
    if upload is None:
        st.info("Upload a CSV from the sidebar to begin, or choose the synthetic sample.")
        st.stop()
    return read_csv_bytes(upload.getvalue()), upload.name


def outcome_histogram(data: pd.DataFrame, outcome: str) -> pd.DataFrame:
    """Prepare an evenly binned histogram for Streamlit's native bar chart."""

    values = data[outcome].dropna().to_numpy(dtype=float)
    if values.size == 0:
        return pd.DataFrame(columns=["range", "count"])
    bin_count = min(20, max(5, int(np.sqrt(values.size))))
    counts, edges = np.histogram(values, bins=bin_count)
    labels = [f"{left:.1f}–{right:.1f}" for left, right in zip(edges[:-1], edges[1:])]
    return pd.DataFrame({"range": labels, "count": counts}).set_index("range")


def render_overview(data: pd.DataFrame) -> None:
    """Render dimensions, schema, duplicate count, and a data preview."""

    summary = dataset_summary(data)
    metric_columns = st.columns(3)
    metric_columns[0].metric("Rows", f"{summary['rows']:,}")
    metric_columns[1].metric("Columns", summary["columns"])
    metric_columns[2].metric("Duplicate rows", summary["duplicate_rows"])

    schema = pd.DataFrame(
        {
            "variable": summary["variable_names"],
            "inferred_type": [
                summary["data_types"][name] for name in summary["variable_names"]
            ],
            "missing_count": [
                summary["missing_values"][name] for name in summary["variable_names"]
            ],
        }
    )
    st.subheader("Variables and inferred types")
    st.dataframe(schema, hide_index=True, width="stretch")
    st.subheader("Preview")
    st.dataframe(data.head(20), hide_index=True, width="stretch")


def render_numeric_summary(data: pd.DataFrame) -> None:
    """Render numeric descriptive statistics."""

    st.subheader("Numeric descriptive statistics")
    statistics = descriptive_statistics(data)
    if statistics.empty:
        st.info("This dataset has no numeric variables to summarise.")
        return
    st.dataframe(
        statistics,
        hide_index=True,
        width="stretch",
        column_config={
            "mean": st.column_config.NumberColumn(format="%.2f"),
            "std": st.column_config.NumberColumn("SD", format="%.2f"),
            "min": st.column_config.NumberColumn(format="%.2f"),
            "max": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def render_missingness(data: pd.DataFrame) -> None:
    """Render missingness table and bar chart."""

    st.subheader("Missingness by variable")
    table = missingness(data)
    st.dataframe(
        table,
        hide_index=True,
        width="stretch",
        column_config={
            "missing_percent": st.column_config.NumberColumn("Missing (%)", format="%.1f")
        },
    )
    st.bar_chart(table.set_index("variable")["missing_count"], x_label="Variable", y_label="Missing rows")


def render_group_comparison(data: pd.DataFrame) -> None:
    """Render interactive outcome and optional group analyses."""

    st.subheader("Outcome exploration")
    outcomes = numeric_columns(data)
    if not outcomes:
        st.info("A numeric outcome variable is required for this analysis.")
        return

    outcome = st.selectbox("Numeric outcome variable", outcomes)
    eligible_groups = [
        str(column)
        for column in data.columns
        if str(column) != outcome and 2 <= data[column].nunique(dropna=True) <= 20
    ]
    grouping = st.selectbox(
        "Optional categorical grouping variable",
        [NO_GROUP, *eligible_groups],
        help="Columns with 2–20 observed categories are offered as grouping variables.",
    )

    st.caption(f"Distribution of {outcome}")
    st.bar_chart(outcome_histogram(data, outcome), x_label=outcome, y_label="Count")

    if grouping == NO_GROUP:
        return

    try:
        grouped = group_statistics(data, outcome, grouping)
        st.subheader("Statistics by group")
        st.dataframe(
            grouped,
            hide_index=True,
            width="stretch",
            column_config={
                "mean": st.column_config.NumberColumn(format="%.2f"),
                "std": st.column_config.NumberColumn("SD", format="%.2f"),
                "min": st.column_config.NumberColumn(format="%.2f"),
                "max": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.bar_chart(grouped.set_index("group")["mean"], x_label=grouping, y_label=f"Mean {outcome}")

        if len(grouped) == 2:
            effect = cohens_d(data, outcome, grouping)
            first, second = effect["group_1"], effect["group_2"]
            st.subheader("Two-group comparison")
            difference_column, effect_column = st.columns(2)
            difference_column.metric(
                f"Mean difference ({first} − {second})", f"{effect['mean_difference']:.2f}"
            )
            effect_column.metric("Cohen's d", f"{effect['cohens_d']:.3f}")
            st.caption(
                "Cohen's d uses the pooled sample standard deviation. Its sign follows the "
                "displayed group order; no causal interpretation is implied."
            )
        else:
            st.info("Cohen's d is shown only when exactly two valid groups are present.")
    except AnalysisError as exc:
        st.warning(str(exc))


def main() -> None:
    """Run the application."""

    st.set_page_config(page_title="Evaluation Data Inspector", page_icon="📊", layout="wide")
    st.title("Evaluation Data Inspector")
    st.write(
        "Inspect the structure, completeness, and descriptive results of an evaluation dataset."
    )
    st.info(
        "Privacy: this demonstration application processes uploads in memory for the active "
        "session and does not intentionally persist uploaded datasets."
    )

    try:
        data, source_name = load_data()
    except AnalysisError as exc:
        st.error(str(exc))
        st.stop()
    except OSError:
        st.error("The synthetic sample dataset is temporarily unavailable.")
        st.stop()

    st.caption(f"Current source: {source_name}")
    overview_tab, statistics_tab, missingness_tab, comparison_tab = st.tabs(
        ("Dataset overview", "Descriptive statistics", "Missingness", "Group comparison")
    )
    with overview_tab:
        render_overview(data)
    with statistics_tab:
        render_numeric_summary(data)
    with missingness_tab:
        render_missingness(data)
    with comparison_tab:
        render_group_comparison(data)


if __name__ == "__main__":
    main()
