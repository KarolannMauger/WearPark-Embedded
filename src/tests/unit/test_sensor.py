import pytest
import wearpark.sensor as sensor_module
from wearpark.errors import ErrorCode, WearParkError
from wearpark.sensor import ICM20948Sensor
from unittest.mock import Mock


def test_sensor_init_raises_when_dependencies_missing(monkeypatch):
    monkeypatch.setattr(sensor_module, "_SENSOR_AVAILABLE", False)
    monkeypatch.setattr(sensor_module, "_SENSOR_IMPORT_ERROR", Exception("missing deps"))
    with pytest.raises(WearParkError) as exc:
        ICM20948Sensor()
    assert exc.value.code == ErrorCode.SENSOR_INIT_FAILED


def test_sensor_read_success(monkeypatch):
    """Test lecture du capteur."""
    monkeypatch.setattr(sensor_module, "_SENSOR_AVAILABLE", True)
    
    # Mock board et sensor
    mock_board = Mock()
    mock_i2c = Mock()
    mock_board.I2C.return_value = mock_i2c
    
    mock_icm_class = Mock()
    mock_icm = Mock()
    mock_icm.acceleration = (1.0, 2.0, 3.0)
    mock_icm.gyro = (4.0, 5.0, 6.0)
    mock_icm_class.return_value = mock_icm
    
    monkeypatch.setattr(sensor_module, "board", mock_board)
    monkeypatch.setattr(sensor_module, "adafruit_icm20x", Mock(ICM20948=mock_icm_class))
    
    sensor = ICM20948Sensor()
    result = sensor.read()
    
    assert result == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)


def test_sensor_read_fails(monkeypatch):
    """Test échec de lecture."""
    monkeypatch.setattr(sensor_module, "_SENSOR_AVAILABLE", True)
    
    mock_board = Mock()
    mock_i2c = Mock()
    mock_board.I2C.return_value = mock_i2c
    
    mock_icm_class = Mock()
    mock_icm = Mock()
    mock_icm.acceleration = property(lambda self: (_ for _ in ()).throw(Exception("read error")))
    mock_icm_class.return_value = mock_icm
    
    monkeypatch.setattr(sensor_module, "board", mock_board)
    monkeypatch.setattr(sensor_module, "adafruit_icm20x", Mock(ICM20948=mock_icm_class))
    
    sensor = ICM20948Sensor()
    
    with pytest.raises(WearParkError) as exc:
        sensor.read()
    assert exc.value.code == ErrorCode.SENSOR_READ_FAILED