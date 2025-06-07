import os
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import File
from app.shared import load_config

config = load_config()


def attack_file_data(engine: Engine, username: str):
    file_dir = Path(config.paths.files)

    with Session(engine) as session:
        files = session.exec(select(File).where(File.owner_username == username)).all()

        if not files:
            print(f"[!] No files owned by user '{username}'")
            return

        print(f"[•] Found {len(files)} file(s) for user '{username}':\n")
        for i, f in enumerate(files):
            print(f"  [{i}] {f.file_name} (UUID: {f.uuid}, Size: {f.size} bytes)")

        choice = input("\n[?] Enter file number to corrupt: ").strip()
        if not choice.isdigit() or not (0 <= int(choice) < len(files)):
            print("[!] Invalid choice.")
            return

        selected_file = files[int(choice)]
        file_path = file_dir / selected_file.uuid

        if not file_path.exists():
            print(f"[!] File on disk not found: {file_path}")
            return

        print(f"[⚠] Corrupting file: {file_path}")
        corrupt_bytes = os.urandom(min(64, selected_file.size or 64))

        file_path.write_bytes(corrupt_bytes)

        print(
            f"[✔] Corrupted file '{selected_file.file_name}' "
            f"(UUID: {selected_file.uuid})"
        )


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(
            description="Simulate corruption of user-owned file data"
        )
        parser.add_argument("username", type=str, help="Username to target")
        parser.add_argument("--db", type=str, help="SQLite database path override")
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    attack_file_data(engine, args.username)
