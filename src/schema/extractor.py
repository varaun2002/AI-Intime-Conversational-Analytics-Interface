"""
Reads SQLite database schema — table names, columns, types,
foreign keys, and sample values. Outputs a dict per table.
"""
import sqlite3


def extract_schema(db_path: str) -> dict:
    """Extract full schema info from SQLite database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all table names
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]

    schema = {}

    for table in tables:
        # Column info
        cur.execute(f"PRAGMA table_info({table})")
        columns = []
        for col in cur.fetchall():
            columns.append({
                "name": col[1],
                "type": col[2],
                "notnull": bool(col[3]),
                "primary_key": bool(col[5]),
            })

        # Foreign keys
        cur.execute(f"PRAGMA foreign_key_list({table})")
        foreign_keys = []
        for fk in cur.fetchall():
            foreign_keys.append({
                "from_column": fk[3],
                "to_table": fk[2],
                "to_column": fk[4],
            })

        # Row count
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cur.fetchone()[0]

        # Sample values (first 3 rows)
        cur.execute(f"SELECT * FROM {table} LIMIT 3")
        sample_rows = cur.fetchall()
        col_names = [c["name"] for c in columns]

        # Build text description for search matching
        description = _build_description(table, columns, foreign_keys, col_names, sample_rows)

        schema[table] = {
            "table_name": table,
            "columns": columns,
            "foreign_keys": foreign_keys,
            "row_count": row_count,
            "column_names": col_names,
            "sample_rows": sample_rows,
            "description": description,
        }

    conn.close()
    return schema


def _build_description(table, columns, foreign_keys, col_names, sample_rows) -> str:
    """Build a rich text description of a table for search matching."""
    parts = [f"Table: {table}"]

    # Column descriptions
    col_parts = []
    for c in columns:
        pk = " (PRIMARY KEY)" if c["primary_key"] else ""
        col_parts.append(f"{c['name']} {c['type']}{pk}")
    parts.append("Columns: " + ", ".join(col_parts))

    # Foreign keys
    if foreign_keys:
        fk_parts = [f"{fk['from_column']} -> {fk['to_table']}.{fk['to_column']}" for fk in foreign_keys]
        parts.append("Foreign Keys: " + ", ".join(fk_parts))

    # Sample values
    if sample_rows:
        for row in sample_rows[:2]:
            row_str = " | ".join(str(v) for v in row)
            parts.append(f"Sample: {row_str}")

    return " . ".join(parts)


def get_schema_context(schema: dict, table_names: list) -> str:
    """Build a prompt-ready schema string for specific tables."""
    context_parts = []

    for table_name in table_names:
        if table_name not in schema:
            continue
        info = schema[table_name]
        lines = [f"TABLE: {table_name} ({info['row_count']} rows)"]

        for col in info["columns"]:
            pk = " [PK]" if col["primary_key"] else ""
            lines.append(f"  - {col['name']} ({col['type']}){pk}")

        for fk in info["foreign_keys"]:
            lines.append(f"  FK: {fk['from_column']} -> {fk['to_table']}.{fk['to_column']}")

        if info["sample_rows"]:
            lines.append(f"  Sample row: {dict(zip(info['column_names'], info['sample_rows'][0]))}")

        context_parts.append("\n".join(lines))

    # Add explicit JOIN guide
    join_guide = """
JOIN GUIDE (use these exact patterns):
- shift_logs -> production_orders: production_orders.shift_id = shift_logs.shift_id
- production_orders -> production_steps: production_steps.order_id = production_orders.order_id
- production_orders -> products: production_orders.product_id = products.product_id
- production_orders -> recipes: production_orders.recipe_id = recipes.recipe_id
- production_orders -> line_master: production_orders.line_id = line_master.line_id
- shift_logs -> staff (supervisor): shift_logs.supervisor_id = staff.staff_id
- production_steps -> staff (operator): production_steps.operator_id = staff.staff_id

IMPORTANT: production_steps connects to shift_logs ONLY through production_orders.
Never join production_steps directly to shift_logs."""

    context_parts.append(join_guide)

    return "\n\n".join(context_parts)