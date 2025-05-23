
from pydantic import BaseModel


class SignedPrekeyPush(BaseModel):
    username: str
    signed_prekey_public: bytes
    signed_prekey_signature: bytes

class OtpPrekeyPush(BaseModel):
    username: str
    pub_otps: list[bytes] # list of otp public keys


class GetPrekeyBundleRequest(BaseModel):
    username: str
    target_username: str


class PrekeyBundleResponse(BaseModel):
    identity_key: bytes
    signed_prekey: bytes
    signed_prekey_signature: bytes
    one_time_prekey: bytes
    one_time_prekey_hash: bytes

class InitialMessage(BaseModel):
    sharer_identity_key_public: bytes
    sharer_ephemeral_key_public: bytes
    otp_hash: bytes
    encrypted_dek: bytes


class GrabInitialMessagesRequest(BaseModel):
    username: str


class GrabInitialMessagesResponse(BaseModel):
    messages: list[InitialMessage]


