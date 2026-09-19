"""Export a stakeholder-ready monthly finance and QA Excel report."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Border, Font, PatternFill, Side

from ingestion.generate_synthetic import generate_all_synthetic_data
from qa.evaluate import combine_detection_results, evaluate_detection_results
from qa.hard_rules import run_hard_rule_detection
from qa.inject_errors import inject_seeded_errors
from qa.reporting import select_operating_threshold, select_overall_metrics
from qa.statistical_rules import run_statistical_detection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "outputs" / "excel" / "monthly_finance_report.xlsx"
DEFAULT_Z_THRESHOLD = 2.5
DEFAULT_IQR_MULTIPLIER = 2.0


def default_report_name() -> str:
    """Return the default Excel report file name."""
    return DEFAULT_OUTPUT_PATH.name


def build_excel_report_data(seed: int = 42) -> dict[str, object]:
    """Build all local data needed for the Excel finance report."""
    datasets = generate_all_synthetic_data(seed=seed, months=8, max_firms=2, validate=True)
    corrupted_performance, ground_truth = inject_seeded_errors(datasets, seed=seed)
    hard_rule_results = run_hard_rule_detection(
        corrupted_performance,
        datasets["synthetic_accounts"],
        datasets["synthetic_advisors"],
        datasets["synthetic_branches"],
    )
    statistical_results = run_statistical_detection(
        corrupted_performance,
        z_threshold=DEFAULT_Z_THRESHOLD,
        iqr_multiplier=DEFAULT_IQR_MULTIPLIER,
    )
    combined = combine_detection_results(hard_rule_results, statistical_results)
    threshold_label = f"z={DEFAULT_Z_THRESHOLD}_iqr={DEFAULT_IQR_MULTIPLIER}"
    metrics, matches = evaluate_detection_results(ground_truth, combined, threshold_label=threshold_label)
    kpis = calculate_excel_kpi_tables(datasets)

    return {
        "datasets": datasets,
        "kpis": kpis,
        "ground_truth": ground_truth,
        "hard_rule_results": hard_rule_results,
        "statistical_results": statistical_results,
        "combined_detections": combined,
        "metrics": metrics,
        "matches": matches,
        "selected_threshold": threshold_label,
    }


def calculate_excel_kpi_tables(datasets: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Calculate firm, branch, advisor, and executive KPI tables for Excel."""
    performance = datasets["synthetic_monthly_performance"].copy()
    accounts = datasets["synthetic_accounts"].copy()
    advisors = datasets["synthetic_advisors"].copy()
    branches = datasets["synthetic_branches"].copy()

    perf_accounts = performance.merge(
        accounts[["account_id", "account_status", "client_segment"]],
        on="account_id",
        how="left",
    )
    perf_advisors = perf_accounts.merge(
        advisors[["advisor_id", "advisor_name", "primary_client_segment"]],
        on="advisor_id",
        how="left",
    )
    base = perf_advisors.merge(
        branches[["branch_id", "branch_name", "branch_region"]],
        on="branch_id",
        how="left",
    )

    advisor_kpis = _aggregate_kpis(
        base,
        ["month_end_date", "firm_crd_number", "branch_id", "branch_name", "advisor_id", "advisor_name"],
        include_advisor_count=False,
    )
    branch_kpis = _aggregate_kpis(
        base,
        ["month_end_date", "firm_crd_number", "branch_id", "branch_name", "branch_region"],
        include_advisor_count=True,
    )
    firm_kpis = _aggregate_kpis(
        base,
        ["month_end_date", "firm_crd_number"],
        include_advisor_count=True,
    )
    executive = _executive_summary(base, firm_kpis, branch_kpis, advisor_kpis)

    return {
        "executive_summary": executive,
        "firm_kpis": firm_kpis,
        "branch_kpis": branch_kpis,
        "advisor_kpis": advisor_kpis,
    }


