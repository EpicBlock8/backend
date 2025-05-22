import logging

from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

from app.models.schema import *  # noqa: F403 # SQLModel subclasses need to be in memory
from app.shared import Logger, load_config

logger = Logger(__name__, level=logging.DEBUG).get_logger()

config = load_config()

engine: Engine = create_engine(config.database.path)
SQLModel.metadata.create_all(engine)
