# simulate_user_key_attack.py
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import User
from app.shared import load_config

config = load_config()


def attack_user_public_key(engine: Engine, username: str):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).one_or_none()
        if not user:
            print(f"[!] No such user: {username}")
            return

        user.public_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw()
        session.add(user)
        session.commit()
        print(f"[✔] Tampered public key for user '{username}'")


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(
            description="Simulate Ed25519 public key tampering for a user"
        )
        parser.add_argument("username", type=str, help="Username to modify")
        parser.add_argument(
            "--db",
            type=str,
            help="Path to SQLite database (default: test_users.db)",
        )
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    attack_user_public_key(engine, args.user)
