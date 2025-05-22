from fastapi import APIRouter, Depends

from app.models.requests import DownloadFileRequest, SignedPayload
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint


@router.post("/files/download")
async def download_file(data=Depends(SignedPayload.unwrap(DownloadFileRequest))):  # noqa: B008
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
    print("RECEIVED Type:", type(data))
    print("RECEIVED Data:", data)
