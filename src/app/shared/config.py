from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING
from os import PathLike
from pathlib import Path

from pydantic import BaseModel, field_validator
from tomllib import load

DEFAULT_CONFIG_PATH = Path("config.toml")


class General(BaseModel):
    title: str


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
    docs: str
    logs: str


class Endpoint(BaseModel):
    ws_client: str

    post_metric: str
    get_metrics: str
    get_metric_by_id: str

    post_machine: str
    get_machines: str
    get_machine_by_id: str
    get_machine_metrics_by_id: str
    get_machine_metric_types_by_id: str
    get_machine_event_types_by_id: str

    get_machine_listener_by_id: str
    post_machine_trigger_by_id: str

    post_metric_type: str
    get_metric_types: str
    get_metric_type_by_id: str


class Network(BaseModel):
    host: str
    port: int
    reload: bool

class Client(BaseModel):
    measurements_per_second: int

class Config(BaseModel):
    general: General
    paths: Paths
    logging: Logging
    endpoint: Endpoint
    network: Network
    client: Client


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
