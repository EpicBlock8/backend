import base64
from datetime import datetime, UTC
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlmodel import Session, select

from app.models.requests import (
    DownloadFileRequest,
    SignedPayload,
    UploadFileRequest,
    UploadFileResponse,
)
from app.models.requests.files import DeleteFileRequest, RevokeFileRequest, RevokeFileResponse, ShareFileRequest
from app.models.schema import File, FileShare, MessageStore, User
from app.shared import Logger, load_config
from app.shared.db import engine

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint

# Create uploads directory if it doesn't exist
uploads_dir = Path(config.paths.files)
uploads_dir.mkdir(exist_ok=True)
logger.info("Files will be stored in: %s", uploads_dir.absolute())

# Add helper to verify and resolve file paths safely
def get_safe_file_path(file_uuid: str) -> Path:
    """
    Returns a safe resolved file path under uploads_dir, preventing path traversal.
    """
    file_path = uploads_dir / file_uuid
    base_dir = uploads_dir.resolve()
    resolved_path = file_path.resolve()
    try:
        resolved_path.relative_to(base_dir)
    except ValueError:
        logger.error("Invalid file path detected: %s", file_path)
        raise HTTPException(status_code=400, detail="Invalid file path")
    return resolved_path


@router.post("/files/upload", response_model=UploadFileResponse)
async def upload_file(
    data: Annotated[
        UploadFileRequest, Depends(SignedPayload.unwrap(UploadFileRequest))
    ],
):
    """
    Upload a file via JSON payload. The file content is Base64 encoded.

    JSON payload should include:
    - uuid: Unique identifier for the file - check first...
    - username: Username of the file owner
    - file_name: Original filename
    - file_content_b64: Base64 encoded file content
    """
    logger.debug(
        "Uploading file: %s for user: %s, UUID: %s", data.file_name, data.username, data.uuid
    )

    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User {data.username} not found"
            )

        # Check if file UUID already exists
        existing_file = session.exec(select(File).where(File.uuid == data.uuid)).first()
        if existing_file:
            raise HTTPException(
                status_code=409, detail=f"File with UUID {data.uuid} already exists"
            )

        # Decode Base64 file content
        try:
            file_content = base64.b64decode(data.file_content_b64, validate=True)
            file_size = len(file_content)
            logger.info(
                "Decoded %s bytes from Base64 input for file: %s", file_size, data.file_name
            )
        except Exception as e:
            logger.error("Failed to decode Base64 content: %s", e)
            raise HTTPException(status_code=400, detail="Invalid Base64 content") from e

        # Check file size limits
        max_file_size = config.files.max_file_size
        if file_size > max_file_size:
            logger.warning(
                "File %s (%s bytes) exceeds maximum file size (%s bytes)", 
                data.file_name, file_size, max_file_size
            )
            raise HTTPException(
                status_code=413, 
                detail=f"File size {file_size} bytes exceeds maximum allowed size of {max_file_size} bytes"
            )

        # Check total user storage limit
        max_total_storage = config.files.max_total_user_storage
        current_storage = session.exec(
            select(File.size).where(File.owner_username == data.username)
        ).all()
        total_current_storage = sum(size for size in current_storage if size is not None)
        
        if total_current_storage + file_size > max_total_storage:
            logger.warning(
                "User %s storage (%s bytes) + new file (%s bytes) exceeds total storage limit (%s bytes)",
                data.username, total_current_storage, file_size, max_total_storage
            )
            raise HTTPException(
                status_code=413,
                detail=f"Adding this file would exceed your storage limit. Current: {total_current_storage} bytes, Limit: {max_total_storage} bytes"
            )

        logger.info(
            "Size checks passed for %s: file size %s bytes, user total storage %s bytes", 
            data.username, file_size, total_current_storage
        )

        # Create file path using UUID
        file_path = get_safe_file_path(data.uuid)

        # Save file to disk
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info("File saved to: %s", file_path)
        except Exception as e:
            logger.error("Failed to save file to disk: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save file") from e

        # Create database record
        new_file = File(
            uuid=data.uuid,
            file_name=data.file_name or "unknown",
            size=file_size,
            date_created=datetime.now(UTC),
            owner_username=data.username,
        )

        session.add(new_file)
        session.commit()
        session.refresh(new_file)

        logger.info(
            "File upload completed: %s (%s bytes) for user %s", data.file_name, file_size, data.username
        )

    return JSONResponse(content={"message": "File uploaded successfully"})


