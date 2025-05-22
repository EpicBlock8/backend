import logging

from fastapi import APIRouter
from sqlmodel import Session, select

from app.shared import Logger, load_config
from app.shared.db import engine
from app.shared.http import server_error_handler

from app.models.requests import DownloadFile

logger = Logger(__name__, level=logging.DEBUG).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint


@router.get("/files/download")
def download_file(data: DownloadFile): ...
