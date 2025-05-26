from .serde_base import SerdeBase


class SignedPrekeyPush(SerdeBase):
    username: str
    signed_prekey_public: str
    signed_prekey_signature: str


class OtpPrekeyPush(SerdeBase):
    username: str
    pub_otps: list[str]  # list of otp public keys


class GetPrekeyBundleRequest(SerdeBase):
    username: str
    target_username: str


class PrekeyBundleResponse(SerdeBase):
    identity_key: str
    signed_prekey: str
    signed_prekey_signature: str
    one_time_prekey: str


class ReturnMessage(SerdeBase):
    sharer_identity_key_public: str
    sharer_ephemeral_key_public: str
    sharer_username: str
    otp_hash: str
    encrypted_dek: str


class GrabReturnMessagesRequest(SerdeBase):
    username: str


class GrabReturnMessages(SerdeBase):
    messages: list[ReturnMessage]
