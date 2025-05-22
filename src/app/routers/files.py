import logging

from fastapi import APIRouter, Depends

from app.models.requests import DownloadFile
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint


@router.get("/files/download")
async def download_file(data: DownloadFile = Depends()):
    """
    download_file
        sending UUID
        ===============
        verify signature
        verify ability to access (are they owner / has it been shared?)
        send encrypted file body.
        ================
        decrypt DEK
        decrypt body
    """
    data_copy = data.model_copy()
    del data_copy["signature"]
    logger.debug(data.model_dump_json())



