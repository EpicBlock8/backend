#!/usr/bin/env python3
"""
Test script for file upload and download functionality.
This demonstrates how to use multipart/form-data with the file endpoints.
"""

import base64
import json
import uuid as uuid_lib
from pathlib import Path

import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_USERNAME = "testuser"
TEST_FILE_PATH = "test_file.txt"


def create_test_file():
    """Create a test file for uploading."""
    content = "Hello, World! This is a test file for upload functionality.\n" * 10
    with open(TEST_FILE_PATH, "w") as f:
        f.write(content)
    print(f"Created test file: {TEST_FILE_PATH}")


def sign_payload(payload_dict, private_key):
    """Sign a payload for authentication."""
    payload_json = json.dumps(payload_dict, separators=(",", ":"))
    payload_bytes = payload_json.encode()
    signature_bytes = private_key.sign(payload_bytes)
    signature_b64 = base64.b64encode(signature_bytes).decode()

    return {"payload": payload_json, "signature": signature_b64}


def test_file_upload(private_key):
    """Test file upload using JSON payload with Base64 encoded content."""
    print("\n=== Testing File Upload ===")

    # Generate a unique UUID for the file
    file_uuid = str(uuid_lib.uuid4())
    print(f"Generated UUID: {file_uuid}")

    # Read and Base64 encode file content
    try:
        with open(TEST_FILE_PATH, "rb") as f:
            file_bytes = f.read()
        file_content_b64 = base64.b64encode(file_bytes).decode("utf-8")
        print(f"Read and encoded file: {TEST_FILE_PATH}")
    except Exception as e:
        print(f"Error reading or encoding file: {e}")
        return None

    # Prepare JSON payload for UploadFileRequest
    upload_file_request_data = {
        "uuid": file_uuid,
        "username": TEST_USERNAME,
        "file_name": Path(TEST_FILE_PATH).name,
        "file_content_b64": file_content_b64,
    }

    # Create the SignedPayload structure
    signed_upload_payload = sign_payload(upload_file_request_data, private_key)

    # Make the upload request
    response = requests.post(f"{BASE_URL}/files/upload", json=signed_upload_payload)

    print(f"Upload Response Status: {response.status_code}")
    try:
        print(f"Upload Response: {response.json()}")
        return file_uuid if response.status_code == 200 else None
    except json.JSONDecodeError:
        print(f"Upload Response (not JSON): {response.text}")
        return None


def test_file_download(file_uuid, private_key):
    """Test file download with signed payload."""
    print(f"\n=== Testing File Download for UUID: {file_uuid} ===")

    # Create download request payload
    download_payload = {"uuid": file_uuid, "username": TEST_USERNAME}

    # Sign the payload
    signed_payload = sign_payload(download_payload, private_key)

    # Make the download request
    response = requests.post(f"{BASE_URL}/files/download", json=signed_payload)

    print(f"Download Response Status: {response.status_code}")

    if response.status_code == 200:
        # Save downloaded file
        download_path = f"downloaded_{TEST_FILE_PATH}"
        with open(download_path, "wb") as f:
            f.write(response.content)
        print(f"Downloaded file saved as: {download_path}")

        # Compare with original
        with (
            open(TEST_FILE_PATH, "rb") as original,
            open(download_path, "rb") as downloaded,
        ):
            if original.read() == downloaded.read():
                print(
                    "✅ File integrity verified - original and downloaded files match!"
                )
            else:
                print("❌ File integrity check failed - files don't match!")
    else:
        print(f"Download failed: {response.text}")


def test_user_registration(private_key):
    """Test user registration (needed for file operations)."""
    print("\n=== Testing User Registration ===")

    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes_raw()
    public_key_b64 = base64.b64encode(public_key_bytes).decode()

    register_payload = {
        "username": TEST_USERNAME,
        "public_key": public_key_b64,  # Use Base64 encoded public key
    }

    signed_payload = sign_payload(register_payload, private_key)

    response = requests.get(f"{BASE_URL}/auth/register", json=signed_payload)

    print(f"Registration Response Status: {response.status_code}")
    print(f"Registration Response: {response.json()}")

    return response.status_code in [200, 403]  # 403 means user already exists


def main():
    """Main test function."""
    print("🚀 Starting File Upload/Download Tests")

    # Generate test key pair
    private_key = Ed25519PrivateKey.from_private_bytes(
        b"test_key_32_bytes_for_demo_only!"
    )

    # Create test file
    create_test_file()

    # Register user (or use existing)
    if not test_user_registration(private_key):
        print("❌ User registration failed")
        return

    # Test file upload
    file_uuid = test_file_upload(private_key)
    if not file_uuid:
        print("❌ File upload failed")
        return

    # Test file download
    test_file_download(file_uuid, private_key)

    # Cleanup
    # Path(TEST_FILE_PATH).unlink(missing_ok=True)
    # Path(f"downloaded_{TEST_FILE_PATH}").unlink(missing_ok=True)

    print("\n✅ Tests completed!")


if __name__ == "__main__":
    main()
