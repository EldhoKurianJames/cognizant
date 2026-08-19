import sqlparse

WRITE_COMMANDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "VACUUM",
}


def _get_statement_keywords(stmt: sqlparse.sql.Statement) -> list[str]:
    keywords: list[str] = []
    for token in stmt.flatten():
        if token.is_whitespace or token.ttype in (
            sqlparse.tokens.Comment,
            sqlparse.tokens.Comment.Single,
            sqlparse.tokens.Comment.Multiline,
        ):
            continue
        if token.ttype in (
            sqlparse.tokens.Keyword,
            sqlparse.tokens.Keyword.DML,
            sqlparse.tokens.Keyword.DDL,
        ) or (token.ttype is None and token.value.upper() in WRITE_COMMANDS):
            keywords.append(token.value.upper())
    return keywords


def is_write_query(sql: str) -> bool:
    """Return True if the SQL contains any write / DDL statement."""
    if not sql or not sql.strip():
        return False

    parsed = [s for s in sqlparse.parse(sql) if str(s).strip().strip(";")]
    if not parsed:
        return False

    for stmt in parsed:
        stmt_type = stmt.get_type()
        if stmt_type in ("INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER", "TRUNCATE"):
            return True
        keywords = _get_statement_keywords(stmt)
        if any(kw in WRITE_COMMANDS for kw in keywords):
            return True
    return False


def validate_sql(sql: str) -> bool:
    """Ensure the SQL is a single, safe, read-only SELECT statement."""
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty")

    try:
        parsed = [s for s in sqlparse.parse(sql) if str(s).strip().strip(";")]
        if not parsed:
            raise ValueError("Invalid SQL syntax")
    except Exception as e:
        raise ValueError(f"SQL parse error: {str(e)}")

    if len(parsed) > 1:
        raise ValueError("Only a single SQL statement is allowed")

    if is_write_query(sql):
        raise ValueError("Only read-only SELECT queries are allowed")

    stmt = parsed[0]
    stmt_type = stmt.get_type()

    # Find the first significant token (ignoring comments/whitespace)
    first_non_ws = None
    for token in stmt.flatten():
        if not token.is_whitespace and token.ttype not in (
            sqlparse.tokens.Comment,
            sqlparse.tokens.Comment.Single,
            sqlparse.tokens.Comment.Multiline,
        ):
            first_non_ws = token.value.upper()
            break

    if stmt_type != "SELECT" and first_non_ws not in ("SELECT", "WITH"):
        raise ValueError("Only SELECT queries are allowed")

    return True
