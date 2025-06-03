#!/usr/bin/env python3
"""
Test path traversal prevention in file endpoints and helper.
"""

import base64
import json
import uuid as uuid_lib
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
import app.routers.files as files_module

client = TestClient(app)

# Use a fixed private key for signing
private_bytes = b"0" * 32
private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
public_key = private_key.public_key()
public_key_bytes = public_key.public_bytes_raw()
public_key_b64 = base64.b64encode(public_key_bytes).decode()

TEST_USERNAME = "path_test_user"

def sign_payload(payload_dict, private_key, username):
    payload_json = json.dumps(payload_dict, separators=(",", ":"))
    payload_bytes = payload_json.encode()
    signature_bytes = private_key.sign(payload_bytes)
    signature_b64 = base64.b64encode(signature_bytes).decode()
    return {
        "payload": payload_json,
        "signature": signature_b64,
        "username": username,
    }

@pytest.fixture(scope="session", autouse=True)
def register_user():
    # Register test user
    register_payload = {"username": TEST_USERNAME, "public_key": public_key_b64}
    signed = sign_payload(register_payload, private_key, TEST_USERNAME)
    response = client.post("/auth/register", json=signed)
    assert response.status_code in [200, 403]
    return None


def test_get_safe_file_path_valid(tmp_path, monkeypatch):
    # Setup a dummy uploads_dir
    monkeypatch.setattr(files_module, "uploads_dir", tmp_path)
    file_uuid = "valid_file_123"
    path = files_module.get_safe_file_path(file_uuid)
    assert path == tmp_path / file_uuid


def test_get_safe_file_path_blocks_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(files_module, "uploads_dir", tmp_path)
    with pytest.raises(HTTPException) as excinfo:
        files_module.get_safe_file_path("../evil.txt")
    assert excinfo.value.status_code == 400
    assert "Invalid file path" in str(excinfo.value.detail)


def test_upload_endpoint_blocks_traversal():
    # Attempt to upload with a malicious UUID
    evil_uuid = "../evil.txt"
    file_content_b64 = base64.b64encode(b"A").decode()
    upload_payload = {
        "uuid": evil_uuid,
        "username": TEST_USERNAME,
        "file_name": "evil.txt",
        "file_content_b64": file_content_b64,
    }
    signed = sign_payload(upload_payload, private_key, TEST_USERNAME)
    response = client.post("/files/upload", json=signed)
    assert response.status_code == 400
    assert "Invalid file path" in response.json().get("detail", "") 