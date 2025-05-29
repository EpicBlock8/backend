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