@router.post("/files/download")
async def download_file(
    data: Annotated[
        DownloadFileRequest, Depends(SignedPayload.unwrap(DownloadFileRequest))
    ],
):
    """
    Download a file by UUID.
    Verifies user has access to the file (owner or shared with them).
    Returns the encrypted file content.
    """
    logger.debug("Download request for UUID: %s by user: %s", data.uuid, data.username)

    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User {data.username} not found"
            )

        # Verify file exists
        file = session.exec(select(File).where(File.uuid == data.uuid)).first()
        if not file:
            raise HTTPException(
                status_code=404, detail=f"File with UUID {data.uuid} not found"
            )

        # Check access permissions
        has_access = False

        # Check if user is the owner
        if file.owner_username == data.username:
            has_access = True
            logger.info("Access granted: %s is owner of file %s", data.username, data.uuid)
        else:
            # Check if file has been shared with this user
            file_share = session.exec(
                select(FileShare).where(
                    FileShare.file_uuid == data.uuid,
                    FileShare.recipient_username == data.username,
                    FileShare.revoked == False,
                )
            ).first()

            if file_share:
                has_access = True
                logger.info(
                    "Access granted: file %s shared with %s", data.uuid, data.username
                )

        if not has_access:
            logger.warning(
                "Access denied: %s cannot access file %s", data.username, data.uuid
            )
            raise HTTPException(
                status_code=403,
                detail=f"User {data.username} does not have access to file {data.uuid}",
            )

        # Check if file exists on disk
        file_path = get_safe_file_path(data.uuid)
        if not file_path.exists():
            logger.error("File not found on disk: %s", file_path)
            raise HTTPException(status_code=404, detail="File not found on disk")

        logger.info("Serving file %s to %s", file.file_name, data.username)

        # Return file as download
        return FileResponse(
            path=file_path,
            filename=file.file_name,
            media_type="application/octet-stream",
        )


@router.post("/files/share_file")
async def share_file(
    data: Annotated[ShareFileRequest, Depends(SignedPayload.unwrap(ShareFileRequest))],
):
    logger.debug(
        "Sharing file from %s to %s", data.sharer_username, data.recipient_username
    )
    with Session(engine) as session:
        # Verify sharer exists
        sharer = session.exec(
            select(User).where(User.username == data.sharer_username)
        ).first()
        if not sharer:
            raise HTTPException(
                status_code=404, detail=f"Sharer {data.sharer_username} not found" 
            )

        # Verify recipient exists
        recipient = session.exec(
            select(User).where(User.username == data.recipient_username)
        ).first()
        if not recipient:
            raise HTTPException(
                status_code=404, detail=f"Recipient {data.recipient_username} not found"
            )

        # Verify file exists and sharer owns it
        file = session.exec(select(File).where(File.uuid == data.file_uuid)).first()
        if not file:
            raise HTTPException(
                status_code=404, detail=f"File with UUID {data.file_uuid} not found"
            )

        if file.owner_username != data.sharer_username:
            raise HTTPException(
                status_code=403,
                detail=f"User {data.sharer_username} does not own file {data.file_uuid}",
            )

        logger.info(
            "File verification passed: %s owned by %s", file.file_name, data.sharer_username
        )

        # Check if file is already shared with this recipient
        existing_share = session.exec(
            select(FileShare).where(
                FileShare.file_uuid == data.file_uuid,
                FileShare.recipient_username == data.recipient_username,
            )
        ).first()

        if existing_share:
            if existing_share.revoked:
                # Re-enable access if previously revoked
                existing_share.revoked = False
                session.add(existing_share)
                session.commit()
                logger.info(
                    "Re-enabled access for %s to file %s", data.recipient_username, data.file_uuid
                )
            else:
                logger.info(
                    "File %s already shared with %s", data.file_uuid, data.recipient_username
                )
        else:
            # Create new file share record
            new_file_share = FileShare(
                file_uuid=data.file_uuid,
                owner_username=data.sharer_username,
                recipient_username=data.recipient_username,
            )
            session.add(new_file_share)
            session.commit()
            logger.info("Created new file share record for %s", data.recipient_username)

    return JSONResponse(content={"message": "File shared successfully"})


