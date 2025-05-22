from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.requests import SignedPayload
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint


class MyEndpointRequest(BaseModel): ...


@router.post(endpoint.my_endpoint)
async def my_endpoint(data=Depends(SignedPayload.unwrap(MyEndpointRequest))):  # noqa: B008
    ...
