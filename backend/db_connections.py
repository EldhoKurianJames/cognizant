"""Manages ad-hoc SQLite database connections uploaded by users.

By default the app queries the database configured via DATABASE_URL (see
database.py). This module lets a user additionally upload their own SQLite
file and query that instead, without touching the DATABASE_URL flow at all.

Each upload gets a unique `connection_id`. The frontend passes that id back
on `/schema` and `/query` calls to target the uploaded file; omitting it
keeps using the default configured database. Connections are tracked
in-memory per backend process, so they reset if the server restarts (fine -
uploads are meant to be temporary/session-scoped, not a system of record).
"""

import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
SQLITE_MAGIC_HEADER = b"SQLite format 3\x00"


@dataclass
class UploadedConnection:
    connection_id: str
    filename: str
    path: Path
    engine: Engine
    created_at: float


_connections: dict[str, UploadedConnection] = {}


class InvalidDatabaseFileError(ValueError):
    pass


def _validate_sqlite_file(data: bytes) -> None:
    if len(data) < len(SQLITE_MAGIC_HEADER) or not data.startswith(SQLITE_MAGIC_HEADER):
        raise InvalidDatabaseFileError(
            "File does not look like a valid SQLite database (bad header)."
        )


def register_uploaded_db(file_bytes: bytes, filename: str) -> UploadedConnection:
    """Validate, persist, and open a read-only engine for an uploaded SQLite file."""
    if len(file_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise InvalidDatabaseFileError(
            f"File too large ({len(file_bytes)} bytes). Max is {MAX_UPLOAD_SIZE_BYTES} bytes."
        )
    _validate_sqlite_file(file_bytes)

    connection_id = uuid.uuid4().hex
    dest_path = UPLOAD_DIR / f"{connection_id}.db"
    dest_path.write_bytes(file_bytes)

    # Open read-only via SQLite's URI mode so uploaded files can never be
    # modified through this connection, no matter what SQL is executed.
    uri_path = quote(str(dest_path.resolve()))
    engine = create_engine(f"sqlite:///file:{uri_path}?mode=ro&uri=true", pool_pre_ping=True)

    connection = UploadedConnection(
        connection_id=connection_id,
        filename=filename,
        path=dest_path,
        engine=engine,
        created_at=time.time(),
    )
    _connections[connection_id] = connection
    return connection


def get_connection(connection_id: str) -> UploadedConnection:
    connection = _connections.get(connection_id)
    if connection is None:
        raise KeyError(f"Unknown or expired connection_id: {connection_id}")
    return connection


def get_engine_for_connection(connection_id: str | None, default_engine: Engine) -> Engine:
    """Resolve the engine to use: the uploaded DB if connection_id is given, else the default."""
    if connection_id is None:
        return default_engine
    return get_connection(connection_id).engine


def remove_connection(connection_id: str) -> None:
    connection = _connections.pop(connection_id, None)
    if connection is None:
        return
    connection.engine.dispose()
    connection.path.unlink(missing_ok=True)
