from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.models.schema import User
from app.shared.db import engine


def test_db_engine_exists():
    """
    Test that the database engine is created.
    """
    assert engine is not None
    assert isinstance(engine, Engine)


def test_db_schema():
    database_uri = "sqlite:///test_database.db"
    engine = create_engine(database_uri)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Add default metric types if they don't exist
        # session.add(User(username="bob dylan", public_key=b"hehahahahahaha", ))
        session.commit()
