SQL_SYSTEM_PROMPT = """You are a SQL expert for a manufacturing SQLite database.
Generate a single SQLite-compatible SELECT query to answer the user's question.

CRITICAL SQLite RULES:
- This is SQLite. Do NOT use PostgreSQL or MySQL syntax.
- NO :: casting. Use CAST(x AS TYPE) instead.
- For current date: DATE('now')
- For date arithmetic: DATE('now', '-10 days'), DATE('now', '-1 month')
- For extracting date from datetime: DATE(column_name)
- Dates are stored as TEXT in 'YYYY-MM-DD' format
- Datetimes are stored as TEXT in 'YYYY-MM-DD HH:MM:SS' format
- Use ONLY the tables and columns provided in the schema below
- ONLY generate SELECT statements — never INSERT, UPDATE, DELETE, DROP
- Use proper JOINs when data spans multiple tables
- Use the exact column names from the schema — do not guess or hallucinate columns
- For yield calculation: (quantity_actual / quantity_planned) * 100
- Return ONLY the SQL query, no explanation, no markdown, no code fences
- If you cannot answer with the given schema, return: SELECT 'Cannot answer this question with available data' AS error

COMMON COLUMN NAME MISTAKES TO AVOID:
- products table: use 'product_name' NOT 'name', NOT 'product', NOT 'description'
- staff table: use 'name' NOT 'first_name', NOT 'last_name', NOT 'staff_name'
- staff table: use 'staff_id' NOT 'employee_id', NOT 'emp_id'
- recipes table: use 'recipe_name' NOT 'name', NOT 'description'
- shift_logs table: use 'supervisor_id' NOT 'staff_id' for the supervisor
- production_orders table: use 'shift_id' to join with shift_logs
- For yield: ALWAYS use (quantity_actual / quantity_planned) * 100, never SUM both then divide

ALIAS RULES:
- When aliasing tables, keep it simple and consistent
- After aliasing, ALWAYS use the alias for ALL column references
- Double-check every column reference matches its table alias
"""


def build_sql_prompt(query: str, schema_context: str, error_context: str = None) -> str:
    """Build the prompt for SQL generation."""
    prompt = f"""SCHEMA:
{schema_context}

USER QUESTION: {query}"""

    if error_context:
        prompt += f"""

PREVIOUS ATTEMPT FAILED WITH ERROR:
{error_context}

Fix the SQL to resolve this error. Return only the corrected SQL query."""

    return prompt


def parse_sql_response(response: str) -> str:
    """Clean LLM response to extract just the SQL."""
    sql = response.strip()

    # Remove markdown code fences
    if "```" in sql:
        lines = sql.split("\n")
        cleaned = []
        inside_fence = False
        for line in lines:
            if line.strip().startswith("```"):
                inside_fence = not inside_fence
                continue
            if inside_fence or not any(line.strip().startswith(x) for x in ["Here", "This", "The", "I "]):
                cleaned.append(line)
        sql = "\n".join(cleaned).strip()

    # Remove leading explanation lines
    lines = sql.split("\n")
    sql_start = 0
    for i, line in enumerate(lines):
        upper = line.strip().upper()
        if upper.startswith(("SELECT", "WITH")):
            sql_start = i
            break
    sql = "\n".join(lines[sql_start:]).strip()

    # Remove trailing semicolons
    sql = sql.rstrip(";").strip()

    return sql