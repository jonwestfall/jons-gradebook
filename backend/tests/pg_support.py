"""Helpers for tests that need a real PostgreSQL server.

These tests run only when TEST_DATABASE_URL points at a server where the user may
create databases, for example:

    TEST_DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/postgres pytest

Each database created here is a throwaway that is dropped afterwards.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

requires_postgres = pytest.mark.skipif(not TEST_DATABASE_URL, reason="set TEST_DATABASE_URL to run against PostgreSQL")


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "app" / "db" / "migrations"))
    config.attributes["database_url"] = database_url
    return config


@contextmanager
def throwaway_database(prefix: str = "gradebook_test") -> Generator[str, None, None]:
    server_url = make_url(TEST_DATABASE_URL)
    name = f"{prefix}_{uuid4().hex[:12]}"
    admin_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield server_url.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin_engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin_engine.dispose()
