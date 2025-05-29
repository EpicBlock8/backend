import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)
from fastapi import HTTPException

from app.shared.logger import Logger

logger = Logger(__name__).get_logger()


def signature_verify(public_key: Ed25519PublicKey, signature: str, data: str):
    # def verify_signature(self) -> None:
    """
    Verifies the Ed25519 signature of the payload.
    Raises HTTPException(400) if the signature is invalid.
    """
    logger.debug("Starting signature verification.")

    try:
        signature_bytes = base64.b64decode(signature)
        public_key.verify(signature_bytes, data.encode(encoding="UTF-8"))
    except InvalidSignature as e:
        logger.warning("Signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    logger.info("Signature verification successful.")
