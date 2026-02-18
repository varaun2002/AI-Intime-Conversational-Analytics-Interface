"""
Combines all outputs into the final report object.
"""
from datetime import datetime


def assemble_report(
    query: str,
    intent: str,
    sql_query: str,
    df,
    kpis: dict,
    summary: str,
    chart_figure,
    tables_used: list,
) -> dict:
    """Build the final report dict."""
    report = {
        "query": query,
        "intent": intent,
        "summary": summary,
        "kpis": kpis,
        "chart": chart_figure,
        "sql_query": sql_query,
        "tables_used": tables_used,
        "row_count": len(df) if df is not None else 0,
        "data": df,
        "timestamp": datetime.now().isoformat(),
    }
    return report