import os
import base64
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File as FastAPIFile, Form
from fastapi.responses import FileResponse
from sqlmodel import Session, create_engine, select

from app.models.requests import DownloadFileRequest, SignedPayload, UploadFileRequest, UploadFileResponse
from app.models.requests.files import ShareFileRequest, ShareFileResponse, FileUploadData
from app.models.schema import MessageStore, User, File, FileShare
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint
engine = create_engine(config.database.path)

# Create uploads directory if it doesn't exist
uploads_dir = Path(config.paths.files)
uploads_dir.mkdir(exist_ok=True)
logger.info(f"Files will be stored in: {uploads_dir.absolute()}")


@router.post("/files/upload", response_model=UploadFileResponse)
async def upload_file(
    data: UploadFileRequest = Depends(SignedPayload.unwrap(UploadFileRequest))
):
    """
    Upload a file via JSON payload. The file content is Base64 encoded.
    
    JSON payload should include:
    - uuid: Unique identifier for the file - check first...
    - username: Username of the file owner
    - file_name: Original filename
    - file_content_b64: Base64 encoded file content
    """
    logger.debug(f"Uploading file: {data.file_name} for user: {data.username}, UUID: {data.uuid}")
    
    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {data.username} not found")
        
        # Check if file UUID already exists
        existing_file = session.exec(select(File).where(File.uuid == data.uuid)).first()
        if existing_file:
            raise HTTPException(status_code=409, detail=f"File with UUID {data.uuid} already exists")
        
        # Decode Base64 file content
        try:
            file_content = base64.b64decode(data.file_content_b64)
            file_size = len(file_content)
            logger.info(f"Decoded {file_size} bytes from Base64 input for file: {data.file_name}")
        except Exception as e:
            logger.error(f"Failed to decode Base64 content: {e}")
            raise HTTPException(status_code=400, detail="Invalid Base64 content")
        
        # Create file path using UUID
        file_path = uploads_dir / f"{data.uuid}"
        
        # Save file to disk
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info(f"File saved to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save file to disk: {e}")
            raise HTTPException(status_code=500, detail="Failed to save file")
        
        # Create database record
        new_file = File(
            uuid=data.uuid,
            file_name=data.file_name or "unknown",
            size=file_size,
            date_created=datetime.utcnow(),
            owner_username=data.username
        )
        
        session.add(new_file)
        session.commit()
        session.refresh(new_file)
        
        logger.info(f"File upload completed: {data.file_name} ({file_size} bytes) for user {data.username}")
        
        return UploadFileResponse(
            message="File uploaded successfully",
            file_uuid=data.uuid,
            file_name=data.file_name or "unknown",
            size=file_size
        )


@router.post("/files/download")
async def download_file(data=Depends(SignedPayload.unwrap(DownloadFileRequest))):  # noqa: B008
    """
    Download a file by UUID.
    Verifies user has access to the file (owner or shared with them).
    Returns the encrypted file content.
    """
    logger.debug(f"Download request for UUID: {data.uuid} by user: {data.username}")
    
    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {data.username} not found")
        
        # Verify file exists
        file = session.exec(select(File).where(File.uuid == data.uuid)).first()
        if not file:
            raise HTTPException(status_code=404, detail=f"File with UUID {data.uuid} not found")
        
        # Check access permissions
        has_access = False
        
        # Check if user is the owner
        if file.owner_username == data.username:
            has_access = True
            logger.info(f"Access granted: {data.username} is owner of file {data.uuid}")
        else:
            # Check if file has been shared with this user
            file_share = session.exec(
                select(FileShare).where(
                    FileShare.file_uuid == data.uuid,
                    FileShare.recipient_username == data.username,
                    FileShare.revoked == False
                )
            ).first()
            
            if file_share:
                has_access = True
                logger.info(f"Access granted: file {data.uuid} shared with {data.username}")
        
        if not has_access:
            logger.warning(f"Access denied: {data.username} cannot access file {data.uuid}")
            raise HTTPException(
                status_code=403, 
                detail=f"User {data.username} does not have access to file {data.uuid}"
            )
        
        # Check if file exists on disk
        file_path = uploads_dir / f"{data.uuid}"
        if not file_path.exists():
            logger.error(f"File not found on disk: {file_path}")
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        logger.info(f"Serving file {file.file_name} to {data.username}")
        
        # Return file as download
        return FileResponse(
            path=file_path,
            filename=file.file_name,
            media_type='application/octet-stream'
        )


@router.post("/files/share_file")
async def share_file(data=Depends(SignedPayload.unwrap(ShareFileRequest))):
    logger.debug(f"Sharing file from {data.sharer_username} to {data.recipient_username}")
    with Session(engine) as session:
        # Verify sharer exists
        sharer = session.exec(select(User).where(User.username == data.sharer_username)).first()
        if not sharer:
            raise HTTPException(status_code=404, detail=f"Sharer {data.sharer_username} not found")

        # Verify recipient exists
        recipient = session.exec(select(User).where(User.username == data.recipient_username)).first()
        if not recipient:
            raise HTTPException(status_code=404, detail=f"Recipient {data.recipient_username} not found")

        # Verify file exists and sharer owns it
        file = session.exec(select(File).where(File.uuid == data.file_uuid)).first()
        if not file:
            raise HTTPException(status_code=404, detail=f"File with UUID {data.file_uuid} not found")
        
        if file.owner_username != data.sharer_username:
            raise HTTPException(
                status_code=403, 
                detail=f"User {data.sharer_username} does not own file {data.file_uuid}"
            )
        
        logger.info(f"File verification passed: {file.file_name} owned by {data.sharer_username}")
        
        # Check if file is already shared with this recipient
        existing_share = session.exec(
            select(FileShare).where(
                FileShare.file_uuid == data.file_uuid,
                FileShare.recipient_username == data.recipient_username
            )
        ).first()
        
        if existing_share:
            if existing_share.revoked:
                # Re-enable access if previously revoked
                existing_share.revoked = False
                session.add(existing_share)
                logger.info(f"Re-enabled access for {data.recipient_username} to file {data.file_uuid}")
            else:
                logger.info(f"File {data.file_uuid} already shared with {data.recipient_username}")
        else:
            # Create new file share record
            new_file_share = FileShare(
                file_uuid=data.file_uuid,
                owner_username=data.sharer_username,
                recipient_username=data.recipient_username
            )
            session.add(new_file_share)
            logger.info(f"Created new file share record for {data.recipient_username}")
        
        # Store the initial message for the recipient
        new_message = MessageStore(
            f_username=data.recipient_username,
            sharer_identity_key_public=data.sharer_identity_key_public,
            eph_key=data.sharer_ephemeral_key_public,
            otp_hash=data.otp_hash,
            e_dek=data.encrypted_dek,
        )
        session.add(new_message)
        session.commit()
        logger.info(f"Initial message stored for {data.recipient_username} from {data.sharer_username}")

    return {"message": "File shared successfully"}