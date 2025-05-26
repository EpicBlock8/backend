import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.verify import verify
from app.models.schema import User
from app.shared import Logger
from app.shared.db import engine

logger = Logger(__name__).get_logger()

T = TypeVar("T")


class SignedPayload(BaseModel):
    payload: str  # JSON string payload (minified)
    signature: str  # Base64-encoded signature
    username: str  # Plaintext string of username

    @classmethod
    def unwrap(cls, output_type: type[T]) -> Callable[[Request], Awaitable[T]]:
        """
        Factory method that returns an async function to:
        - Parse a SignedPayload from the request
        - Verify its signature
        - Decode and load the payload as an instance of `output_type`
        """
        logger.debug(
            "Creating unwrap handler for output type: %s", output_type.__name__
        )

        async def handler(request: Request) -> T:
            logger.debug("Handling unwrap request.")
            try:
                body = await request.json()
                logger.debug("Request JSON body parsed successfully.")

                signed = cls(**body)

                with Session(engine) as session:
                    # Get user and ensure it exists
                    user = session.exec(
                        select(User).where(User.username == signed.username)
                    ).first()
                    if user is None:
                        raise HTTPException(
                            status_code=404,
                            detail="User does not exists",
                        )
                    public_key = Ed25519PublicKey.from_public_bytes(user.public_key)

                verify(
                    public_key=public_key,
                    signature=signed.signature,
                    data=signed.payload,
                )

                payload_data = json.loads(signed.payload)
                logger.debug("Payload successfully decoded: %s", payload_data)

                result = output_type(**payload_data)
                logger.info(
                    "Unwrapped payload into %s instance successfully.",
                    output_type.__name__,
                )
                return result

            except (ValueError, json.JSONDecodeError) as e:
                logger.warning("Failed to unwrap payload: %s", e)
                raise HTTPException(
                    status_code=400, detail=f"Invalid payload: {e}"
                ) from e

        return handler
