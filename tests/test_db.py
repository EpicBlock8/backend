from sqlalchemy import Engine

from app.shared.db import engine


def test_db_engine_exists():
    """
    Test that the database engine is created.
    """
    assert engine is not None
    assert isinstance(engine, Engine) 