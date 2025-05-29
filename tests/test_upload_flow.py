#!/usr/bin/env python3
"""
Pytest-compliant test script for file upload and download functionality using FastAPI.
"""

import base64
import json
import uuid as uuid_lib
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Configuration
TEST_USERNAME = "testuser"
TEST_FILE_PATH = Path("test_file.txt")


@pytest.fixture(scope="session")
def private_key():
    return Ed25519PrivateKey.from_private_bytes(b"test_key_32_bytes_for_demo_only!")


@pytest.fixture(scope="session")
def file_uuid():
    return str(uuid_lib.uuid4())


def test_registered_user(private_key):
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes_raw()
    public_key_b64 = base64.b64encode(public_key_bytes).decode()

    register_payload = {
        "username": TEST_USERNAME,
        "public_key": public_key_b64,
    }

    signed_payload = sign_payload(register_payload, private_key)
    response = client.post("/auth/register", json=signed_payload)

    assert response.status_code in [200, 403], (
        f"Unexpected status: {response.status_code}"
    )


@pytest.fixture(scope="session", autouse=True)
def test_file():
    """Create a test file before tests and delete it after."""
    content = "Hello, World! This is a test file for upload functionality.\n" * 10
    TEST_FILE_PATH.write_text(content)
    yield TEST_FILE_PATH
    if TEST_FILE_PATH.exists():
        TEST_FILE_PATH.unlink()
    download_path = Path(f"downloaded_{TEST_FILE_PATH.name}")
    if download_path.exists():
        download_path.unlink()


def sign_payload(payload_dict, private_key):
    """Sign a payload for authentication."""
    payload_json = json.dumps(payload_dict, separators=(",", ":"))
    payload_bytes = payload_json.encode()
    signature_bytes = private_key.sign(payload_bytes)
    signature_b64 = base64.b64encode(signature_bytes).decode()

    return {
        "payload": payload_json,
        "signature": signature_b64,
        "username": TEST_USERNAME,
    }


def test_file_upload(private_key, file_uuid, test_file):
    """Test file upload using Base64-encoded file content."""
    file_bytes = test_file.read_bytes()
    file_content_b64 = base64.b64encode(file_bytes).decode("utf-8")

    upload_payload = {
        "uuid": file_uuid,
        "username": TEST_USERNAME,
        "file_name": test_file.name,
        "file_content_b64": file_content_b64,
    }

    signed_payload = sign_payload(upload_payload, private_key)
    response = client.post("/files/upload", json=signed_payload)

    assert response.status_code == 200
    assert response.json().get("message", "").lower().startswith("file uploaded")


def test_file_download(private_key, file_uuid, test_file):
    """Test downloading the file and verifying content."""
    download_payload = {"uuid": file_uuid, "username": TEST_USERNAME}
    signed_payload = sign_payload(download_payload, private_key)

    response = client.post("/files/download", json=signed_payload)

    assert response.status_code == 200

    download_path = Path(f"downloaded_{test_file.name}")
    download_path.write_bytes(response.content)

    assert test_file.read_bytes() == download_path.read_bytes()


def test_file_download_rate_limit(private_key, file_uuid):
    """Test rate limiting by sending multiple download requests quickly."""
    payload = {"uuid": file_uuid, "username": TEST_USERNAME}
    signed_payload = sign_payload(payload, private_key)

    responses = [client.post("/files/download", json=signed_payload) for _ in range(20)]

    rate_limited = any(resp.status_code == 429 for resp in responses)
    assert rate_limited, "Expected at least one rate-limited (429) response"
