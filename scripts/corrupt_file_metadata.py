from sqlalchemy import Engine
from sqlmodel import Session, create_engine, select

from app.models.schema import File
from app.shared import load_config

config = load_config()


def attack_file_metadata(engine: Engine, username: str):
    with Session(engine) as session:
        files = session.exec(select(File).where(File.owner_username == username)).all()

        if not files:
            print(f"[!] No files owned by user '{username}'")
            return

        print(f"[•] Found {len(files)} file(s) for user '{username}':\n")
        for i, f in enumerate(files):
            print(f"  [{i}] {f.file_name} (UUID: {f.uuid}, Size: {f.size} bytes)")

        choice = input("\n[?] Enter file number to tamper with metadata: ").strip()
        if not choice.isdigit() or not (0 <= int(choice) < len(files)):
            print("[!] Invalid choice.")
            return

        selected_file = files[int(choice)]

        # Tamper metadata
        selected_file.file_name = "TAMPERED_FILE.docx"
        selected_file.size = 999999

        session.add(selected_file)
        session.commit()

        print(f"[✔] Tampered metadata of file '{selected_file.uuid}'")


if __name__ == "__main__":
    import argparse

    from app.shared.db import engine

    def parse_args():
        parser = argparse.ArgumentParser(
            description="Simulate tampering with file metadata"
        )
        parser.add_argument("username", type=str, help="Username who owns the file(s)")
        parser.add_argument("--db", type=str, help="SQLite database path override")
        return parser.parse_args()

    args = parse_args()
    if args.db:
        engine = create_engine(args.db)

    attack_file_metadata(engine, args.username)
