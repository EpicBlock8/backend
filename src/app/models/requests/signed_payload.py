import json
from collections.abc import Awaitable, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.verify import signature_verify
from app.models.schema import User
from app.shared import Logger
from app.shared.db import engine

logger = Logger(__name__).get_logger()

type UnwrapHandler[T] = Callable[[Request], Awaitable[T]]


class SignedPayload[T: BaseModel](BaseModel):
    payload: str  # JSON string payload (minified)
    signature: str  # Base64-encoded signature
    username: str  # Plaintext string of username

    @classmethod
    def unwrap(cls, output_type: T) -> UnwrapHandler[T]:
        return cls._create_handler(output_type, verify_signature=True)

    @classmethod
    def unwrap_no_checks(cls, output_type: T) -> UnwrapHandler[T]:
        return cls._create_handler(output_type, verify_signature=False)

    @classmethod
    def _create_handler(
        cls,
        output_type: T,
        verify_signature: bool,
    ) -> UnwrapHandler[T]:
        logger.debug(
            "Creating unwrap handler for output type: %s (verify: %s)",
            output_type.__name__,
            verify_signature,
        )

        async def unwrap_handler(request: Request) -> T:
            logger.debug("Handling unwrap request.")
            try:
                signed_payload = cls.model_validate(await request.json())
                logger.debug("Request JSON body parsed successfully.")

                if verify_signature:
                    signed_payload.verify()

                payload_data = json.loads(signed_payload.payload)
                logger.debug("Payload successfully decoded: %s", payload_data)

                result = output_type.model_validate(payload_data)
                logger.info(
                    "Unwrapped payload into %s instance successfully.",
                    output_type.__name__,
                )
                return result

            except (ValueError, json.JSONDecodeError) as e:
                logger.warning("Failed to unwrap payload: %s", e)
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid payload: {e}",
                ) from e

        return unwrap_handler

    def verify(self):
        with Session(engine) as session:
            statement = select(User).where(User.username == self.username)
            user = session.exec(statement).first()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User does not exists",
            )

        public_key = Ed25519PublicKey.from_public_bytes(user.public_key)

        signature_verify(
            public_key=public_key,
            signature=self.signature,
            data=self.payload,
        )
