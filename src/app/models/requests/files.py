from .serde_base import SerdeBase


class DownloadFileRequest(SerdeBase):
    uuid: str
    username: str  # Added to verify access permissions


class UploadFileRequest(SerdeBase):
    uuid: str
    username: str
    file_name: str  # Original filename from client
    file_content_b64: str  # Base64 encoded file content


class ShareFileRequest(SerdeBase):
    sharer_username: str
    recipient_username: str
    file_uuid: str
    sharer_identity_key_public: str  # Alice's public iKEK
    sharer_ephemeral_key_public: str  # Ephemeral key (random key that Alice generated during the secret derivation step)
    otp_hash: str  # Hash of the Bob's OT PreKey
    encrypted_dek: str  # eDEK (encrypted DEK)


class DeleteFileRequest(SerdeBase):
    uuid: str
    username: str


class ShareFileResponse(SerdeBase):
    message: str


class UploadFileResponse(SerdeBase):
    message: str
    file_uuid: str
    file_name: str
    size: int


class FileUploadData(SerdeBase):
    uuid: str
    username: str
