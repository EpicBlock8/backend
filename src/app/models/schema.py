from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(..., unique=True, index=True, description="Unique username")
    public_key: bytes = Field(..., description="User's public key")

    # Relationships
    prekey_bundles: list["PrekeyBundle"] = Relationship(back_populates="user")
    otps: list["Otp"] = Relationship(back_populates="user")
    message_stores: list["MessageStore"] = Relationship(back_populates="user")


class File(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uuid: str = Field(
        ..., unique=True, index=True, description="Unique file identifier"
    )
    file_name: str = Field(..., description="Original name of the file")
    size: int = Field(..., description="Size of the file in bytes")
    date_created: datetime = Field(..., description="Timestamp when file was created")


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
    otp_val: str = Field(..., description="One-time prekey value")
    used: bool = Field(
        default=False, description="Flag indicating if the OTP has been used"
    )

    user: User | None = Relationship(back_populates="otps")


class MessageStore(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    f_username: str = Field(
        ..., foreign_key="user.username", description="Foreign key to User.username"
    )
    eph_key: bytes = Field(..., description="Ephemeral encryption key")
    e_dek: bytes = Field(..., description="Encrypted data encryption key")
    otp_hash: bytes = Field(..., description="Hash of the OTP used for this message")

    user: User | None = Relationship(back_populates="message_stores")