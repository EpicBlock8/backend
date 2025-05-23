import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException, Request
from pydantic import BaseModel

from app.core.verify import verify
from app.shared import Logger

logger = Logger(__name__).get_logger()

T = TypeVar("T")


def db_get_public_key(username: str):
    # TODO: Replace with real public key retrieval logic
    private_bytes = (b"hello world" * 3)[:32]
    private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    public_key = private_key.public_key()
    return public_key


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
                public_key = db_get_public_key(signed.username)
                try:
                    verify(
                        public_key=public_key,
                        signature=signed.signature,
                        data=signed.payload,
                    )
                except HTTPException as e:
                    # TODO: DO NOT PUSH TO PROD OR I WILL KILL SOMEONE
                    logger.warning(
                        "Signature verification failed (IGNORING DEBUG!! DO NOT USE IN PROD): %s",
                        e,
                    )
                    # raise HTTPException(status_code=400, detail="Invalid signature") from e

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
