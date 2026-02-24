"""Shared pytest fixtures."""
import pytest
from pathlib import Path
from wearpark.config import Settings


@pytest.fixture
def temp_cert_files(tmp_path):
    """Create temp certificate files for testing."""
    ca_cert = tmp_path / "ca.pem"
    server_cert = tmp_path / "server.crt"
    server_key = tmp_path / "server.key"
    client_cert = tmp_path / "client.crt"
    client_key = tmp_path / "client.key"
    
    # Create minimal test cert content
    ca_cert.write_text("-----BEGIN CERTIFICATE-----\nCA_CERT_CONTENT\n-----END CERTIFICATE-----")
    server_cert.write_text("-----BEGIN CERTIFICATE-----\nSERVER_CERT_CONTENT\n-----END CERTIFICATE-----")
    server_key.write_text("-----BEGIN PRIVATE KEY-----\nSERVER_KEY_CONTENT\n-----END PRIVATE KEY-----")
    client_cert.write_text("-----BEGIN CERTIFICATE-----\nCLIENT_CERT_CONTENT\n-----END CERTIFICATE-----")
    client_key.write_text("-----BEGIN PRIVATE KEY-----\nCLIENT_KEY_CONTENT\n-----END PRIVATE KEY-----")
    
    return {
        "ca_cert": ca_cert,
        "server_cert": server_cert,
        "server_key": server_key,
        "client_cert": client_cert,
        "client_key": client_key,
    }


@pytest.fixture
def base_settings():
    """Base settings for testing."""
    return Settings(
        host="127.0.0.1",
        port=9999,
        connect_timeout_s=5,
        io_timeout_s=2,
        tls_enabled=False,
    )


@pytest.fixture
def tls_settings(temp_cert_files):
    """TLS settings for testing."""
    return Settings(
        host="127.0.0.1",
        port=9999,
        tls_enabled=True,
        tls_ca_cert_path=str(temp_cert_files["ca_cert"]),
        tls_client_cert_path=str(temp_cert_files["client_cert"]),
        tls_client_key_path=str(temp_cert_files["client_key"]),
        tls_require_client_cert=True,
    )
