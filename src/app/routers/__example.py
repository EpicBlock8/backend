# type: ignore
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.models.requests import SignedPayload
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint


class MyEndpointRequest(BaseModel): ...


@router.post("/")
async def my_endpoint(
    data: Annotated[
        MyEndpointRequest, Depends(SignedPayload.unwrap(MyEndpointRequest))
    ],
): ...


raise ImportError(
    "\nThis module should never be imported directly."
    "\nInstead, copy this file and use it as a template."
    "\nRemove this line afterwards."
)
