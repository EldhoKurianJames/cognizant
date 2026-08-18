"""Computes a stable fingerprint of the tables referenced by a SQL query.

The fingerprint (schema hash) is used to automatically invalidate cached SQL
queries whenever the underlying database schema changes (columns added,
removed, renamed, retyped, or tables dropped/renamed). Pure data changes
(rows inserted/updated/deleted) do not affect the hash, so the cache remains
valid across normal data changes.
"""

import hashlib

import sqlparse
from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def extract_schema_from_database(engine: Engine) -> dict[str, list[tuple[str, str]]]:
    """Introspect the database and return {table_name: [(column_name, column_type), ...]}."""
    inspector = inspect(engine)
    schema: dict[str, list[tuple[str, str]]] = {}
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        schema[table_name] = [(col["name"], str(col["type"])) for col in columns]
    return schema


def extract_tables_from_sql(sql_query: str) -> list[str]:
    """Extract table names referenced in FROM/JOIN clauses of a SQL query."""
    tables: list[str] = []
    expect_table = False

    for statement in sqlparse.parse(sql_query):
        for token in statement.flatten():
            if token.is_whitespace:
                continue

            if token.ttype is sqlparse.tokens.Keyword:
                upper = token.value.upper()
                if upper == "FROM" or upper.endswith("JOIN"):
                    expect_table = True
                    continue
                if upper == "AS":
                    # table alias follows; not a table name, keep expect_table False
                    continue
                # Any other keyword ends the "expecting a table name" state.
                expect_table = False
                continue

            if expect_table:
                if token.ttype in (sqlparse.tokens.Name, sqlparse.tokens.Literal.String.Symbol, None):
                    name = token.value.strip().strip('"').strip("`").strip("'")
                    if name and name != ",":
                        tables.append(name.split(".")[-1])
                expect_table = False

    # De-duplicate while preserving order (case-insensitive).
    seen: set[str] = set()
    unique_tables: list[str] = []
    for table in tables:
        key = table.lower()
        if key not in seen:
            seen.add(key)
            unique_tables.append(table)
    return unique_tables


def extract_relevant_schema(full_schema: dict[str, list[tuple[str, str]]], table_names: list[str]) -> str:
    """Build a deterministic string representation of only the referenced tables' schema."""
    lower_lookup = {name.lower(): name for name in full_schema}
    parts = []

    for table_name in sorted(table_names, key=str.lower):
        actual_name = lower_lookup.get(table_name.lower())
        if actual_name is None:
            # Table no longer exists (dropped/renamed) - encode that as a distinct marker
            # so the hash changes and the cache gets invalidated.
            parts.append(f"{table_name}[MISSING]")
            continue
        columns = full_schema[actual_name]
        cols_str = ",".join(f"{name}({dtype})" for name, dtype in columns)
        parts.append(f"{actual_name}[{cols_str}]")

    return "|".join(parts)


def compute_schema_hash(schema_string: str) -> str:
    """Hash a schema string. Identical input always yields identical output."""
    return hashlib.sha256(schema_string.encode("utf-8")).hexdigest()


def get_schema_hash_for_query(sql_query: str, engine: Engine) -> str:
    """Compute the schema fingerprint for the tables referenced by `sql_query`."""
    full_schema = extract_schema_from_database(engine)
    tables = extract_tables_from_sql(sql_query)
    relevant_schema = extract_relevant_schema(full_schema, tables)
    return compute_schema_hash(relevant_schema)
