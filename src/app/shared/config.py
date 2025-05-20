from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from os import PathLike
from pathlib import Path
from tomllib import load

from pydantic import BaseModel, field_validator

DEFAULT_CONFIG_PATH = Path("config.toml")


class General(BaseModel):
    title: str


class Database(BaseModel):
    path: str


class Logging(BaseModel):
    level: int

    @field_validator("level", mode="before")
    @classmethod
    def convert_log_level(cls, value):
        log_levels = {
            "DEBUG": DEBUG,
            "INFO": INFO,
            "WARNING": WARNING,
            "ERROR": ERROR,
            "CRITICAL": CRITICAL,
        }
        return log_levels.get(value.upper(), INFO)


class Paths(BaseModel):
    logs: str


class Endpoint(BaseModel):
    # ws_client: str
    ...


class Network(BaseModel):
    host: str
    port: int
    reload: bool


class Config(BaseModel):
    general: General
    database: Database
    paths: Paths
    logging: Logging
    endpoint: Endpoint
    network: Network


def load_config(
    shared_config_file: PathLike = DEFAULT_CONFIG_PATH,
    specific_config_file: PathLike | None = None,
) -> Config:
    """Load and merge configurations from TOML files."""
    # Load shared config
    with Path(shared_config_file).open("rb") as f:
        config_data = load(f)

    # Load and merge specific config if provided
    if specific_config_file:
        with Path(specific_config_file).open("rb") as f:
            specific_data = load(f)
            # Using update() instead of dictionary unpacking
            config_data.update(specific_data)

    return Config(**config_data)