@router.post("/files/revoke_file")
async def revoke_file(
    data: Annotated[RevokeFileRequest, Depends(SignedPayload.unwrap(RevokeFileRequest))],
):
    logger.debug(
        "Revocation request for file %s from %s to %s", data.file_uuid, data.sharer_username, data.revoked_username
    )
    
    with Session(engine) as session:
        # Verify sharer exists
        sharer = session.exec(
            select(User).where(User.username == data.sharer_username)
        ).first()
        if not sharer:
            raise HTTPException(
                status_code=404, detail=f"Sharer {data.sharer_username} not found" 
            )

        # Verify revoked user exists
        revoked = session.exec(
            select(User).where(User.username == data.revoked_username)
        ).first()
        if not revoked:
            raise HTTPException(
                status_code=404, detail=f"Revoked {data.revoked_username} not found"
            )

        # Verify file exists and sharer owns it
        file = session.exec(select(File).where(File.uuid == data.file_uuid)).first()
        if not file:
            raise HTTPException(
                status_code=404, detail=f"File with UUID {data.file_uuid} not found"
            )

        if file.owner_username != data.sharer_username:
            raise HTTPException(
                status_code=403,
                detail=f"User {data.sharer_username} does not own file {data.file_uuid}",
            )

        logger.info(
            "File verification passed: %s owned by %s", file.file_name, data.sharer_username
        )

        # Check to make sure the user being revoked currently has access to this file
        existing_share = session.exec(
            select(FileShare).where(
                FileShare.file_uuid == data.file_uuid,
                FileShare.recipient_username == data.revoked_username,
            )
        ).first()

        if existing_share and not existing_share.revoked:
            existing_share.revoked = True
            session.add(existing_share)
            session.commit()
            
            logger.info(
                "Revoked access for %s to file %s", data.revoked_username, data.file_uuid
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"User {data.revoked_username} does not have access to this file"
            )
            
        # Update the encrypted contents of the now-revoked file
        try:
            file_content = base64.b64decode(data.file_content_b64, validate=True)
            file_size = len(file_content)
            logger.info(
                "Decoded %s bytes from Base64 input for file: %s", file_size, file.uuid
            )
        except Exception as e:
            logger.error("Failed to decode Base64 content: %s", e)
            raise HTTPException(status_code=400, detail="Invalid Base64 content") from e

        file_path = get_safe_file_path(data.file_uuid)

        # Save file to disk
        try:
            with open(file_path, "wb") as f:
                f.write(file_content)
            logger.info("File saved to: %s", file_path)
        except Exception as e:
            logger.error("Failed to save file to disk: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save file") from e
        
    
    return RevokeFileResponse(message="File revoked successfully")

@router.post("/files/delete")
async def delete_file(
    data: Annotated[
        DeleteFileRequest, Depends(SignedPayload.unwrap(DeleteFileRequest))
    ],
):
    """
    send: file UUID signed
    ======================
    Delete file blob
    Delete every record we have of it being shared
    ======================
    receive: confirmation
    """
    logger.debug("Delete request for UUID: %s by user: %s", data.uuid, data.username)

    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User {data.username} not found"
            )

        # Verify file exists
        file = session.exec(select(File).where(File.uuid == data.uuid)).first()
        if not file:
            raise HTTPException(
                status_code=404, detail=f"File with UUID {data.uuid} not found"
            )

        # Check access permissions
        has_access = False

        # Check if user is the owner
        if file.owner_username == data.username:
            has_access = True
            logger.info("Access granted: %s is owner of file %s", data.username, data.uuid)

        if not has_access:
            logger.warning(
                "Access denied: %s cannot delete file %s", data.username, data.uuid
            )
            raise HTTPException(
                status_code=403,
                detail=f"User {data.username} does not have access to delete file {data.uuid}",
            )

        # Check if file exists on disk
        file_path = get_safe_file_path(data.uuid)
        if not file_path.exists():
            logger.error("File not found on disk: %s", file_path)
            raise HTTPException(status_code=404, detail="File not found on disk")

        try:
            file_path.unlink()
        except Exception as e:
            logger.error("Failed to delete file: %s", e)
            raise HTTPException(status_code=500, detail="Failed to delete file") from e
        
        # Return file as download
        return JSONResponse({ "message": "File deleted successfully" })
