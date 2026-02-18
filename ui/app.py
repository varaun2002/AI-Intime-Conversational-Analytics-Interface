"""
Streamlit chat interface for AI Intime.
Renders reports with summary, KPIs, charts, data tables, and metadata.
"""
import streamlit as st
import pandas as pd
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.analytics_agent import AnalyticsAgent


# ---- Page Config ----
st.set_page_config(
    page_title="AI Intime — Manufacturing Analytics",
    page_icon="🏭",
    layout="wide",
)

# ---- Custom CSS ----
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        opacity: 0.7;
        margin-bottom: 2rem;
    }
    .kpi-card {
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
    }
    .kpi-label {
        font-size: 0.85rem;
        opacity: 0.6;
        margin-top: 0.3rem;
    }
    .report-section {
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(255,255,255,0.1);
    }
</style>
""", unsafe_allow_html=True)


# ---- Initialize Agent (cached) ----
@st.cache_resource
def load_agent():
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "sample_manufacturing.db"
    )
    return AnalyticsAgent(db_path)


def render_kpis(kpis: dict):
    """Render KPI cards in columns."""
    if not kpis or "error" in kpis:
        return

    # Pick the most important KPIs to display as cards
    display_kpis = {}

    key_map = {
        "avg_yield": ("Avg Yield", "%"),
        "total_orders": ("Total Orders", ""),
        "total_planned": ("Total Planned", ""),
        "total_actual": ("Total Actual", ""),
        "total_variance": ("Variance", ""),
        "avg_duration_min": ("Avg Duration", " min"),
        "total_shifts": ("Total Shifts", ""),
        "min_yield": ("Min Yield", "%"),
        "max_yield": ("Max Yield", "%"),
        "unique_supervisors": ("Supervisors", ""),
        "row_count": ("Records", ""),
    }

    for key, (label, suffix) in key_map.items():
        if key in kpis:
            display_kpis[label] = f"{kpis[key]}{suffix}"

    if not display_kpis:
        return

    cols = st.columns(min(len(display_kpis), 4))
    for i, (label, value) in enumerate(list(display_kpis.items())[:4]):
        with cols[i]:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-value">{value}</div>
                <div class="kpi-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


def render_report(report: dict):
    """Render the full report."""

    # Summary
    st.markdown("### 📋 Summary")
    st.markdown(f'<div class="report-section">{report["summary"]}</div>',
                unsafe_allow_html=True)

    # KPIs
    if report.get("kpis"):
        st.markdown("### 📊 Key Metrics")
        render_kpis(report["kpis"])

    # Chart
    if report.get("chart") is not None:
        st.markdown("### 📈 Visualization")
        st.plotly_chart(report["chart"], use_container_width=True)

    # Data Table
    if report.get("data") is not None and not report["data"].empty:
        st.markdown("### 🗃️ Data")
        with st.expander(f"View raw data ({report['row_count']} rows)", expanded=False):
            st.dataframe(report["data"], use_container_width=True)

    # Metadata
    st.markdown("### ⚙️ Query Details")
    meta_cols = st.columns(3)
    with meta_cols[0]:
        st.markdown(f"**Intent:** `{report.get('intent', 'N/A')}`")
    with meta_cols[1]:
        tables = ", ".join(report.get("tables_used", []))
        st.markdown(f"**Tables:** `{tables}`")
    with meta_cols[2]:
        st.markdown(f"**Timestamp:** `{report.get('timestamp', 'N/A')[:19]}`")

    with st.expander("View generated SQL", expanded=False):
        st.code(report.get("sql_query", "N/A"), language="sql")


# ---- Main App ----
def main():
    # Header
    st.markdown('<div class="main-header">🏭 AI Intime</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Conversational Manufacturing Analytics — Powered by DeepSeek + LangGraph</div>',
                unsafe_allow_html=True)

    # Load agent
    agent = load_agent()

    # Chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg["content"])
            else:
                render_report(msg["report"])

    # Chat input
    if question := st.chat_input("Ask about your manufacturing data..."):
        # Show user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Run agent
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                start = time.time()
                report = agent.ask(question)
                elapsed = time.time() - start
                report["elapsed_seconds"] = round(elapsed, 2)

            render_report(report)
            st.session_state.messages.append({"role": "assistant", "report": report})

    # Sidebar
    with st.sidebar:
        st.markdown("## 💡 Sample Questions")
        sample_questions = [
            "How many orders were completed?",
            "What was the yield for LINE-3 this week?",
            "Show me details for order PO-1042",
            "Compare yield between day and night shift",
            "Which supervisor had the best performance?",
            "Plot yield trend for the last 10 days",
            "What products did we make on 2026-02-14?",
            "What's the average cycle time for ChemX-500?",
        ]
        for q in sample_questions:
            if st.button(q, use_container_width=True):
                st.session_state["_pending_question"] = q
                st.rerun()

        st.markdown("---")
        st.markdown("## ℹ️ System Info")
        st.markdown(f"**LLM:** {agent.llm.provider} / {agent.llm.model}")
        st.markdown(f"**Database:** {agent.db_path}")
        st.markdown(f"**Tables:** {len(agent.schema)}")
        st.markdown(f"**LLM Available:** {'✅' if agent.llm.is_available() else '❌'}")

    # Handle sidebar button clicks
    if "_pending_question" in st.session_state:
        q = st.session_state.pop("_pending_question")
        st.session_state.messages.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                report = agent.ask(q)
            render_report(report)
            st.session_state.messages.append({"role": "assistant", "report": report})


if __name__ == "__main__":
    main()