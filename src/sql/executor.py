"""
Executes validated SQL against the database via SQLAlchemy.
Returns a Pandas DataFrame or an error dict.
"""
import re
import pandas as pd
from sqlalchemy import create_engine, text


class SQLExecutor:
    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite:///{db_path}")

    def execute(self, sql: str) -> dict:
        """
        Run SQL, return results.
        Returns: {"success": bool, "data": DataFrame or None, "error": str or None, "row_count": int}
        """
        try:
            # Auto-fix common PostgreSQL syntax that LLMs generate
            sql = self._fix_sqlite_compat(sql)

            with self.engine.connect() as conn:
                df = pd.read_sql_query(text(sql), conn)

            return {
                "success": True,
                "data": df,
                "error": None,
                "row_count": len(df),
            }

        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e),
                "row_count": 0,
            }

    def _fix_sqlite_compat(self, sql: str) -> str:
        """Fix common PostgreSQL/MySQL syntax to SQLite equivalents."""
        # Fix ::DATE, ::TEXT, ::INTEGER etc.
        sql = re.sub(r'::(\w+)', r'', sql)

        # Fix EXTRACT(YEAR FROM col) -> strftime('%Y', col)
        sql = re.sub(
            r'EXTRACT\s*\(\s*YEAR\s+FROM\s+(\w+)\s*\)',
            r"CAST(strftime('%Y', \1) AS INTEGER)",
            sql, flags=re.IGNORECASE
        )
        sql = re.sub(
            r'EXTRACT\s*\(\s*MONTH\s+FROM\s+(\w+)\s*\)',
            r"CAST(strftime('%m', \1) AS INTEGER)",
            sql, flags=re.IGNORECASE
        )

        # Fix NOW() -> datetime('now')
        sql = re.sub(r'\bNOW\(\)', "datetime('now')", sql, flags=re.IGNORECASE)

        # Fix CURRENT_TIMESTAMP -> datetime('now')
        sql = re.sub(r'\bCURRENT_TIMESTAMP\b', "datetime('now')", sql, flags=re.IGNORECASE)

        # Fix ILIKE -> LIKE
        sql = re.sub(r'\bILIKE\b', 'LIKE', sql, flags=re.IGNORECASE)

        # Fix INTERVAL '10 days' -> nothing
        sql = re.sub(r"INTERVAL\s+'(\d+)\s+days?'", r"'\1 days'", sql, flags=re.IGNORECASE)

        # Fix BOOL/BOOLEAN -> INTEGER
        sql = re.sub(r'\bBOOLEAN\b', 'INTEGER', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\bBOOL\b', 'INTEGER', sql, flags=re.IGNORECASE)

        # Fix common hallucinated column names
        sql = self._fix_column_names(sql)

        return sql

    def _fix_column_names(self, sql: str) -> str:
        """Fix commonly hallucinated column names."""
        # products table: name -> product_name
        # Match p.name, products.name but NOT staff.name or s.name
        # Only fix when clearly referencing products table
        replacements = [
            # products.description or p.description -> product_name (when alias is products/p joined to products)
            (r'\bproducts\.name\b', 'products.product_name'),
            (r'\bproducts\.description\b', 'products.product_name'),
            # staff first_name/last_name -> name
            (r'\.first_name\b', '.name'),
            (r'\.last_name\b', '.name'),
            (r'\.staff_name\b', '.name'),
            # employee_id -> staff_id
            (r'\.employee_id\b', '.staff_id'),
            (r'\.emp_id\b', '.staff_id'),
            # recipe description -> recipe_name
            (r'\brecipes\.description\b', 'recipes.recipe_name'),
            (r'\brecipes\.name\b', 'recipes.recipe_name'),
        ]

        for pattern, replacement in replacements:
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)

        return sql

    def test_connection(self) -> bool:
        """Verify database is accessible."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False