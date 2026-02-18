"""
Generates Plotly charts via LLM or deterministically based on intent + data.
Falls back to auto-chart if LLM-generated code fails.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

CHART_SYSTEM_PROMPT = """You are a Python data visualization expert.
Generate Plotly code to create a chart for manufacturing data.

RULES:
- Use plotly.graph_objects as go (already imported)
- The data is a pandas DataFrame called `df`
- KPIs are a dict called `kpis`
- Assign the final figure to a variable called `fig`
- Use a clean dark theme: template='plotly_dark'
- Add a clear title and axis labels
- Return ONLY Python code, no explanation, no markdown, no backticks
- Do NOT call fig.show()
- Do NOT import anything — go, pd, np are already available
"""


def build_chart_prompt(query: str, intent: str, kpis: dict, df_info: str) -> str:
    """Build prompt for chart code generation."""
    chart_hints = {
        "TREND": "Create a LINE CHART showing values over time. X-axis should be dates.",
        "COMPARISON": "Create a GROUPED BAR CHART comparing categories side by side.",
        "AGGREGATION": "Create a BAR CHART showing totals or averages per category.",
        "REPORT": "Create the most appropriate chart for this data.",
        "LOOKUP": None,
    }

    hint = chart_hints.get(intent)
    if hint is None:
        return None

    return f"""{hint}

USER QUESTION: {query}

KPIs: {kpis}

DATAFRAME INFO:
{df_info}

