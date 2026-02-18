"""
LangGraph 5-node analytics agent.
Intent Classification -> Schema Retrieval -> SQL Gen+Exec -> KPI Calc -> Report Assembly
"""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
import pandas as pd

from src.llm.provider import LLMProvider
from src.schema.extractor import extract_schema, get_schema_context
from src.retrieval.schema_store import SchemaStore
from src.sql.generator import SQL_SYSTEM_PROMPT, build_sql_prompt, parse_sql_response
from src.sql.validator import validate_sql
from src.sql.executor import SQLExecutor
from src.calculations.kpi_agent import calculate_kpis
from src.report.summarizer import SUMMARY_SYSTEM_PROMPT, build_summary_prompt
from src.report.assembler import assemble_report


# ---- Agent State ----
class AgentState(TypedDict):
    query: str
    intent: str
    needs_chart: bool
    relevant_tables: List[str]
    schema_context: str
    sql_query: str
    sql_result: Optional[pd.DataFrame]
    calculations: dict
    sql_retries: int
    chart_code: str
    chart_retries: int
    chart_output: Optional[object]
    report_summary: str
    final_report: dict
    error: str


# ---- Intent Classification Prompt ----
INTENT_SYSTEM_PROMPT = """Classify the user's manufacturing question into exactly one intent.

Respond with ONLY a JSON object, no explanation:
{"intent": "LOOKUP|AGGREGATION|COMPARISON|TREND|REPORT", "needs_chart": true|false}

INTENT DEFINITIONS:
- LOOKUP: fetch a specific record (e.g., "show me order PO-1042")
- AGGREGATION: summarize data with averages/totals (e.g., "what was average yield")
- COMPARISON: compare two groups or periods (e.g., "day shift vs night shift")
- TREND: show change over time (e.g., "yield trend for last 10 days")
- REPORT: full summary of a period/shift (e.g., "what happened last shift")

Return ONLY the JSON object."""


