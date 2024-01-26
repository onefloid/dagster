import os
import sqlite3
import tempfile

import pytest
from dagster import file_relative_path
from dagster_embedded_elt.sling import (
    SlingConnectionResource,
    SlingResource,
    SlingSourceConnection,
    SlingTargetConnection,
)


@pytest.fixture
def test_csv():
    return os.path.abspath(file_relative_path(__file__, "test.csv"))


@pytest.fixture
def test_staging_csv():
    return os.path.abspath(file_relative_path(__file__, "staging_test.csv"))


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir_path:
        dbpath = os.path.join(tmpdir_path, "sqlite.db")
        yield dbpath


@pytest.fixture
def sling_sqlite_resource(temp_db):
    return SlingResource(
        source_connection=SlingSourceConnection(type="file"),
        target_connection=SlingTargetConnection(
            type="sqlite", connection_string=f"sqlite://{temp_db}"
        ),
    )


@pytest.fixture
def sling_file_connection():
    return SlingConnectionResource(type="file")


@pytest.fixture
def sling_staging_file_connection():
    return SlingConnectionResource(type="file")


@pytest.fixture
def sling_sqlite_connection(temp_db):
    return SlingConnectionResource(type="sqlite", connection_string=f"sqlite://{temp_db}")


@pytest.fixture
def sqlite_connection(temp_db):
    yield sqlite3.connect(temp_db)