Generate Plotly code. `df`, `kpis`, `go`, `pd`, `np` are available. Assign to `fig`."""


def execute_chart_code(code: str, df: pd.DataFrame, kpis: dict) -> dict:
    """Safely execute LLM-generated chart code."""
    try:
        clean = code.strip()
        if "```" in clean:
            lines = clean.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            clean = "\n".join(lines)

        local_vars = {"df": df.copy(), "kpis": kpis, "go": go, "px": px, "pd": pd, "np": np}
        exec(clean, {"__builtins__": {"range": range, "len": len, "list": list, "dict": dict,
                                       "str": str, "int": int, "float": float, "round": round,
                                       "enumerate": enumerate, "zip": zip, "sorted": sorted,
                                       "min": min, "max": max, "sum": sum, "abs": abs}},
             local_vars)

        fig = local_vars.get("fig")
        if fig is None:
            return {"success": False, "error": "No 'fig' variable created", "figure": None}

        return {"success": True, "error": None, "figure": fig}

    except Exception as e:
        return {"success": False, "error": str(e), "figure": None}


def auto_chart(df: pd.DataFrame, kpis: dict, intent: str, query: str) -> go.Figure:
    """
    Deterministic chart generation — no LLM needed.
    Fallback when LLM chart code fails, or primary for simple cases.
    """
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]
    fig = None

    try:
        # ---- TREND: Line chart over time ----
        if intent == "TREND" and "trend_data" in kpis:
            dates = list(kpis["trend_data"].keys())
            values = list(kpis["trend_data"].values())
            metric = kpis.get("trend_metric", "value")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=values,
                mode="lines+markers",
                name=metric,
                line=dict(width=3),
                marker=dict(size=8),
            ))
            fig.update_layout(
                title=f"Trend: {metric}",
                xaxis_title="Date",
                yaxis_title=metric.replace("_", " ").title(),
                template="plotly_dark",
            )
            return fig

        # ---- COMPARISON: Grouped bar ----
        if intent == "COMPARISON" and "comparison" in kpis:
            categories = list(kpis["comparison"].keys())
            values = list(kpis["comparison"].values())
            metric = kpis.get("comparison_metric", "value")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=categories, y=values,
                text=[f"{v:.1f}" for v in values],
                textposition="auto",
                marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"][:len(categories)],
            ))
            fig.update_layout(
                title=f"Comparison: {metric.replace('_', ' ').title()}",
                xaxis_title=kpis.get("comparison_group", "Category"),
                yaxis_title=metric.replace("_", " ").title(),
                template="plotly_dark",
            )
            return fig
        
        # ---- REPORT: Step timeline or order breakdown ----
        if intent == "REPORT":
            # If steps are present, show step-level bar chart
            if "step_name" in [c.lower() for c in df.columns]:
                step_col = "step_name"
                if "yield_pct" in df.columns:
                    val_col = "yield_pct"
                elif "quantity_actual" in [c.lower() for c in df.columns]:
                    val_col = "quantity_actual"
                else:
                    val_col = None

                if val_col:
                    step_data = df.groupby(step_col)[val_col].mean().round(2)
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=step_data.index.tolist(),
                        y=step_data.values.tolist(),
                        text=[f"{v:.1f}" for v in step_data.values],
                        textposition="auto",
                        marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA",
                                      "#FFA15A", "#19D3F3", "#FF6692"][:len(step_data)],
                    ))
                    fig.update_layout(
                        title="Breakdown by Production Step",
                        xaxis_title="Step",
                        yaxis_title=val_col.replace("_", " ").title(),
                        template="plotly_dark",
                    )
                    return fig

            # If orders are present, show per-order yield
            if "order_id" in [c.lower() for c in df.columns] and "yield_pct" in df.columns:
                order_yield = df.groupby("order_id")["yield_pct"].mean().round(2)
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=order_yield.index.tolist(),
                    y=order_yield.values.tolist(),
                    text=[f"{v:.1f}%" for v in order_yield.values],
                    textposition="auto",
                    marker_color="#636EFA",
                ))
                fig.update_layout(
                    title="Yield by Order",
                    xaxis_title="Order",
                    yaxis_title="Yield %",
                    template="plotly_dark",
                )
                return fig

        # ---- Yield by line ----
        if "yield_by_line" in kpis:
            lines = list(kpis["yield_by_line"].keys())
            yields = list(kpis["yield_by_line"].values())
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=lines, y=yields,
                text=[f"{v:.1f}%" for v in yields],
                textposition="auto",
                marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"][:len(lines)],
            ))
            fig.update_layout(
                title="Yield by Production Line",
                xaxis_title="Line",
                yaxis_title="Yield %",
                template="plotly_dark",
            )
            return fig

        # ---- Yield by supervisor ----
        if "yield_by_supervisor" in kpis:
            sups = list(kpis["yield_by_supervisor"].keys())
            yields = list(kpis["yield_by_supervisor"].values())
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=sups, y=yields,
                text=[f"{v:.1f}%" for v in yields],
                textposition="auto",
                marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"][:len(sups)],
            ))
            fig.update_layout(
                title="Yield by Supervisor",
                xaxis_title="Supervisor",
                yaxis_title="Yield %",
                template="plotly_dark",
            )
            return fig

        # ---- Output by product ----
        if "output_by_product_name" in kpis:
            products = list(kpis["output_by_product_name"].keys())
            amounts = list(kpis["output_by_product_name"].values())
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=products, y=amounts,
                text=[f"{v:,.0f}" for v in amounts],
                textposition="auto",
                marker_color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"][:len(products)],
            ))
            fig.update_layout(
                title="Output by Product",
                xaxis_title="Product",
                yaxis_title="Quantity",
                template="plotly_dark",
            )
            return fig

        # ---- Generic: if there's a text col + numeric col, bar chart ----
        text_cols = [c for c in df.columns if df[c].dtype == "object"
                     and c not in ("order_id", "shift_id", "step_id", "status")]
        num_cols = [c for c in df.columns if df[c].dtype in ["float64", "int64"]
                    and "id" not in c]
        if text_cols and num_cols and len(df) <= 50:
            x_col = text_cols[0]
            y_col = num_cols[0]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df[x_col].tolist(),
                y=df[y_col].tolist(),
                marker_color="#636EFA",
            ))
            fig.update_layout(
                title=f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
                xaxis_title=x_col.replace("_", " ").title(),
                yaxis_title=y_col.replace("_", " ").title(),
                template="plotly_dark",
            )
            return fig

    except Exception:
        pass

    return fig