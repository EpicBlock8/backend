from base64 import b64decode, b64encode
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.models.requests import SignedPayload
from app.models.requests.x3dh import (
    GetPrekeyBundleRequest,
    GrabReturnMessages,
    PostReturnMessage,
    PostReturnMessageResponse,
    ReturnMessage,
    OtpPrekeyPush,
    PrekeyBundleResponse,
    SignedPrekeyPush,
    GrabReturnMessagesRequest,
    PQSignedPrekeyPush,
    PQOtpPrekeyPush,
)
from app.models.schema import (
    MessageStore, 
    Otp, 
    PrekeyBundle, 
    User, 
    PQSignedPrekeyBundle,
    PQOneTimePrekey
)
from app.shared import Logger, load_config
from app.shared.db import engine

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint

def validate_base64_and_decode(data: str, field_name: str, expected_min_length: int = 1) -> bytes:
    """
    Validate and decode base64 data with proper error handling and logging.
    """
    try:
        decoded = b64decode(data, validate=True)
        if len(decoded) < expected_min_length:
            logger.error("Decoded %s is too short: %d bytes", field_name, len(decoded))
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid {field_name}: decoded data too short"
            )
        logger.debug("Successfully decoded %s: %d bytes", field_name, len(decoded))
        return decoded
    except Exception as e:
        logger.error("Failed to decode base64 %s: %s", field_name, e)
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid base64 encoding for {field_name}"
        ) from e


@router.post("/x3dh/signed_prekey_push")
async def signed_prekey_push(
    data: Annotated[SignedPrekeyPush, Depends(SignedPayload.unwrap(SignedPrekeyPush))],
):
    logger.info("Processing signed prekey push for user: %s", data.username)
    
    # Validate base64 inputs
    prekey_bytes = validate_base64_and_decode(data.signed_prekey_public, "signed_prekey_public", 32)
    sig_bytes = validate_base64_and_decode(data.signed_prekey_signature, "signed_prekey_signature", 16)
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            logger.error("User not found for signed prekey push: %s", data.username)
            raise HTTPException(status_code=404, detail="User not found")

        prekey_bundle = session.exec(
            select(PrekeyBundle).where(PrekeyBundle.f_username == data.username)
        ).first()
        
        if prekey_bundle:
            logger.info("Updating existing prekey bundle for user: %s", data.username)
            prekey_bundle.prekey = prekey_bytes
            prekey_bundle.sig_prekey = sig_bytes
        else:
            logger.info("Creating new prekey bundle for user: %s", data.username)
            prekey_bundle = PrekeyBundle(
                f_username=data.username,
                prekey=prekey_bytes,
                sig_prekey=sig_bytes,
            )
        
        session.add(prekey_bundle)
        session.commit()
        session.refresh(prekey_bundle)
        
        logger.info("Successfully processed signed prekey push for user: %s", data.username)

    return JSONResponse(content={"message": "Signed prekey push received"})


@router.post("/x3dh/pq_signed_prekey_push")
async def pq_signed_prekey_push(
    data: Annotated[PQSignedPrekeyPush, Depends(SignedPayload.unwrap(PQSignedPrekeyPush))],
):
    logger.info("Processing PQ signed prekey push for user: %s", data.username)
    
    # Validate inputs
    pqspkb_bytes = validate_base64_and_decode(data.pq_signed_prekey_public, "pq_signed_prekey_public", 32)
    pqspkb_sig_bytes = validate_base64_and_decode(data.pq_signed_prekey_signature, "pq_signed_prekey_signature", 16)
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            logger.error("User not found for PQ signed prekey push: %s", data.username)
            raise HTTPException(status_code=404, detail="User not found")

        pq_prekey_bundle = session.exec(
            select(PQSignedPrekeyBundle).where(PQSignedPrekeyBundle.f_username == data.username)
        ).first()
        
        if pq_prekey_bundle:
            logger.info("Updating existing PQ signed prekey bundle for user: %s", data.username)
            pq_prekey_bundle.pqspkb = pqspkb_bytes
            pq_prekey_bundle.pqspkb_sig = pqspkb_sig_bytes
        else:
            logger.info("Creating new PQ signed prekey bundle for user: %s", data.username)
            pq_prekey_bundle = PQSignedPrekeyBundle(
                f_username=data.username,
                pqspkb=pqspkb_bytes,
                pqspkb_sig=pqspkb_sig_bytes,
            )
        
        session.add(pq_prekey_bundle)
        session.commit()
        session.refresh(pq_prekey_bundle)
        
        logger.info("Successfully processed PQ signed prekey push for user: %s", data.username)

    return JSONResponse(content={"message": "PQ signed prekey push received"})


