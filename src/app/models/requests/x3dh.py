from .serde_base import SerdeBase


class SignedPrekeyPush(SerdeBase):
    username: str
    signed_prekey_public: str
    signed_prekey_signature: str


class OtpPrekeyPush(SerdeBase):
    username: str
    pub_otps: list[str]  # list of otp public keys


class PQSignedPrekeyPush(SerdeBase):
    """Post-quantum signed prekey push for PQXDH last-resort KEM prekey"""
    username: str
    pq_signed_prekey_public: str  # base64-encoded KEM last-resort public key
    pq_signed_prekey_signature: str  # base64-encoded signature


class PQOtpData(SerdeBase):
    """Individual PQ OTP entry with public key and signature."""
    public_key: str
    signature: str


class PQOtpPrekeyPush(SerdeBase):
    """Post-quantum one-time prekey push for PQXDH"""
    username: str
    pub_pq_otps: list[PQOtpData]


class GetPrekeyBundleRequest(SerdeBase):
    username: str
    target_username: str


class PrekeyBundleResponse(SerdeBase):
    # Classical X3DH fields
    identity_key: str
    signed_prekey: str
    signed_prekey_signature: str
    one_time_prekey: str
    
    # Post-quantum PQXDH fields
    pq_signed_prekey: str  # base64(KEM last-resort public key)
    pq_signed_prekey_signature: str  # base64(signature on that key)
    
    one_time_pq_prekey: str | None = None  # base64(one-time KEM public key)
    one_time_pq_prekey_signature: str | None = None  # base64(signature on one-time key)


class ReturnMessage(SerdeBase):
    # Classical X3DH fields
    sharer_identity_key_public: str
    sharer_ephemeral_key_public: str
    sharer_username: str
    otp_hash: str
    encrypted_message: str
    
    # Post-quantum PQXDH fields
    kem_ciphertext: str  # base64(KEM ciphertext CT)
    pq_otp_hash: str  # hash of the PQ OTP used


class PostReturnMessage(SerdeBase):
    # Classical X3DH fields
    sharer_username: str
    recipient_username: str
    sharer_identity_key_public: str  # Alice's public iKEK
    sharer_ephemeral_key_public: str  # Ephemeral key (random key that Alice generated during the secret derivation step)
    otp_hash: str  # Hash of the Bob's OT PreKey
    encrypted_message: str  # eMessage (encrypted message)
    
    # Post-quantum PQXDH fields
    kem_ciphertext: str  # base64(KEM ciphertext CT)
    pq_otp_hash: str  # hash of the PQ OTP used

    
class PostReturnMessageResponse(SerdeBase):
    message: str


class GrabReturnMessagesRequest(SerdeBase):
    username: str


class GrabReturnMessages(SerdeBase):
    messages: list[ReturnMessage]
