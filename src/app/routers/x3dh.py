import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, create_engine, select

from app.models.requests import SignedPayload
from app.models.requests.x3dh import (
    GetPrekeyBundleRequest,
    GrabInitialMessagesRequest,
    GrabInitialMessagesResponse,
    InitialMessage,
    PrekeyBundleResponse,
    ShareFileRequest,
    ShareFileResponse,
    OtpPrekeyPush,
    SignedPrekeyPush,
)
from app.models.schema import MessageStore, Otp, PrekeyBundle, User
from app.shared import Logger, load_config

logger = Logger(__name__).get_logger()

router = APIRouter()

config = load_config()
endpoint = config.endpoint
engine = create_engine(config.database.path)

@router.post("/x3dh/signed_prekey_push")
async def signed_prekey_push(data=Depends(SignedPayload.unwrap(SignedPrekeyPush))):
    logger.debug(data)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prekey_bundle = session.exec(select(PrekeyBundle).where(PrekeyBundle.f_username == data.username)).first()
        if prekey_bundle:
            # Update existing prekey bundle
            prekey_bundle.prekey = data.signed_prekey_public
            prekey_bundle.sig_prekey = data.signed_prekey_signature
        else:
            # Create new prekey bundle
            prekey_bundle = PrekeyBundle(
                f_username=data.username,
                prekey=data.signed_prekey_public,
                sig_prekey=data.signed_prekey_signature,
            )
        session.add(prekey_bundle)
        session.commit()
        session.refresh(prekey_bundle)

    return {"message": "Signed prekey push received"}


@router.post("/x3dh/otp_prekey_push")
async def otp_prekey_push(data=Depends(SignedPayload.unwrap(OtpPrekeyPush))):
    logger.debug(data)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found") # double checking in case -

        for otp_key in data.pub_otps:
            new_otp = Otp(f_username=data.username, otp_val=otp_key)
            session.add(new_otp)

        session.commit()


    return {"message": "OTP prekey push received"}

@router.post("/x3dh/prekey_bundle", response_model=PrekeyBundleResponse)
async def get_prekey_bundle(data=Depends(SignedPayload.unwrap(GetPrekeyBundleRequest))):
    logger.debug(f"Fetching prekey bundle for user: {data.target_username}")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == data.target_username)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        prekey_bundle_db = session.exec(
            select(PrekeyBundle).where(PrekeyBundle.f_username == data.target_username)
        ).first()
        if not prekey_bundle_db:
            raise HTTPException(status_code=404, detail="Prekey bundle not found for user")

        # Fetch an unused OTP with row-level locking to prevent race conditions
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
            session.commit()
            session.refresh(otp_record)
            logger.info(f"OTP {otp_record.id} for user {data.target_username} marked as used.")
        else:
            # OTP is mandatory, raise an error if not found
            logger.error(f"Mandatory OTP not available for user: {data.target_username}")
            raise HTTPException(status_code=404, detail=f"Mandatory OTP not available for user: {data.target_username}")

        # Calculate SHA-256 hash of the OTP
        otp_hash = hashlib.sha256(one_time_prekey_val).digest()

        return PrekeyBundleResponse(
            identity_key=user.public_key,
            signed_prekey=prekey_bundle_db.prekey,
            signed_prekey_signature=prekey_bundle_db.sig_prekey,
            one_time_prekey=one_time_prekey_val,
            one_time_prekey_hash=otp_hash
        )

@router.post("/x3dh/share_file", response_model=ShareFileResponse)
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

        return ShareFileResponse(message="File shared successfully")

@router.post("/x3dh/grab_initial_messages", response_model=GrabInitialMessagesResponse)
async def grab_initial_messages(data=Depends(SignedPayload.unwrap(GrabInitialMessagesRequest))):
    logger.debug(f"Grabbing initial messages for user: {data.username}")
    with Session(engine) as session:
        # Verify user exists
        user = session.exec(select(User).where(User.username == data.username)).first()
        if not user:
            raise HTTPException(status_code=404, detail=f"User {data.username} not found")

        # Fetch all messages for the user
        message_records = session.exec(
            select(MessageStore).where(MessageStore.f_username == data.username)
        ).all()

        if not message_records:
            logger.info(f"No initial messages found for user: {data.username}")
            return GrabInitialMessagesResponse(messages=[])

        initial_messages = []
        for record in message_records:
            initial_messages.append(
                InitialMessage(
                    sharer_identity_key_public=record.sharer_identity_key_public,
                    sharer_ephemeral_key_public=record.eph_key,
                    otp_hash=record.otp_hash,
                    encrypted_dek=record.e_dek,
                )
            )
            # Delete the message from the server after fetching
            session.delete(record)

        session.commit()
        logger.info(f"Retrieved and deleted {len(initial_messages)} initial messages for user: {data.username}")

        return GrabInitialMessagesResponse(messages=initial_messages)