def write_monthly_finance_report(
    report_data: dict[str, object],
    output_path: str | Path | None = None,
) -> Path:
    """Write the finance and QA report workbook."""
    path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    kpis = report_data["kpis"]
    metrics = report_data["metrics"]
    matches = report_data["matches"]
    ground_truth = report_data["ground_truth"]
    combined = report_data["combined_detections"]
    overall = select_overall_metrics(metrics)
    executive = kpis["executive_summary"].iloc[0].to_dict()
    selected_threshold = report_data.get("selected_threshold", select_operating_threshold(metrics))

    executive_summary = _executive_summary_sheet(executive, overall, selected_threshold)
    qa_summary = _qa_summary_sheet(ground_truth, combined, overall, selected_threshold)
    findings_sample = matches.head(25).copy()

    sheet_frames = {
        "Executive Summary": executive_summary,
        "Firm KPIs": kpis["firm_kpis"],
        "Branch KPIs": kpis["branch_kpis"],
        "Advisor KPIs": kpis["advisor_kpis"],
        "QA Summary": qa_summary,
        "QA Findings Sample": findings_sample,
    }

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheet_frames.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

        _format_workbook(writer, sheet_frames)

    return path


def export_monthly_finance_report(output_path: str | Path | None = None, seed: int = 42) -> Path:
    """Build report data and export the monthly finance workbook."""
    report_data = build_excel_report_data(seed=seed)
    return write_monthly_finance_report(report_data, output_path=output_path)


def _aggregate_kpis(df: pd.DataFrame, group_cols: list[str], include_advisor_count: bool) -> pd.DataFrame:
    agg = (
        df.groupby(group_cols, as_index=False)
        .agg(
            account_count=("account_id", "nunique"),
            beginning_aum=("beginning_aum", "sum"),
            ending_aum=("ending_aum", "sum"),
            net_new_assets=("net_new_assets", "sum"),
            revenue=("revenue", "sum"),
            avg_fee_rate=("fee_rate", "mean"),
        )
        .sort_values(group_cols)
    )
    if include_advisor_count:
        advisor_counts = df.groupby(group_cols)["advisor_id"].nunique().reset_index(name="advisor_count")
        agg = agg.merge(advisor_counts, on=group_cols, how="left")
    agg["aum_growth_rate"] = (agg["ending_aum"] - agg["beginning_aum"]) / agg["beginning_aum"].replace(0, pd.NA)
    agg["revenue_per_account"] = agg["revenue"] / agg["account_count"].replace(0, pd.NA)
    return agg


def _executive_summary(base: pd.DataFrame, firm_kpis: pd.DataFrame, branch_kpis: pd.DataFrame, advisor_kpis: pd.DataFrame) -> pd.DataFrame:
    total_beginning = base["beginning_aum"].sum()
    total_ending = base["ending_aum"].sum()
    return pd.DataFrame(
        [
            {
                "run_timestamp": "2026-09-18",
                "reporting_period_covered": f"{base['month_end_date'].min()} to {base['month_end_date'].max()}",
                "total_firms": firm_kpis["firm_crd_number"].nunique(),
                "total_branches": branch_kpis["branch_id"].nunique(),
                "total_advisors": advisor_kpis["advisor_id"].nunique(),
                "total_accounts": base["account_id"].nunique(),
                "total_beginning_aum": total_beginning,
                "total_ending_aum": total_ending,
                "total_net_new_assets": base["net_new_assets"].sum(),
                "total_revenue": base["revenue"].sum(),
                "portfolio_aum_growth_rate": (total_ending - total_beginning) / total_beginning if total_beginning else 0,
            }
        ]
    )