@router.post("/x3dh/otp_prekey_push")
async def otp_prekey_push(
    data: Annotated[OtpPrekeyPush, Depends(SignedPayload.unwrap(OtpPrekeyPush))],
):
    logger.info("Processing OTP prekey push for user: %s with %d keys", data.username, len(data.pub_otps))
    
    if not data.pub_otps:
        logger.error("Empty OTP prekey list provided for user: %s", data.username)
        raise HTTPException(status_code=400, detail="At least one OTP prekey must be provided")
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            logger.error("User not found for OTP prekey push: %s", data.username)
            raise HTTPException(status_code=404, detail="User not found")

        valid_otps = []
        for i, otp_key in enumerate(data.pub_otps):
            try:
                otp_bytes = validate_base64_and_decode(otp_key, f"otp_key[{i}]", 32)
                valid_otps.append(otp_bytes)
            except HTTPException:
                logger.error("Skipping invalid OTP key at index %d for user %s", i, data.username)
                continue
        
        if not valid_otps:
            logger.error("No valid OTP keys found for user: %s", data.username)
            raise HTTPException(status_code=400, detail="No valid OTP keys provided")

        for otp_bytes in valid_otps:
            new_otp = Otp(f_username=data.username, otp_val=otp_bytes)
            session.add(new_otp)

        session.commit()
        logger.info("Successfully added %d OTP prekeys for user: %s", len(valid_otps), data.username)

    return JSONResponse(content={"message": "OTP prekey push received"})


@router.post("/x3dh/pq_otp_prekey_push")
async def pq_otp_prekey_push(
    data: Annotated[PQOtpPrekeyPush, Depends(SignedPayload.unwrap(PQOtpPrekeyPush))],
):
    logger.info("Processing PQ OTP prekey push for user: %s with %d keys", data.username, len(data.pub_pq_otps))
    
    if not data.pub_pq_otps:
        logger.error("Empty PQ OTP prekey list provided for user: %s", data.username)
        raise HTTPException(status_code=400, detail="At least one PQ OTP prekey must be provided")
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            logger.error("User not found for PQ OTP prekey push: %s", data.username)
            raise HTTPException(status_code=404, detail="User not found")

        valid_pq_otps = []
        for i, otp_data_item in enumerate(data.pub_pq_otps):
            try:
                otp_bytes = validate_base64_and_decode(otp_data_item.public_key, f"pq_otp_key[{i}].public_key", 32)
                sig_bytes = validate_base64_and_decode(otp_data_item.signature, f"pq_otp_key[{i}].signature", 16)
                
                valid_pq_otps.append((otp_bytes, sig_bytes))
            except (HTTPException, AttributeError) as e:
                logger.error("Skipping invalid PQ OTP key at index %d for user %s: %s", i, data.username, e)
                continue
        
        if not valid_pq_otps:
            logger.error("No valid PQ OTP keys found for user: %s", data.username)
            raise HTTPException(status_code=400, detail="No valid PQ OTP keys provided")

        for otp_bytes, sig_bytes in valid_pq_otps:
            new_pq_otp = PQOneTimePrekey(
                f_username=data.username,
                pqotp=otp_bytes,
                pqotp_sig=sig_bytes
            )
            session.add(new_pq_otp)

        session.commit()
        logger.info("Successfully added %d PQ OTP prekeys for user: %s", len(valid_pq_otps), data.username)

    return JSONResponse(content={"message": "PQ OTP prekey push received"})


