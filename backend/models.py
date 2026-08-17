from typing import Any

from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    source: str  # "template" or "llm"


class ExecuteSQLRequest(BaseModel):
    sql: str


class ErrorResponse(BaseModel):
    detail: str
