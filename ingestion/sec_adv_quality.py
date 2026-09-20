"""Compact quality profiling for normalized SEC/IAPD adviser firm data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUALITY_REPORT_PATH = PROJECT_ROOT / "reports" / "sec_adv_ingestion_quality.md"


def sec_adv_quality_columns() -> list[str]:
    """Return the normalized columns used by the quality profile."""
    return [
        "firm_crd_number",
        "firm_name",
        "regulatory_aum",
        "registration_state",
        "source_type",
        "source_file",
    ]


def profile_sec_adv_dataset(df: pd.DataFrame) -> dict[str, object]:
    """Calculate completeness, state, source, and top-firm metrics."""
    missing_columns = [column for column in sec_adv_quality_columns() if column not in df.columns]
    if missing_columns:
        raise ValueError(f"SEC ADV dataset is missing quality columns: {', '.join(missing_columns)}")

    crd = _clean_string(df["firm_crd_number"])
    names = _clean_string(df["firm_name"])
    states = _clean_string(df["registration_state"])
    source_types = _clean_string(df["source_type"])
    aum = pd.to_numeric(df["regulatory_aum"], errors="coerce")

    top_firms = df.assign(regulatory_aum=aum).sort_values(
        "regulatory_aum", ascending=False, na_position="last", kind="stable"
    ).head(10)

    return {
        "row_count": len(df),
        "unique_firm_crd_number_count": int(crd.nunique(dropna=True)),
        "missing_firm_crd_number_count": int(crd.isna().sum()),
        "missing_firm_name_count": int(names.isna().sum()),
        "missing_regulatory_aum_count": int(aum.isna().sum()),
        "registration_state_counts": {
            str(key): int(value)
            for key, value in states.fillna("(missing)").value_counts().sort_index().items()
        },
        "top_firms_by_regulatory_aum": [
            {
                "firm_crd_number": _display_value(row.firm_crd_number),
                "firm_name": _display_value(row.firm_name),
                "regulatory_aum": None if pd.isna(row.regulatory_aum) else float(row.regulatory_aum),
            }
            for row in top_firms.itertuples(index=False)
        ],
        "source_type_breakdown": {
            str(key): int(value)
            for key, value in source_types.fillna("(missing)").value_counts().sort_index().items()
        },
    }


def write_sec_adv_quality_report(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
) -> Path:
    """Write a Markdown quality report and return its path."""
    path = Path(output_path) if output_path is not None else DEFAULT_QUALITY_REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = profile_sec_adv_dataset(df)
    source_types = profile["source_type_breakdown"]
    is_sample = set(source_types) == {"development_sample"}

    lines = [
        "# SEC ADV Ingestion Quality Report",
        "",
    ]
    if is_sample:
        lines.extend([
            "> **Development sample only:** This report was generated from synthetic development rows, not official SEC/IAPD output.",
            "",
        ])
    else:
        lines.extend([
            "This report profiles normalized public firm-level records from a user-supplied local SEC/IAPD file.",
            "",
        ])

    lines.extend([
        "## Completeness Summary",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Row count | {profile['row_count']:,} |",
        f"| Unique firm CRD numbers | {profile['unique_firm_crd_number_count']:,} |",
        f"| Missing firm CRD numbers | {profile['missing_firm_crd_number_count']:,} |",
        f"| Missing firm names | {profile['missing_firm_name_count']:,} |",
        f"| Missing regulatory AUM values | {profile['missing_regulatory_aum_count']:,} |",
        "",
        "## Count by Registration State",
        "",
        "| Registration state | Count |",
        "| --- | ---: |",
    ])
    for state, count in profile["registration_state_counts"].items():
        lines.append(f"| {_markdown_text(state)} | {count:,} |")

    lines.extend([
        "",
        "## Top 10 Firms by Regulatory AUM",
        "",
        "| Rank | Firm CRD number | Firm name | Regulatory AUM |",
        "| ---: | --- | --- | ---: |",
    ])
    for rank, firm in enumerate(profile["top_firms_by_regulatory_aum"], start=1):
        aum = firm["regulatory_aum"]
        formatted_aum = "(missing)" if aum is None else f"${aum:,.0f}"
        lines.append(
            f"| {rank} | {_markdown_text(firm['firm_crd_number'])} | "
            f"{_markdown_text(firm['firm_name'])} | {formatted_aum} |"
        )

    lines.extend([
        "",
        "## Source Type Breakdown",
        "",
        "| Source type | Count |",
        "| --- | ---: |",
    ])
    for source_type, count in source_types.items():
        lines.append(f"| {_markdown_text(source_type)} | {count:,} |")

    lines.extend([
        "",
        "## Governance Note",
        "",
        "Public firm-level SEC/IAPD data remains separate from synthetic private-style branch, advisor, account, and monthly performance data.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _clean_string(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned.eq(""), pd.NA)


def _display_value(value: object) -> str:
    return "(missing)" if pd.isna(value) else str(value)


def _markdown_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")
