from pydantic import BaseModel
from typing import List, Optional

class signed_prekey_push(BaseModel):
    username: str
    signed_prekey_public: bytes
    signed_prekey_signature: bytes
    
class otp_prekey_push(BaseModel):
    username: str
    pub_otps: List[bytes] # list of otp public keys


class GetPrekeyBundleRequest(BaseModel):
    username: str
    target_username: str


class PrekeyBundleResponse(BaseModel):
    identity_key: bytes
    signed_prekey: bytes
    signed_prekey_signature: bytes
    one_time_prekey: bytes
    one_time_prekey_hash: bytes


class ShareFileRequest(BaseModel):
    sharer_username: str
    recipient_username: str
    sharer_identity_key_public: bytes # Alice's public iKEK
    sharer_ephemeral_key_public: bytes # Ephemeral key (random key that Alice generated during the secret derivation step)
    otp_hash: bytes # Hash of the Bob's OT PreKey
    encrypted_dek: bytes # eDEK (encrypted DEK)


class ShareFileResponse(BaseModel):
    message: str


class InitialMessage(BaseModel):
    sharer_identity_key_public: bytes
    sharer_ephemeral_key_public: bytes
    otp_hash: bytes
    encrypted_dek: bytes


class GrabInitialMessagesRequest(BaseModel):
    username: str


class GrabInitialMessagesResponse(BaseModel):
    messages: List[InitialMessage]


    