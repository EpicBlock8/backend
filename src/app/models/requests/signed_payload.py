import base64
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import HTTPException, Request
from pydantic import BaseModel


class SignedPayload(BaseModel):
    payload: str  # minified JSON as a string
    signature: str  # base64-encoded signature

    def verify_signature(self) -> None:
        # Load the public key (replace this with your real key loading logic)
        # COMMENT: insert code here to get your Ed25519PublicKey
        public_key = Ed25519PublicKey.from_public_bytes(b"...")  # placeholder

        # Verify signature
        signature = base64.b64decode(self.signature_)
        try:
            public_key.verify(signature, self.payload.encode("utf-8"))
        except InvalidSignature as e:
            raise HTTPException(status_code=400, detail="Invalid signature") from e

async def parse_signed_payload(request: Request) -> DownloadFile:
    try:
        body = await request.json()
        signed = SignedPayload(**body)
        signed.verify_signature()
        payload_data = json.loads(signed.payload)
        return DownloadFile(**payload_data)
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
