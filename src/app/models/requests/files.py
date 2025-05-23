from pydantic import BaseModel


class DownloadFileRequest(BaseModel):
    uuid: str
    username: str  # Added to verify access permissions


class UploadFileRequest(BaseModel):
    uuid: str
    username: str
    file_name: str  # Original filename from client
    file_content_b64: str  # Base64 encoded file content


class ShareFileRequest(BaseModel):
    sharer_username: str
    recipient_username: str
    file_uuid: str
    sharer_identity_key_public: str  # Alice's public iKEK
    sharer_ephemeral_key_public: str  # Ephemeral key (random key that Alice generated during the secret derivation step)
    otp_hash: str  # Hash of the Bob's OT PreKey
    encrypted_dek: str  # eDEK (encrypted DEK)


class ShareFileResponse(BaseModel):
    message: str


class UploadFileResponse(BaseModel):
    message: str
    file_uuid: str
    file_name: str
    size: int


class FileUploadData(BaseModel):
    uuid: str
    username: str
