import pytest
from unittest.mock import MagicMock, patch, mock_open
from enviroplus_logger.enviroplus_logger import (
    upload_file,
    get_environmantal_data,
    main,
)

# Mock RPi.GPIO module
# RPi = MagicMock()
# RPi.GPIO = MagicMock()


def test_upload_file():
    with patch("boto3.client") as mock:
        mock.return_value.upload_file.return_value = True
        assert upload_file("test_file", "test_bucket", 1234567890) == True
        mock.return_value.upload_file.side_effect = Exception("Test exception")
        assert upload_file("test_file", "test_bucket", 1234567890) == False


def test_get_environmantal_data():
    mock_bme280 = MagicMock()
    mock_bme280.get_temperature.return_value = 20.0
    mock_bme280.get_pressure.return_value = 1000.0
    mock_bme280.get_humidity.return_value = 50.0

    mock_ltr559 = MagicMock()
    mock_ltr559.get_lux.return_value = 100.0
    mock_ltr559.get_proximity.return_value = 1.0

    mock_gas = MagicMock()
    mock_gas.read_all.return_value = "Test gas data"

    result = get_environmantal_data(mock_bme280, mock_gas, mock_ltr559)
    assert result["temperature"] == 20.0
    assert result["pressure"] == 1000.0
    assert result["humidity"] == 50.0
    assert result["brightness"] == 100.0
    assert result["proximity"] == 1.0
    assert result["gas_sensor"] == "Test gas data"
