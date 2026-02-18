"""
Full test suite — runs every query type and reports results.
Run from ai-intime/ directory: python3 tests/test_all_queries.py
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.agents.analytics_agent import AnalyticsAgent

agent = AnalyticsAgent("data/sample_manufacturing.db")

TESTS = [
    # ---- LOOKUP ----
    ("LOOKUP", "Show me details for order PO-1042"),
    ("LOOKUP", "What recipe is used for ChemX-500?"),
    ("LOOKUP", "Who are our supervisors and how many shifts have they worked?"),

    # ---- AGGREGATION ----
    ("AGGREGATION", "How many orders were completed?"),
    ("AGGREGATION", "What is the average yield across all lines?"),
    ("AGGREGATION", "What's the average cycle time for ChemX-500?"),
    ("AGGREGATION", "What products did we make on 2026-02-14?"),
    ("AGGREGATION", "How many orders did we complete last week?"),
    ("AGGREGATION", "What percentage of orders were cancelled?"),
    ("AGGREGATION", "What is the total output in kg this month?"),

    # ---- COMPARISON ----
    ("COMPARISON", "Compare yield between day shift and night shift"),
    ("COMPARISON", "Which line has the highest yield?"),
    ("COMPARISON", "How does Building A compare to Building B in total output?"),
    ("COMPARISON", "Compare the performance of John Davis vs Sarah Chen"),

    # ---- TREND ----
    ("TREND", "Plot yield trend for the last 10 days"),
    ("TREND", "Show me daily production output for the past 2 weeks"),
    ("TREND", "What's the yield trend for LINE-2 this month?"),

    # ---- REPORT ----
    ("REPORT", "Give me a full shift report for the night shift on February 10th"),
    ("REPORT", "What happened on LINE-1 last week?"),
    ("REPORT", "Which supervisor had the best performance this month?"),
]

print("=" * 80)
print("AI INTIME — FULL TEST SUITE")
print(f"Testing {len(TESTS)} queries against {agent.llm.model}")
print("=" * 80)

results = []

for i, (expected_intent, question) in enumerate(TESTS, 1):
    print(f"\n{'─' * 80}")
    print(f"[{i}/{len(TESTS)}] {question}")
    print(f"Expected intent: {expected_intent}")
    print(f"{'─' * 80}")

    start = time.time()
    try:
        report = agent.ask(question)
        elapsed = round(time.time() - start, 2)

        intent_match = "✅" if report["intent"] == expected_intent else "⚠️"
        has_data = "✅" if report["row_count"] > 0 else "❌"
        has_chart = "✅" if report["chart"] is not None else "➖"
        has_kpis = "✅" if report["kpis"] and "error" not in report["kpis"] else "❌"
        has_summary = "✅" if report["summary"] and "Sorry" not in report["summary"] else "❌"

        print(f"  Intent:  {intent_match} {report['intent']} (expected {expected_intent})")
        print(f"  Data:    {has_data} {report['row_count']} rows")
        print(f"  KPIs:    {has_kpis} {list(report['kpis'].keys())[:5]}...")
        print(f"  Chart:   {has_chart}")
        print(f"  Summary: {has_summary}")
        print(f"  Time:    {elapsed}s")
        print(f"  SQL:     {report['sql_query'][:100]}...")
        print(f"  Summary: {report['summary'][:150]}...")

        results.append({
            "question": question,
            "expected": expected_intent,
            "actual": report["intent"],
            "intent_ok": report["intent"] == expected_intent,
            "data_ok": report["row_count"] > 0,
            "chart": report["chart"] is not None,
            "kpis_ok": bool(report["kpis"] and "error" not in report["kpis"]),
            "summary_ok": bool(report["summary"] and "Sorry" not in report["summary"]),
            "time": elapsed,
            "error": None,
        })

    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f"  ❌ FAILED: {str(e)[:200]}")
        results.append({
            "question": question,
            "expected": expected_intent,
            "actual": "ERROR",
            "intent_ok": False,
            "data_ok": False,
            "chart": False,
            "kpis_ok": False,
            "summary_ok": False,
            "time": elapsed,
            "error": str(e),
        })

# ---- Summary Report ----
print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)

total = len(results)
intent_ok = sum(1 for r in results if r["intent_ok"])
data_ok = sum(1 for r in results if r["data_ok"])
kpis_ok = sum(1 for r in results if r["kpis_ok"])
charts = sum(1 for r in results if r["chart"])
summaries_ok = sum(1 for r in results if r["summary_ok"])
errors = sum(1 for r in results if r["error"])
avg_time = round(sum(r["time"] for r in results) / total, 2)

print(f"  Total queries:     {total}")
print(f"  Intent correct:    {intent_ok}/{total}")
print(f"  Data returned:     {data_ok}/{total}")
print(f"  KPIs computed:     {kpis_ok}/{total}")
print(f"  Charts generated:  {charts}/{total}")
print(f"  Summaries valid:   {summaries_ok}/{total}")
print(f"  Errors:            {errors}/{total}")
print(f"  Avg response time: {avg_time}s")

# ---- Failed queries ----
failed = [r for r in results if not r["data_ok"] or r["error"]]
if failed:
    print(f"\n{'─' * 80}")
    print("FAILED QUERIES:")
    for r in failed:
        print(f"  ❌ {r['question']}")
        if r["error"]:
            print(f"     Error: {r['error'][:100]}")
        else:
            print(f"     Intent: {r['actual']}, Data: {r['data_ok']}")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)