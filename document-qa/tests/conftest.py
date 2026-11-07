"""Shared fixtures: app clients with mock providers, memory and Postgres backends.

Postgres-backed tests run only when TEST_DATABASE_URL is set (CI provides a
pgvector service container); otherwise they are skipped, not failed.
"""

import asyncio
import os
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict

from app.config import DEFAULT_MIGRATIONS_DIR, Settings, StoreBackend
from app.main import create_app
from app.store.postgres import run_migrations

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
BACKENDS = [StoreBackend.MEMORY, StoreBackend.POSTGRES]


def _assert_disposable(dsn: str) -> None:
    """Tests TRUNCATE every table. Refuse any database not explicitly named *_test,
    so a wrong port or an SSH tunnel can never point them at real data."""
    dbname = conninfo_to_dict(dsn).get("dbname", "")
    if not str(dbname).endswith("_test"):
        pytest.exit(
            f"TEST_DATABASE_URL must point to a database named *_test, got {dbname!r}. "
            "Refusing to truncate it.",
            returncode=2,
        )


def _reset_database(dsn: str) -> None:
    _assert_disposable(dsn)
    asyncio.run(run_migrations(dsn, DEFAULT_MIGRATIONS_DIR))
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("TRUNCATE documents, chunks, sessions, messages CASCADE")


def backend_settings(backend: StoreBackend, **overrides: Any) -> Settings:
    if backend is StoreBackend.POSTGRES:
        if not TEST_DATABASE_URL:
            pytest.skip("TEST_DATABASE_URL not set")
        _reset_database(TEST_DATABASE_URL)
        overrides.setdefault("database_url", TEST_DATABASE_URL)
    return Settings(_env_file=None, store_backend=backend, **overrides)  # type: ignore[call-arg]


MakeClient = Callable[..., TestClient]


@pytest.fixture
def make_client() -> Iterator[MakeClient]:
    clients: list[TestClient] = []

    def _make(backend: StoreBackend = StoreBackend.MEMORY, **overrides: Any) -> TestClient:
        client = TestClient(create_app(backend_settings(backend, **overrides)))
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client: MakeClient) -> TestClient:
    return make_client()


@pytest.fixture(params=BACKENDS, ids=lambda b: b.value)
def backend(request: pytest.FixtureRequest) -> StoreBackend:
    return StoreBackend(request.param)


@pytest.fixture
def any_client(make_client: MakeClient, backend: StoreBackend) -> TestClient:
    """The same API test, run against every store backend."""
    return make_client(backend)