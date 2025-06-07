#!/usr/bin/env python3

import argparse
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlmodel import Session, create_engine, select

from app.models.schema import User
from app.shared import Config, load_config

config: Config = load_config()
DATABASE_URL = config.database.path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulate Ed25519 public key tampering for a user"
    )
    parser.add_argument("username", type=str, help="Username to modify")
    parser.add_argument(
        "--db",
        type=str,
        default=DATABASE_URL,
        help="Path to SQLite database (default: test_users.db)",
    )
    return parser.parse_args()


def simulate_attack(username: str, db_url: str):
    engine = create_engine(db_url)

    with Session(engine) as session:
        statement = select(User).where(User.username == username)
        user = session.exec(statement).one_or_none()

        if not user:
            print(f"[!] User '{username}' not found in the database.")
            sys.exit(1)

        # Generate new malicious keypair
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # Serialize public key
        user.public_key = public_key.public_bytes_raw()
        session.add(user)
        session.commit()

        print(
            f"[✔] Tampered public key for user '{username}' "
            "with a malicious Ed25519 key."
        )


if __name__ == "__main__":
    args = parse_args()
    simulate_attack(args.username, args.db)
