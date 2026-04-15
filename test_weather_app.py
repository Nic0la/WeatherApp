"""
test_weather_app.py — Unit tests for weather_app.py

Run with:
    python -m pytest test_weather_app.py -v
"""

import pytest
import requests
from unittest.mock import patch, MagicMock

import weather_app
from weather_app import (
    get_weather,
    get_weather_multiple,
    CityNotFoundError,
    APIError,
    _cache,
)


# ---------------------------------------------------------------------------
# Helpers to build mock responses
# ---------------------------------------------------------------------------

def _geo_mock(city="Rome", lat=41.89, lon=12.48):
    """Return a mock geo-API response for *city*."""
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = {
        "results": [{"name": city, "latitude": lat, "longitude": lon}]
    }
    return m


def _weather_mock(temp=22.5, code=0, wind=15.0):
    """Return a mock weather-API response."""
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = {
        "current": {
            "temperature_2m": temp,
            "weathercode": code,
            "windspeed_10m": wind,
        }
    }
    return m


def _empty_geo_mock():
    """Return a mock geo-API response with no results."""
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = {"results": []}
    return m


# ---------------------------------------------------------------------------
# Tests: get_weather
# ---------------------------------------------------------------------------

class TestGetWeather:
    def setup_method(self):
        """Clear the in-memory cache before every test."""
        _cache.clear()

    @patch("weather_app.SESSION")
    def test_returns_correct_weather_data(self, mock_session):
        """get_weather returns a dict with the expected values."""
        mock_session.get.side_effect = [
            _geo_mock("Rome", 41.89, 12.48),
            _weather_mock(temp=22.5, code=0, wind=15.0),
        ]
        result = get_weather("Rome")

        assert result["city"] == "Rome"
        assert result["temperature_c"] == 22.5
        assert result["wind_speed_kmh"] == 15.0
        assert result["condition"] == "Clear sky"
        assert result["cached"] is False

    @patch("weather_app.SESSION")
    def test_city_not_found_raises_error(self, mock_session):
        """get_weather raises CityNotFoundError for unknown cities."""
        mock_session.get.return_value = _empty_geo_mock()

        with pytest.raises(CityNotFoundError, match="NonExistentCityXYZ"):
            get_weather("NonExistentCityXYZ")

    @patch("weather_app.SESSION")
    def test_http_error_raises_api_error(self, mock_session):
        """get_weather raises APIError when the API returns an HTTP error."""
        bad_mock = MagicMock()
        bad_mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )
        mock_session.get.return_value = bad_mock

        with pytest.raises(APIError):
            get_weather("Rome")

    @patch("weather_app.SESSION")
    def test_timeout_raises_api_error(self, mock_session):
        """get_weather raises APIError when the request times out."""
        mock_session.get.side_effect = requests.exceptions.Timeout

        with pytest.raises(APIError, match="timed out"):
            get_weather("Rome")

    def test_input_too_long_raises_value_error(self):
        """City names longer than MAX_CITY_LEN raise ValueError (no API call made)."""
        with pytest.raises(ValueError):
            get_weather("A" * (weather_app.MAX_CITY_LEN + 1))

    @patch("weather_app.SESSION")
    def test_cache_prevents_second_api_call(self, mock_session):
        """Second call for the same city hits the cache; no extra HTTP requests."""
        mock_session.get.side_effect = [
            _geo_mock("Rome", 41.89, 12.48),
            _weather_mock(22.5, 0, 15.0),
        ]

        get_weather("Rome")            # first call — 2 HTTP requests
        result2 = get_weather("Rome")  # second call — should use cache

        assert result2["cached"] is True
        assert mock_session.get.call_count == 2   # still only 2 total requests

    @patch("weather_app.SESSION")
    def test_unknown_weather_code_returns_unknown(self, mock_session):
        """An unrecognised WMO code produces 'Unknown' as the condition."""
        mock_session.get.side_effect = [
            _geo_mock("Rome", 41.89, 12.48),
            _weather_mock(temp=10.0, code=999, wind=5.0),
        ]
        result = get_weather("Rome")
        assert result["condition"] == "Unknown"


# ---------------------------------------------------------------------------
# Tests: get_weather_multiple
# ---------------------------------------------------------------------------

class TestGetWeatherMultiple:
    def setup_method(self):
        _cache.clear()

    @patch("weather_app.SESSION")
    def test_returns_one_entry_per_city(self, mock_session):
        """get_weather_multiple returns exactly one result per requested city."""
        mock_session.get.side_effect = [
            _geo_mock("Rome",  41.89, 12.48),
            _weather_mock(22.5, 0, 15.0),
            _geo_mock("Tokyo", 35.68, 139.69),
            _weather_mock(18.0, 61, 20.0),
        ]
        results = get_weather_multiple(["Rome", "Tokyo"])

        assert len(results) == 2
        assert results[0]["city"] == "Rome"
        assert results[1]["city"] == "Tokyo"

    @patch("weather_app.SESSION")
    def test_error_in_one_city_does_not_block_others(self, mock_session):
        """A failed city produces an error entry; subsequent cities still succeed."""
        mock_session.get.side_effect = [
            _empty_geo_mock(),                          # BadCity → no results
            _geo_mock("Tokyo", 35.68, 139.69),
            _weather_mock(18.0, 61, 20.0),
        ]
        results = get_weather_multiple(["BadCityXYZ", "Tokyo"])

        assert "error" in results[0]
        assert results[1]["city"] == "Tokyo"
        assert "error" not in results[1]