@router.post("/x3dh/prekey_bundle", response_model=PrekeyBundleResponse)
async def get_prekey_bundle(
    data: Annotated[
        GetPrekeyBundleRequest, Depends(SignedPayload.unwrap(GetPrekeyBundleRequest))
    ],
):
    logger.info("Fetching prekey bundle for user: %s (requested by: %s)", data.target_username, data.username)
    
    with Session(engine) as session:
        # Verify target user exists
        user = session.exec(
            select(User).where(User.username == data.target_username)
        ).first()
        if not user:
            logger.error("Target user not found: %s", data.target_username)
            raise HTTPException(status_code=404, detail="Target user not found")

        # Fetch classical prekey bundle
        prekey_bundle_db = session.exec(
            select(PrekeyBundle).where(PrekeyBundle.f_username == data.target_username)
        ).first()
        if not prekey_bundle_db:
            logger.error("Classical prekey bundle not found for user: %s", data.target_username)
            raise HTTPException(
                status_code=404, detail="Prekey bundle not found for user"
            )

        # Fetch PQ signed prekey bundle
        pq_prekey_bundle_db = session.exec(
            select(PQSignedPrekeyBundle).where(PQSignedPrekeyBundle.f_username == data.target_username)
        ).first()
        if not pq_prekey_bundle_db:
            logger.error("PQ signed prekey bundle not found for user: %s", data.target_username)
            raise HTTPException(
                status_code=404, detail="PQ prekey bundle not found for user"
            )

        # Fetch an unused classical OTP with row-level locking
        otp_record = session.exec(
            select(Otp)
            .where(Otp.f_username == data.target_username, Otp.used == False)
            .with_for_update()
        ).first()

        one_time_prekey_val = None
        if otp_record:
            one_time_prekey_val = otp_record.otp_val
            otp_record.used = True
            session.add(otp_record)
            logger.info("Classical OTP %s for user %s marked as used", otp_record.id, data.target_username)
        else:
            logger.error("Mandatory classical OTP not available for user: %s", data.target_username)
            raise HTTPException(
                status_code=404,
                detail=f"Mandatory OTP not available for user: {data.target_username}",
            )

        # Fetch an unused PQ OTP with row-level locking (prefer one-time over last-resort)
        pq_otp_record = session.exec(
            select(PQOneTimePrekey)
            .where(PQOneTimePrekey.f_username == data.target_username, PQOneTimePrekey.used == False)
            .with_for_update()
        ).first()

        pq_one_time_key = None
        pq_one_time_sig = None
        
        if pq_otp_record:
            # Use one-time PQ prekey
            pq_one_time_key = pq_otp_record.pqotp
            pq_one_time_sig = pq_otp_record.pqotp_sig
            pq_otp_record.used = True
            session.add(pq_otp_record)
            logger.info("PQ OTP %s for user %s marked as used", pq_otp_record.id, data.target_username)
        else:
            # PQ OTP is mandatory, raise an error if not found
            logger.error("Mandatory PQ OTP not available for user: %s", data.target_username)
            raise HTTPException(
                status_code=404,
                detail=f"Mandatory PQ OTP not available for user: {data.target_username}",
            )

        session.commit()

        response = PrekeyBundleResponse(
            # Classical X3DH fields
            identity_key=b64encode(user.public_key).decode("utf8"),
            signed_prekey=b64encode(prekey_bundle_db.prekey).decode("utf8"),
            signed_prekey_signature=b64encode(prekey_bundle_db.sig_prekey).decode("utf8"),
            one_time_prekey=b64encode(one_time_prekey_val).decode("utf8"),
            
            # Post-quantum PQXDH fields
            pq_signed_prekey=b64encode(pq_prekey_bundle_db.pqspkb).decode("utf8"),
            pq_signed_prekey_signature=b64encode(pq_prekey_bundle_db.pqspkb_sig).decode("utf8"),
            
            # One-time PQ prekey fields (always present since it's mandatory)
            one_time_pq_prekey=b64encode(pq_one_time_key).decode("utf8"),
            one_time_pq_prekey_signature=b64encode(pq_one_time_sig).decode("utf8"),
        )
        
        logger.info("Successfully provided prekey bundle for user: %s to requester: %s", data.target_username, data.username)
        return response


