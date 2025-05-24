from .base import BaseRequest


class SignedPrekeyPush(BaseRequest):
    username: str
    signed_prekey_public: str
    signed_prekey_signature: str


class OtpPrekeyPush(BaseRequest):
    username: str
    pub_otps: list[str]  # list of otp public keys


class GetPrekeyBundleRequest(BaseRequest):
    username: str
    target_username: str


class PrekeyBundleResponse(BaseRequest):
    identity_key: str
    signed_prekey: str
    signed_prekey_signature: str
    one_time_prekey: str


class ReturnMessage(BaseRequest):
    sharer_identity_key_public: str
    sharer_ephemeral_key_public: str
    otp_hash: str
    encrypted_dek: str


class GrabReturnMessagesRequest(BaseRequest):
    username: str


class GrabReturnMessages(BaseRequest):
    messages: list[ReturnMessage]
