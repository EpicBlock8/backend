from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app
from app.models.requests import DownloadFileRequest, SignedPayload

client = TestClient(app)

private_bytes = (b"hello world" * 3)[:32]
private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
public_key = private_key.public_key()


def sign_packet(payload: BaseModel) -> SignedPayload:
    payload_json: str = payload.model_dump_json()
    payload_json_bytes: bytes = payload_json.encode()
    signature_bytes: bytes = private_key.sign(payload_json_bytes)
    signature_hex: str = signature_bytes.hex()
    return SignedPayload(payload=payload_json, signature=signature_hex)


def test_download_file():
    # This just shouldnt crash
    payload = DownloadFileRequest(uuid="i am a uuid")
    payload_signed = sign_packet(payload)
    print("THIS IS OUR PAYLOAD BEFORE SENDING:", payload_signed)

    _ = client.post("/files/download", json=payload_signed.model_dump())
    print(_)