def _executive_summary_sheet(executive: dict[str, object], overall: pd.Series, selected_threshold: str) -> pd.DataFrame:
    rows = [
        ("Run timestamp", executive["run_timestamp"]),
        ("Reporting period covered", executive["reporting_period_covered"]),
        ("Total firms", executive["total_firms"]),
        ("Total branches", executive["total_branches"]),
        ("Total advisors", executive["total_advisors"]),
        ("Total accounts", executive["total_accounts"]),
        ("Total beginning AUM", executive["total_beginning_aum"]),
        ("Total ending AUM", executive["total_ending_aum"]),
        ("Total net new assets", executive["total_net_new_assets"]),
        ("Total revenue", executive["total_revenue"]),
        ("Portfolio AUM growth rate", executive["portfolio_aum_growth_rate"]),
        ("Overall QA precision", overall.get("precision", 0)),
        ("Overall QA recall", overall.get("recall", 0)),
        ("Overall QA false-positive rate", overall.get("false_positive_rate", 0)),
        ("Selected QA threshold", selected_threshold),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def _qa_summary_sheet(ground_truth: pd.DataFrame, detections: pd.DataFrame, overall: pd.Series, selected_threshold: str) -> pd.DataFrame:
    rows = [
        ("Injected error count", len(ground_truth)),
        ("Detection count", len(detections)),
        ("Precision", overall.get("precision", 0)),
        ("Recall", overall.get("recall", 0)),
        ("False-positive rate", overall.get("false_positive_rate", 0)),
        ("F1 score", overall.get("f1_score", 0)),
        ("Threshold label", selected_threshold),
        (
            "Reviewer tradeoff note",
            "Higher recall catches more seeded issues; lower false positives reduce reviewer workload.",
        ),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def _format_workbook(writer: pd.ExcelWriter, sheet_frames: dict[str, pd.DataFrame]) -> None:
    header_fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    header_font = Font(bold=True)
    thin_border = Border(bottom=Side(style="thin", color="B7C9D6"))

    for sheet_name, worksheet in writer.sheets.items():
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.border = thin_border

        _autosize_columns(worksheet, sheet_frames[sheet_name])

        if sheet_name == "Executive Summary":
            _format_metric_rows(worksheet)
        elif sheet_name == "QA Summary":
            _format_metric_rows(worksheet)
            worksheet.column_dimensions["B"].width = 60
        else:
            _format_kpi_sheet(worksheet)


def _autosize_columns(worksheet, df: pd.DataFrame) -> None:
    for index, column_name in enumerate(df.columns, start=1):
        values = [column_name]
        if not df.empty:
            values.extend(df[column_name].head(100).astype(str).tolist())
        width = min(max(len(str(value)) for value in values) + 2, 40)
        worksheet.column_dimensions[worksheet.cell(row=1, column=index).column_letter].width = width


def _format_metric_rows(worksheet) -> None:
    currency_labels = {"Total beginning AUM", "Total ending AUM", "Total net new assets", "Total revenue"}
    percent_labels = {
        "Portfolio AUM growth rate",
        "Overall QA precision",
        "Overall QA recall",
        "Overall QA false-positive rate",
        "Precision",
        "Recall",
        "False-positive rate",
        "F1 score",
    }
    number_labels = {
        "Total firms",
        "Total branches",
        "Total advisors",
        "Total accounts",
        "Injected error count",
        "Detection count",
    }
    for row in range(2, worksheet.max_row + 1):
        label = worksheet.cell(row=row, column=1).value
        value_cell = worksheet.cell(row=row, column=2)
        if label in currency_labels:
            value_cell.number_format = "$#,##0"
        elif label in percent_labels:
            value_cell.number_format = "0.0%"
        elif label in number_labels:
            value_cell.number_format = "#,##0"


def _format_kpi_sheet(worksheet) -> None:
    currency_columns = {"beginning_aum", "ending_aum", "net_new_assets", "revenue", "revenue_per_account"}
    percent_columns = {"avg_fee_rate", "aum_growth_rate"}
    number_columns = {"account_count", "advisor_count"}
    for column in range(1, worksheet.max_column + 1):
        header = worksheet.cell(row=1, column=column).value
        if header in currency_columns:
            number_format = "$#,##0"
        elif header in percent_columns:
            number_format = "0.0%"
        elif header in number_columns:
            number_format = "#,##0"
        else:
            continue
        for row in range(2, worksheet.max_row + 1):
            worksheet.cell(row=row, column=column).number_format = number_format


if __name__ == "__main__":
    output = export_monthly_finance_report()
    print(f"Excel report written to {output}")
