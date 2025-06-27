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


def decrypt_secret(
    private_key_pem: str,
    encrypted_value: str,
    type: str,
    encrypted_aes_key: str,
    aes_iv: str,
) -> str:
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
        backend=default_backend()
    )

    if type == 'rsa':
        ciphertext = base64.b64decode(encrypted_value)
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext.decode('utf-8')
    else:
        encrypted_aes_key = base64.b64decode(encrypted_aes_key)
        iv = base64.b64decode(aes_iv)
        ciphertext = base64.b64decode(encrypted_value)

        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        cipher = Cipher(
            algorithms.AES(aes_key),
            modes.CFB(iv),
        )
        decryptor = cipher.decryptor()
        plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        return plaintext.decode('utf-8')


def test_encrypt_rsa(rsa_key_pair):
    private_key_pem, public_key_pem = rsa_key_pair

    client = UnstructuredClient()

    plaintext = "This is a secret message."

    secret_obj = client.users.encrypt_secret(public_key_pem, plaintext)

    # A short payload should use direct RSA encryption
    assert secret_obj["type"] == 'rsa'

    decrypted_text = decrypt_secret(
        private_key_pem,
        secret_obj["encrypted_value"],
        secret_obj["type"],
        "",
        "",
    )
    assert decrypted_text == plaintext

    assert True


def test_encrypt_rsa_aes(rsa_key_pair):
    private_key_pem, public_key_pem = rsa_key_pair

    client = UnstructuredClient()

    plaintext = "This is a secret message." * 100

    secret_obj = client.users.encrypt_secret(public_key_pem, plaintext)

    # A longer payload uses hybrid RSA-AES encryption
    assert secret_obj["type"] == 'rsa_aes'

    decrypted_text = decrypt_secret(
        private_key_pem,
        secret_obj["encrypted_value"],
        secret_obj["type"],
        secret_obj["encrypted_aes_key"],
        secret_obj["aes_iv"],
    )
    assert decrypted_text == plaintext

    assert True