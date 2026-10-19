import sqlite3

import pytest

pytest.importorskip("sqlalchemy")

from DataElevate import InvalidInput, Load_data  # noqa: E402


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "data.db"
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE users (id INTEGER, name TEXT);"
        "INSERT INTO users VALUES (1, 'a'), (2, 'b');"
        'CREATE TABLE "odd name" (x INTEGER); INSERT INTO "odd name" VALUES (7);'
    )
    con.commit()
    con.close()
    return path


def test_load_table(db):
    df = Load_data.Database.from_sqlite(str(db), "users")
    assert df["name"].tolist() == ["a", "b"]


def test_readme_alias(db):
    assert len(Load_data.Database.sqlite(db_name=str(db), table_name="users")) == 2


def test_table_name_with_space(db):
    assert Load_data.Database.from_sqlite(db, "odd name")["x"].tolist() == [7]


def test_custom_query_with_params(db):
    df = Load_data.Database.from_sqlite(db, query="SELECT name FROM users WHERE id = :id",
                                        params={"id": 2})
    assert df["name"].tolist() == ["b"]


def test_sql_injection_in_table_name_is_blocked(db):
    with pytest.raises(InvalidInput):
        Load_data.Database.from_sqlite(db, "users; DROP TABLE users")
    assert len(Load_data.Database.from_sqlite(db, "users")) == 2  # table still there


def test_needs_table_or_query(db):
    with pytest.raises(InvalidInput):
        Load_data.Database.from_sqlite(db)
    with pytest.raises(InvalidInput):
        Load_data.Database.from_sqlite(db, "users", query="SELECT 1")


def test_missing_sqlite_file_is_not_created(tmp_path):
    missing = tmp_path / "missing.db"
    with pytest.raises(InvalidInput):
        Load_data.Database.from_sqlite(missing, "users")
    assert not missing.exists()


def test_from_url(db):
    df = Load_data.Database.from_url(f"sqlite:///{db.as_posix()}", "users")
    assert len(df) == 2


def test_password_special_characters_are_escaped():
    pytest.importorskip("psycopg2")
    engine = Load_data.Database._engine(
        "postgresql+psycopg2", "psycopg2", "psycopg2-binary", "db",
        "mydb", "user", "p@ss:w/rd#1", "db.example.com", 5432)
    url = engine.url
    assert url.password == "p@ss:w/rd#1" and url.host == "db.example.com"
    assert "p@ss" not in repr(url)  # password masked in logs/reprs


def test_rds_engine_validation():
    with pytest.raises(InvalidInput):
        Load_data.Database.from_amazon_rds("db", "t", "u", "p", "h", engine="sqlserver")
