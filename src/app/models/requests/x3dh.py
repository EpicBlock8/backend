from pydantic import BaseModel


class SignedPrekeyPush(BaseModel):
    username: str
    signed_prekey_public: str
    signed_prekey_signature: str


class OtpPrekeyPush(BaseModel):
    username: str
    pub_otps: list[str]  # list of otp public keys


class GetPrekeyBundleRequest(BaseModel):
    username: str
    target_username: str


class PrekeyBundleResponse(BaseModel):
    identity_key: str
    signed_prekey: str
    signed_prekey_signature: str
    one_time_prekey: str
    one_time_prekey_hash: str


class InitialMessage(BaseModel):
    sharer_identity_key_public: str
    sharer_ephemeral_key_public: str
    otp_hash: str
    encrypted_dek: str


class GrabInitialMessagesRequest(BaseModel):
    username: str


class GrabInitialMessagesResponse(BaseModel):
    messages: list[InitialMessage]
