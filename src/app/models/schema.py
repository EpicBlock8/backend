from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

# TODO - we need to do some stuff to do authentication
# dont let people download
# do revocation from a crypto + database perspective (maybe optional)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(..., unique=True, index=True, description="Unique username")
    public_key: bytes = Field(..., description="User's public key")

    # Relationships
    prekey_bundles: list["PrekeyBundle"] = Relationship(back_populates="user")
    otps: list["Otp"] = Relationship(back_populates="user")
    pq_signed_prekey_bundles: list["PQSignedPrekeyBundle"] = Relationship(back_populates="user")
    pq_otps: list["PQOneTimePrekey"] = Relationship(back_populates="user")
    owned_files: list["File"] = Relationship(back_populates="owner")
    shared_files: list["FileShare"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "FileShare.owner_username"},
    )
    received_files: list["FileShare"] = Relationship(
        back_populates="recipient",
        sa_relationship_kwargs={"foreign_keys": "FileShare.recipient_username"},
    )
    received_messages: list["MessageStore"] = Relationship(
        back_populates="recipient",
        sa_relationship_kwargs={"foreign_keys": "MessageStore.recipient_username"},
    )
    sent_messages: list["MessageStore"] = Relationship(
        back_populates="sharer",
        sa_relationship_kwargs={"foreign_keys": "MessageStore.sharer_username"},
    )


class File(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uuid: str = Field(
        ..., unique=True, index=True, description="Unique file identifier"
    )
    file_name: str = Field(..., description="Original name of the file")
    size: int = Field(..., description="Size of the file in bytes")
    date_created: datetime = Field(..., description="Timestamp when file was created")
    owner_username: str = Field(
        ..., foreign_key="user.username", description="Username of the file owner"
    )

    # Relationships
    owner: User | None = Relationship(back_populates="owned_files")
    shares: list["FileShare"] = Relationship(back_populates="file")


class FileShare(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    file_uuid: str = Field(
        ..., foreign_key="file.uuid", description="UUID of the shared file"
    )
    owner_username: str = Field(
        ..., foreign_key="user.username", description="Username of the file owner"
    )
    recipient_username: str = Field(
        ..., foreign_key="user.username", description="Username of the recipient"
    )
    shared_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when file was shared"
    )
    revoked: bool = Field(
        default=False, description="Flag indicating if access has been revoked"
    )

    # Relationships
    file: File | None = Relationship(back_populates="shares")
    owner: User | None = Relationship(
        back_populates="shared_files",
        sa_relationship_kwargs={"foreign_keys": "FileShare.owner_username"},
    )
    recipient: User | None = Relationship(
        back_populates="received_files",
        sa_relationship_kwargs={"foreign_keys": "FileShare.recipient_username"},
    )


class PrekeyBundle(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    f_username: str = Field(
        ..., foreign_key="user.username", description="Foreign key to User.username"
    )
    prekey: bytes = Field(..., description="Medium term pre-key")
    sig_prekey: bytes = Field(..., description="Signature of the medium term pre-key")

    user: User | None = Relationship(back_populates="prekey_bundles")


class Otp(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    f_username: str = Field(
        ..., foreign_key="user.username", description="Foreign key to User.username"
    )
    otp_val: bytes = Field(..., description="One-time prekey value")
    used: bool = Field(
        default=False, description="Flag indicating if the OTP has been used"
    )

    user: User | None = Relationship(back_populates="otps")


class PQSignedPrekeyBundle(SQLModel, table=True):
    """Post-quantum signed prekey bundle for PQXDH last-resort KEM prekey"""
    id: int | None = Field(default=None, primary_key=True)
    f_username: str = Field(
        ..., foreign_key="user.username", description="Foreign key to User.username"
    )
    pqspkb: bytes = Field(..., description="PQ last-resort KEM public key")
    pqspkb_sig: bytes = Field(..., description="Signature over the KEM public key")

    user: User | None = Relationship(back_populates="pq_signed_prekey_bundles")


class PQOneTimePrekey(SQLModel, table=True):
    """Post-quantum one-time prekey for PQXDH"""
    id: int | None = Field(default=None, primary_key=True)
    f_username: str = Field(
        ..., foreign_key="user.username", description="Foreign key to User.username"
    )
    pqotp: bytes = Field(..., description="PQ one-time KEM public key")
    pqotp_sig: bytes = Field(..., description="Signature over the one-time KEM public key")
    used: bool = Field(
        default=False, description="Flag indicating if the PQ OTP has been used"
    )

    user: User | None = Relationship(back_populates="pq_otps")


class MessageStore(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    recipient_username: str = Field(..., foreign_key="user.username")
    sharer_username: str = Field(..., foreign_key="user.username")
    sharer_identity_key_public: bytes = Field(
        ..., description="Sharer's public identity key"
    )
    eph_key: bytes = Field(..., description="Sharer's public ephemeral key")
    e_message: bytes = Field(..., description="Encrypted message")
    otp_hash: bytes = Field(
        ..., description="Hash of the recipient's OTP used for this message"
    )
    # Post-quantum fields for PQXDH
    pq_ct: bytes = Field(..., description="PQ KEM ciphertext for this initial message")
    pq_otp_hash: bytes = Field(..., description="Hash of the recipient's PQ OTP used for this message")

    # disambiguated relationships:
    recipient: User | None = Relationship(
        back_populates="received_messages",
        sa_relationship_kwargs={"foreign_keys": "MessageStore.recipient_username"},
    )
    sharer: User | None = Relationship(
        back_populates="sent_messages",
        sa_relationship_kwargs={"foreign_keys": "MessageStore.sharer_username"},
    )
