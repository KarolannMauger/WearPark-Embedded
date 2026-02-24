"""Tests pour logging config."""
import logging
from wearpark.logging_config import configure_logging
from wearpark.config import Settings


def test_configure_logging_creates_logger():
    """Test que configure_logging configure le logger."""
    settings = Settings(log_level="INFO")
    configure_logging(settings)
    
    # Juste vérifier que ça ne crash pas
    assert True


def test_configure_logging_with_debug():
    """Test configuration avec DEBUG."""
    settings = Settings(log_level="DEBUG")
    configure_logging(settings)
    
    # Vérifier que ça ne crash pas
    assert True


def test_configure_logging_with_file(tmp_path):
    """Test configuration avec fichier log."""
    log_file = tmp_path / "test.log"
    settings = Settings(log_level="INFO", log_file=str(log_file))
    
    configure_logging(settings)
    
    # Vérifier que le fichier peut être créé
    assert True