class AnalyticsAgent:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.llm = LLMProvider()
        self.executor = SQLExecutor(db_path)
        self.schema = extract_schema(db_path)
        self.store = SchemaStore()
        self.store.ingest(self.schema)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the 5-node LangGraph workflow."""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("classify_intent", self.classify_intent)
        graph.add_node("retrieve_schema", self.retrieve_schema)
        graph.add_node("generate_sql", self.generate_sql)
        graph.add_node("calculate_kpis", self.calculate_kpis_node)
        graph.add_node("assemble_report", self.assemble_report_node)

        # Set entry point
        graph.set_entry_point("classify_intent")

        # Linear flow with conditional on SQL
        graph.add_edge("classify_intent", "retrieve_schema")
        graph.add_edge("retrieve_schema", "generate_sql")
        graph.add_conditional_edges(
            "generate_sql",
            self._sql_router,
            {"success": "calculate_kpis", "retry": "generate_sql", "fatal": "assemble_report"},
        )
        graph.add_edge("calculate_kpis", "assemble_report")
        graph.add_edge("assemble_report", END)

        return graph.compile()

    # ---- Node 1: Intent Classifier ----
    def classify_intent(self, state: AgentState) -> dict:
        try:
            response = self.llm.generate(state["query"], INTENT_SYSTEM_PROMPT)
            # Parse JSON from response
            import json
            # Find JSON in response
            text = response.strip()
            if "{" in text:
                json_str = text[text.index("{"):text.rindex("}") + 1]
                result = json.loads(json_str)
                intent = result.get("intent", "AGGREGATION").upper()
                needs_chart = result.get("needs_chart", False)
            else:
                intent = "AGGREGATION"
                needs_chart = False
        except Exception:
            intent = "AGGREGATION"
            needs_chart = False

        valid_intents = {"LOOKUP", "AGGREGATION", "COMPARISON", "TREND", "REPORT"}
        if intent not in valid_intents:
            intent = "AGGREGATION"

        return {"intent": intent, "needs_chart": needs_chart, "sql_retries": 0, "chart_retries": 0}

    # ---- Node 2: Schema Retriever ----
    def retrieve_schema(self, state: AgentState) -> dict:
        tables = self.store.get_matched_table_names(state["query"], top_k=4)
        schema_context = get_schema_context(self.schema, tables)
        return {"relevant_tables": tables, "schema_context": schema_context}

    # ---- Node 3: SQL Generator + Executor ----
    def generate_sql(self, state: AgentState) -> dict:
        error_ctx = state.get("error") if state.get("sql_retries", 0) > 0 else None
        prompt = build_sql_prompt(state["query"], state["schema_context"], error_ctx)
        response = self.llm.generate(prompt, SQL_SYSTEM_PROMPT)
        sql = parse_sql_response(response)

        # Validate
        validation = validate_sql(sql)
        if not validation["valid"]:
            return {
                "sql_query": sql,
                "sql_result": None,
                "error": validation["error"],
                "sql_retries": state.get("sql_retries", 0) + 1,
            }

        # Execute
        result = self.executor.execute(validation["cleaned_sql"])
        if not result["success"]:
            return {
                "sql_query": validation["cleaned_sql"],
                "sql_result": None,
                "error": result["error"],
                "sql_retries": state.get("sql_retries", 0) + 1,
            }

        return {
            "sql_query": validation["cleaned_sql"],
            "sql_result": result["data"],
            "error": "",
        }

    # ---- SQL Router ----
    def _sql_router(self, state: AgentState) -> str:
        if state.get("sql_result") is not None and state.get("error", "") == "":
            return "success"
        if state.get("sql_retries", 0) >= 3:
            return "fatal"
        return "retry"

    # ---- Node 4: KPI Calculator ----
    def calculate_kpis_node(self, state: AgentState) -> dict:
        df = state.get("sql_result")
        if df is None or df.empty:
            return {"calculations": {"error": "No data available"}}
        kpis = calculate_kpis(df, state["intent"], state["query"])
        return {"calculations": kpis}

    # ---- Node 5: Report Assembler ----
    def assemble_report_node(self, state: AgentState) -> dict:
        df = state.get("sql_result")
        kpis = state.get("calculations", {})

        # Handle fatal SQL error
        if df is None:
            report = assemble_report(
                query=state["query"],
                intent=state.get("intent", "UNKNOWN"),
                sql_query=state.get("sql_query", ""),
                df=pd.DataFrame(),
                kpis={},
                summary=f"Sorry, I couldn't retrieve data for your question. Error: {state.get('error', 'Unknown')}",
                chart_figure=None,
                tables_used=state.get("relevant_tables", []),
            )
            return {"final_report": report}

        # 5a: Generate text summary
        df_preview = df.head(5).to_string()
        summary_prompt = build_summary_prompt(state["query"], kpis, df_preview)
        try:
            summary = self.llm.generate(summary_prompt, SUMMARY_SYSTEM_PROMPT)
        except Exception as e:
            summary = f"Data retrieved: {len(df)} rows. KPIs: {kpis}"

        # 5b: Generate chart
        chart_fig = None
        if state["intent"] != "LOOKUP":
            # Try auto-chart first (deterministic, reliable)
            from src.report.chart_generator import auto_chart, build_chart_prompt, execute_chart_code, CHART_SYSTEM_PROMPT
            chart_fig = auto_chart(df, kpis, state["intent"], state["query"])

            # If auto-chart didn't produce anything, try LLM
            if chart_fig is None and state.get("needs_chart", True):
                df_info = f"Columns: {list(df.columns)}\nShape: {df.shape}\nFirst 3 rows:\n{df.head(3).to_string()}"
                chart_prompt = build_chart_prompt(
                    state["query"], state["intent"], kpis, df_info
                )
                if chart_prompt:
                    retries = 0
                    while retries < 2 and chart_fig is None:
                        try:
                            chart_code = self.llm.generate(chart_prompt, CHART_SYSTEM_PROMPT)
                            result = execute_chart_code(chart_code, df, kpis)
                            if result["success"]:
                                chart_fig = result["figure"]
                            else:
                                chart_prompt += f"\n\nPREVIOUS CODE FAILED: {result['error']}\nFix it."
                        except Exception:
                            pass
                        retries += 1

        # 5c: Assemble
        report = assemble_report(
            query=state["query"],
            intent=state["intent"],
            sql_query=state["sql_query"],
            df=df,
            kpis=kpis,
            summary=summary,
            chart_figure=chart_fig,
            tables_used=state.get("relevant_tables", []),
        )
        return {"final_report": report}

    # ---- Public API ----
    def ask(self, question: str) -> dict:
        """Run a question through the full pipeline."""
        initial_state = {
            "query": question,
            "intent": "",
            "needs_chart": False,
            "relevant_tables": [],
            "schema_context": "",
            "sql_query": "",
            "sql_result": None,
            "calculations": {},
            "sql_retries": 0,
            "chart_code": "",
            "chart_retries": 0,
            "chart_output": None,
            "report_summary": "",
            "final_report": {},
            "error": "",
        }
        result = self.graph.invoke(initial_state)
        return result["final_report"]