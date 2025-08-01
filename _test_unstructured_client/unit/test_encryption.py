from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64
from typing import Optional

import pytest

from unstructured_client import UnstructuredClient

@pytest.fixture
def rsa_key_pair():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    return private_key_pem, public_key_pem

@pytest.mark.ignore(reason="Encryption is not in the SDK yet")
def test_encrypt_rsa(rsa_key_pair):
    private_key_pem, public_key_pem = rsa_key_pair

    client = UnstructuredClient()

    plaintext = "This is a secret message."

    secret_obj = client.users.encrypt_secret(public_key_pem, plaintext)

    # A short payload should use direct RSA encryption
    assert secret_obj["type"] == 'rsa'

    decrypted_text = client.users.decrypt_secret(
        private_key_pem,
        secret_obj["encrypted_value"],
        secret_obj["type"],
        "",
        "",
    )
    assert decrypted_text == plaintext


@pytest.mark.ignore(reason="Encryption is not in the SDK yet")
def test_encrypt_rsa_aes(rsa_key_pair):
    private_key_pem, public_key_pem = rsa_key_pair

    client = UnstructuredClient()

    plaintext = "This is a secret message." * 100

    secret_obj = client.users.encrypt_secret(public_key_pem, plaintext)

    # A longer payload uses hybrid RSA-AES encryption
    assert secret_obj["type"] == 'rsa_aes'

    decrypted_text = client.users.decrypt_secret(
        private_key_pem,
        secret_obj["encrypted_value"],
        secret_obj["type"],
        secret_obj["encrypted_aes_key"],
        secret_obj["aes_iv"],
    )
    assert decrypted_text == plaintext


rsa_key_size_bytes = 2048 // 8
max_payload_size = rsa_key_size_bytes - 66  # OAEP SHA256 overhead

@pytest.mark.ignore(reason="Encryption is not in the SDK yet")
@pytest.mark.parametrize(("plaintext", "secret_type"), [
    ("Short message", "rsa"),
    ("A" * (max_payload_size), "rsa"),  # Just at the RSA limit
    ("A" * (max_payload_size + 1), "rsa_aes"),  # Just over the RSA limit
    ("A" * 500, "rsa_aes"),  # Well over the RSA limit
])
def test_encrypt_around_rsa_size_limit(rsa_key_pair, plaintext, secret_type):
    """
    Test that payloads around the RSA size limit choose the correct algorithm.
    """
    _, public_key_pem = rsa_key_pair

    # Load the public key
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode('utf-8'),
        backend=default_backend()
    )

    client = UnstructuredClient()

    secret_obj = client.users.encrypt_secret(public_key_pem, plaintext)

    assert secret_obj["type"] == secret_type
    assert secret_obj["encrypted_value"] is not None