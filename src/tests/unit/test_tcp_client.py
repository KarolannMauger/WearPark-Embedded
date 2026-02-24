"""Tests basiques pour TCP client."""
import socket
import pytest
from unittest.mock import Mock, patch, MagicMock
from wearpark.tcp_client import TcpClient
from wearpark.errors import ErrorCode, WearParkError


def test_tcp_client_init(base_settings):
    """Test initialisation du client TCP."""
    client = TcpClient(base_settings)
    assert client.s == base_settings
    assert client.sock is None


def test_tcp_client_connect_plain(base_settings, monkeypatch):
    """Test connexion TCP simple."""
    mock_sock = Mock()
    mock_create = Mock(return_value=mock_sock)
    monkeypatch.setattr(socket, "create_connection", mock_create)
    
    client = TcpClient(base_settings)
    client.connect()
    
    assert client.sock == mock_sock
    mock_create.assert_called_once()
    mock_sock.settimeout.assert_called_with(base_settings.io_timeout_s)


def test_tcp_client_sendall(base_settings):
    """Test envoi de données."""
    client = TcpClient(base_settings)
    client.sock = Mock()
    
    client.sendall(b"test data")
    client.sock.sendall.assert_called_once_with(b"test data")


def test_tcp_client_sendall_timeout(base_settings):
    """Test timeout lors de l'envoi."""
    client = TcpClient(base_settings)
    client.sock = Mock()
    client.sock.sendall.side_effect = socket.timeout()
    
    with pytest.raises(WearParkError) as exc:
        client.sendall(b"data")
    assert exc.value.code == ErrorCode.ENOTCONN
    assert client.sock is None


def test_tcp_client_sendall_no_socket(base_settings):
    """Test envoi sans socket."""
    client = TcpClient(base_settings)
    
    with pytest.raises(WearParkError) as exc:
        client.sendall(b"data")
    assert exc.value.code == ErrorCode.ENOTCONN


def test_tcp_client_recv_until_newline(base_settings):
    """Test réception jusqu'à newline."""
    client = TcpClient(base_settings)
    client.sock = Mock()
    client.sock.recv.side_effect = [b"hello", b"\n"]
    
    result = client.recv_until_newline()
    assert result == b"hello\n"


def test_tcp_client_recv_timeout(base_settings):
    """Test timeout lors de la réception."""
    client = TcpClient(base_settings)
    client.sock = Mock()
    client.sock.recv.side_effect = socket.timeout()
    
    with pytest.raises(WearParkError) as exc:
        client.recv_until_newline()
    assert exc.value.code == ErrorCode.ECONNRESET


def test_tcp_client_recv_closed_connection(base_settings):
    """Test connexion fermée."""
    client = TcpClient(base_settings)
    client.sock = Mock()
    client.sock.recv.return_value = b""
    
    with pytest.raises(WearParkError) as exc:
        client.recv_until_newline()
    assert exc.value.code == ErrorCode.ECONNRESET


def test_tcp_client_close(base_settings):
    """Test fermeture du client."""
    client = TcpClient(base_settings)
    mock_sock = Mock()
    client.sock = mock_sock
    
    client.close()
    mock_sock.close.assert_called_once()
    assert client.sock is None


def test_tcp_client_close_no_socket(base_settings):
    """Test fermeture sans socket."""
    client = TcpClient(base_settings)
    client.close()  # Ne devrait pas crasher


def test_validate_file_missing(base_settings, tmp_path):
    """Test validation fichier manquant."""
    client = TcpClient(base_settings)
    
    with pytest.raises(WearParkError) as exc:
        client._validate_file(str(tmp_path / "missing.pem"), "TEST_FILE")
    assert exc.value.code == ErrorCode.TLS_CONFIG_ERROR


def test_validate_file_empty_path(base_settings):
    """Test validation chemin vide."""
    client = TcpClient(base_settings)
    
    with pytest.raises(WearParkError) as exc:
        client._validate_file("", "TEST_FILE")
    assert exc.value.code == ErrorCode.TLS_CONFIG_ERROR


def test_connect_with_tls(tls_settings, monkeypatch):
    """Test connexion avec TLS."""
    mock_sock = Mock()
    mock_ssl_sock = Mock()
    mock_ssl_sock.cipher.return_value = ("TLS_AES_256", "TLSv1.3", 256)
    
    mock_create = Mock(return_value=mock_sock)
    mock_context = Mock()
    mock_context.wrap_socket.return_value = mock_ssl_sock
    
    monkeypatch.setattr(socket, "create_connection", mock_create)
    
    with patch("ssl.create_default_context", return_value=mock_context):
        client = TcpClient(tls_settings)
        client.connect()
    
    assert client.sock == mock_ssl_sock
    mock_context.wrap_socket.assert_called_once()


def test_tcp_client_keepalive_error(base_settings, monkeypatch):
    """Test que le client continue même si keepalive échoue."""
    mock_sock = Mock()
    mock_sock.setsockopt.side_effect = OSError("Not supported")
    
    mock_create = Mock(return_value=mock_sock)
    monkeypatch.setattr(socket, "create_connection", mock_create)
    
    client = TcpClient(base_settings)
    client.connect()
    
    assert client.sock == mock_sock


def test_tcp_client_ssl_handshake_error(tls_settings, monkeypatch):
    """Test erreur lors du handshake SSL."""
    import ssl
    
    mock_sock = Mock()
    mock_create = Mock(return_value=mock_sock)
    mock_context = Mock()
    mock_context.wrap_socket.side_effect = ssl.SSLError("Handshake failed")
    
    monkeypatch.setattr(socket, "create_connection", mock_create)
    
    with patch("ssl.create_default_context", return_value=mock_context):
        client = TcpClient(tls_settings)
        
        with pytest.raises(WearParkError) as exc:
            client.connect()
        
        assert exc.value.code == ErrorCode.TLS_HANDSHAKE_FAILED