@router.post("/x3dh/post_return_message", response_model=PostReturnMessageResponse)
async def post_return_messages(
    data: Annotated[
        PostReturnMessage, Depends(SignedPayload.unwrap(PostReturnMessage))
    ],
):
    logger.info("Posting return message from %s to %s", data.sharer_username, data.recipient_username)
    
    # Validate all base64 inputs
    sharer_identity_bytes = validate_base64_and_decode(data.sharer_identity_key_public, "sharer_identity_key_public", 32)
    sharer_eph_bytes = validate_base64_and_decode(data.sharer_ephemeral_key_public, "sharer_ephemeral_key_public", 32)
    otp_hash_bytes = validate_base64_and_decode(data.otp_hash, "otp_hash", 16)
    encrypted_msg_bytes = validate_base64_and_decode(data.encrypted_message, "encrypted_message", 1)
    kem_ct_bytes = validate_base64_and_decode(data.kem_ciphertext, "kem_ciphertext", 32)
    pq_otp_hash_bytes = validate_base64_and_decode(data.pq_otp_hash, "pq_otp_hash", 16)
    
    with Session(engine) as session:
        # Verify sharer exists
        sharer = session.exec(
            select(User).where(User.username == data.sharer_username)
        ).first()
        
        if not sharer:
            logger.error("Sharer not found: %s", data.sharer_username)
            raise HTTPException(
                status_code=404, detail=f"Sharer {data.sharer_username} not found" 
            )

        # Verify recipient exists
        recipient = session.exec(
            select(User).where(User.username == data.recipient_username)
        ).first()
        
        if not recipient:
            logger.error("Recipient not found: %s", data.recipient_username)
            raise HTTPException(
                status_code=404, detail=f"Recipient {data.recipient_username} not found"
            )
        
        # Store the initial message for the recipient        
        new_message = MessageStore(
            recipient_username=data.recipient_username,
            sharer_identity_key_public=sharer_identity_bytes,
            eph_key=sharer_eph_bytes,
            sharer_username=data.sharer_username,
            otp_hash=otp_hash_bytes,
            e_message=encrypted_msg_bytes,
            # PQ fields
            pq_ct=kem_ct_bytes,
            pq_otp_hash=pq_otp_hash_bytes,
        )

        session.add(new_message)
        session.commit()
        session.refresh(new_message)

        logger.info(
            "Initial message (ID: %s) stored for %s from %s with PQ OTP hash", 
            new_message.id, data.recipient_username, data.sharer_username
        )
        
        return PostReturnMessageResponse(message="Message posted successfully")


@router.post(
    "/x3dh/grab_return_messages", response_model=GrabReturnMessages
)
async def grab_return_messages(
    data: Annotated[
        GrabReturnMessagesRequest,
        Depends(SignedPayload.unwrap(GrabReturnMessagesRequest)),
    ],
):
    logger.info("Grabbing initial messages for user: %s", data.username)
    
    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            logger.error("User not found for grab messages: %s", data.username)
            raise HTTPException(
                status_code=404, detail=f"User {data.username} not found"
            )

        # Fetch all messages for the user
        message_records = session.exec(
            select(MessageStore).where(MessageStore.recipient_username == data.username)
        ).all()

        if not message_records:
            logger.info("No initial messages found for user: %s", data.username)
            return GrabReturnMessages(messages=[])

        return_messages = []
        for record in message_records:
            return_messages.append(
                ReturnMessage(
                    # Classical X3DH fields
                    sharer_identity_key_public=b64encode(record.sharer_identity_key_public).decode("utf8"),
                    sharer_ephemeral_key_public=b64encode(record.eph_key).decode("utf8"),
                    sharer_username=record.sharer_username,
                    otp_hash=b64encode(record.otp_hash).decode("utf8"),
                    encrypted_message=b64encode(record.e_message).decode("utf8"),
                    # Post-quantum PQXDH fields
                    kem_ciphertext=b64encode(record.pq_ct).decode("utf8"),
                    pq_otp_hash=b64encode(record.pq_otp_hash).decode("utf8"),
                )
            )
            # Delete the message from the server after fetching
            session.delete(record)

        session.commit()
        logger.info(
            "Retrieved and deleted %s initial messages for user: %s", len(return_messages), data.username
        )

        return GrabReturnMessages(messages=return_messages)
