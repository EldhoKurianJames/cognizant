import sqlparse

FORBIDDEN_KEYWORDS = [
    "DROP", "ALTER", "DELETE", "INSERT", "UPDATE", "CREATE TABLE",
    "TRUNCATE", "GRANT", "REVOKE",
]


def validate_sql(sql: str) -> bool:
    """Ensure the SQL is a single, safe, read-only SELECT statement."""
    sql_upper = sql.strip().upper()

    if not sql_upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed")

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            raise ValueError(f"Operation '{keyword}' is not allowed")

    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            raise ValueError("Invalid SQL syntax")
    except Exception as e:
        raise ValueError(f"SQL parse error: {str(e)}")

    statements = [s for s in parsed if str(s).strip().strip(";")]
    if len(statements) > 1:
        raise ValueError("Only a single SQL statement is allowed")

    return True
