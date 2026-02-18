"""
Safety check — ensures generated SQL is read-only.
Rejects any write/modify operations before execution.
"""
import re

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
    "ALTER", "CREATE", "REPLACE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE", "MERGE",
]


def validate_sql(sql: str) -> dict:
    """
    Check SQL for forbidden keywords.
    Returns: {"valid": bool, "error": str or None, "cleaned_sql": str}
    """
    if not sql or not sql.strip():
        return {"valid": False, "error": "Empty SQL query", "cleaned_sql": ""}

    cleaned = sql.strip()

    # Remove markdown code fences if LLM wraps it
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    # Remove trailing semicolons (SQLite handles fine without)
    cleaned = cleaned.rstrip(";").strip()

    # Check for forbidden keywords
    # Use word boundary matching to avoid false positives
    # e.g., "UPDATED_AT" column name shouldn't trigger "UPDATE"
    upper_sql = cleaned.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, upper_sql):
            return {
                "valid": False,
                "error": f"Forbidden keyword detected: {keyword}. Only SELECT queries allowed.",
                "cleaned_sql": "",
            }

    # Must start with SELECT or WITH (for CTEs)
    first_word = upper_sql.lstrip().split()[0] if upper_sql.strip() else ""
    if first_word not in ("SELECT", "WITH"):
        return {
            "valid": False,
            "error": f"Query must start with SELECT or WITH. Got: {first_word}",
            "cleaned_sql": "",
        }

    return {"valid": True, "error": None, "cleaned_sql": cleaned}