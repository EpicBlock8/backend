import logging

from fastapi import FastAPI
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine

from app.shared import Logger, load_config

logger = Logger(__name__, level=logging.DEBUG).get_logger()

app = FastAPI()
config = load_config()

engine: Engine = create_engine(config.database.path)
SQLModel.metadata.create_all(engine)
