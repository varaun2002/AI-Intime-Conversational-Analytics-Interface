"""
Deterministic KPI calculations using Pandas.
No LLM involved — pure math on actual data.
Handles both raw multi-row data AND pre-aggregated single-row results.
"""
import pandas as pd
import numpy as np


def calculate_kpis(df: pd.DataFrame, intent: str, query: str) -> dict:
    """
    Compute KPIs based on the dataframe and intent type.
    Returns a dict of calculated metrics.
    """
    if df is None or df.empty:
        return {"error": "No data to calculate KPIs from"}

    kpis = {}
    cols = [c.lower() for c in df.columns]
    df.columns = [c.lower() for c in df.columns]

    # ---- Handle pre-aggregated results (1-5 rows from GROUP BY / COUNT) ----
    if len(df) <= 5 and len(df.columns) <= 5:
        for col in df.columns:
            values = df[col].tolist()
            if len(values) == 1:
                kpis[col] = values[0]
            else:
                # Multiple rows — probably a GROUP BY result
                kpis[col] = values

    # ---- Yield calculations (when raw order data is present) ----
    if "quantity_planned" in cols and "quantity_actual" in cols:
        df["yield_pct"] = (df["quantity_actual"] / df["quantity_planned"] * 100).round(2)
        kpis["avg_yield"] = round(df["yield_pct"].mean(), 2)
        kpis["min_yield"] = round(df["yield_pct"].min(), 2)
        kpis["max_yield"] = round(df["yield_pct"].max(), 2)
        kpis["total_planned"] = round(df["quantity_planned"].sum(), 2)
        kpis["total_actual"] = round(df["quantity_actual"].sum(), 2)
        kpis["total_variance"] = round(kpis["total_actual"] - kpis["total_planned"], 2)
        kpis["variance_pct"] = round(
            (kpis["total_actual"] - kpis["total_planned"]) / kpis["total_planned"] * 100, 2
        )

    # ---- Yield % column already computed by SQL ----
    for col in cols:
        if "yield" in col or "efficiency" in col or "ratio" in col:
            if df[col].dtype in ["float64", "int64", "float32"]:
                kpis[f"avg_{col}"] = round(df[col].mean(), 2)
                kpis[f"min_{col}"] = round(df[col].min(), 2)
                kpis[f"max_{col}"] = round(df[col].max(), 2)

    # ---- Order counts ----
    if "order_id" in cols:
        kpis["total_orders"] = int(df["order_id"].nunique())
    if "status" in cols:
        status_counts = df["status"].value_counts().to_dict()
        kpis["status_breakdown"] = status_counts
        kpis["completed_orders"] = int(status_counts.get("completed", 0))

    # ---- Time calculations ----
    if "start_time" in cols and "end_time" in cols:
        try:
            start = pd.to_datetime(df["start_time"], errors="coerce")
            end = pd.to_datetime(df["end_time"], errors="coerce")
            valid = start.notna() & end.notna()
            if valid.any():
                duration = (end[valid] - start[valid]).dt.total_seconds() / 60
                # Fix overnight shifts (negative duration means crosses midnight)
                duration = duration.apply(lambda x: x + 1440 if x < 0 else x)
                kpis["avg_duration_min"] = round(duration.mean(), 1)
                kpis["min_duration_min"] = round(duration.min(), 1)
                kpis["max_duration_min"] = round(duration.max(), 1)
                kpis["total_duration_hours"] = round(duration.sum() / 60, 1)
        except Exception:
            pass

    # ---- Cycle time ----
    if "cycle_time_minutes" in cols:
        kpis["avg_cycle_time"] = round(df["cycle_time_minutes"].mean(), 1)

    # ---- Shift counts ----
    if "shift_id" in cols:
        kpis["total_shifts"] = int(df["shift_id"].nunique())
    if "shift_type" in cols:
        kpis["shifts_by_type"] = df["shift_type"].value_counts().to_dict()
    if "shift_date" in cols:
        kpis["date_range"] = f"{df['shift_date'].min()} to {df['shift_date'].max()}"
        kpis["unique_days"] = int(df["shift_date"].nunique())

    # ---- Staff counts ----
    if "supervisor_id" in cols:
        kpis["unique_supervisors"] = int(df["supervisor_id"].nunique())
    if "operator_id" in cols:
        kpis["unique_operators"] = int(df["operator_id"].nunique())
    if "name" in cols:
        kpis["staff_names"] = df["name"].unique().tolist()

    # ---- Line breakdown ----
    if "line_id" in cols and "quantity_actual" in cols:
        line_totals = df.groupby("line_id")["quantity_actual"].sum()
        kpis["output_by_line"] = {k: round(v, 2) for k, v in line_totals.items()}
        kpis["best_line"] = line_totals.idxmax()
        kpis["worst_line"] = line_totals.idxmin()

    if "line_id" in cols and "yield_pct" in df.columns:
        line_yield = df.groupby("line_id")["yield_pct"].mean().round(2)
        kpis["yield_by_line"] = line_yield.to_dict()

    # ---- Product breakdown ----
    if "product_id" in cols and "quantity_actual" in cols:
        prod_totals = df.groupby("product_id")["quantity_actual"].sum()
        kpis["output_by_product"] = {k: round(v, 2) for k, v in prod_totals.items()}

    if "product_name" in cols and "quantity_actual" in cols:
        prod_totals = df.groupby("product_name")["quantity_actual"].sum()
        kpis["output_by_product_name"] = {k: round(v, 2) for k, v in prod_totals.items()}

    # ---- Supervisor performance ----
    if "supervisor_id" in cols and "yield_pct" in df.columns:
        sup_yield = df.groupby("supervisor_id")["yield_pct"].mean().round(2)
        kpis["yield_by_supervisor"] = sup_yield.to_dict()
        kpis["best_supervisor"] = sup_yield.idxmax()

    # ---- Comparison intent ----
    if intent == "COMPARISON":
        if "shift_type" in cols and "yield_pct" in df.columns:
            group_yield = df.groupby("shift_type")["yield_pct"].mean().round(2)
            kpis["yield_by_shift_type"] = group_yield.to_dict()

        # Generic: group by first text column, aggregate first numeric column
        text_cols = [c for c in df.columns if df[c].dtype == "object" and c not in ("order_id", "shift_id", "step_id")]
        num_cols = [c for c in df.columns if df[c].dtype in ["float64", "int64"]]
        if text_cols and num_cols:
            group_col = text_cols[0]
            val_col = num_cols[0]
            grouped = df.groupby(group_col)[val_col].mean().round(2)
            kpis["comparison"] = grouped.to_dict()
            kpis["comparison_group"] = group_col
            kpis["comparison_metric"] = val_col

    # ---- Trend intent ----
    if intent == "TREND":
        date_col = None
        for c in ["shift_date", "date", "day", "start_time", "end_time"]:
            if c in cols:
                date_col = c
                break

        num_cols = [c for c in df.columns if df[c].dtype in ["float64", "int64", "float32"]
                    and "id" not in c and c != "step_number"]
        if date_col and num_cols:
            val_col = "yield_pct" if "yield_pct" in df.columns else num_cols[0]
            try:
                if date_col in ("start_time", "end_time"):
                    df["_date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date.astype(str)
                    daily = df.groupby("_date")[val_col].mean().round(2)
                else:
                    daily = df.groupby(date_col)[val_col].mean().round(2)

                kpis["trend_data"] = {str(k): v for k, v in daily.items()}
                kpis["trend_metric"] = val_col

                if len(daily) >= 3:
                    x = np.arange(len(daily))
                    slope, intercept = np.polyfit(x, daily.values, 1)
                    kpis["trend_slope"] = round(slope, 3)
                    kpis["trend_direction"] = "improving" if slope > 0 else "declining"
            except Exception:
                pass

    # ---- Row count ----
    kpis["row_count"] = len(df)

    return kpis