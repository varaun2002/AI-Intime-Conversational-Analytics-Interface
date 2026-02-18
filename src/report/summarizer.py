"""
Generates plain English summary from KPI data using LLM.
Numbers come from Pandas — LLM only writes the words around them.
"""

SUMMARY_SYSTEM_PROMPT = """You are a manufacturing analytics assistant.
Write a concise 2-3 sentence summary answering the user's question.

RULES:
- Use ONLY the numbers provided in the KPI data below — do not invent numbers
- Be specific: include actual values, percentages, counts
- Be direct: answer the question first, then add context
- No markdown, no bullet points — just plain sentences
"""


def build_summary_prompt(query: str, kpis: dict, df_preview: str) -> str:
    """Build the prompt for report summarization."""
    return f"""USER QUESTION: {query}

CALCULATED KPIs:
{kpis}

DATA PREVIEW (first 5 rows):
{df_preview}

Write a 2-3 sentence summary answering the user's question using ONLY the numbers above."""