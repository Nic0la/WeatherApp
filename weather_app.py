"""
weather_app.py — Weather application using the Open-Meteo API.

Fetches current weather data for one or multiple cities using the free
Open-Meteo API (https://open-meteo.com/) — no API key required.

AI Disclosure: Parts of this code were generated with the assistance of
Claude (Anthropic) and reviewed for correctness and security.
License: MIT
"""

import time
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SESSION = requests.Session()
TIMEOUT = 10          # seconds before a request is aborted
CACHE_TTL = 300       # seconds a cached result stays valid (5 minutes)
MAX_CITY_LEN = 100    # guard against unexpectedly long inputs

# In-memory cache: { cache_key: (unix_timestamp, data) }
_cache: dict = {}

# WMO Weather Interpretation Codes
# Source: https://open-meteo.com/en/docs#weathervariables
WMO_CODES: dict[int, str] = {
    0:  "Clear sky",
    1:  "Mainly clear",   2: "Partly cloudy",  3: "Overcast",
    45: "Fog",           48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain",   63: "Moderate rain",    65: "Heavy rain",
    71: "Slight snow",   73: "Moderate snow",    75: "Heavy snow",
    80: "Slight showers",81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm",  96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class WeatherAppError(Exception):
    """Base exception for all WeatherApp errors."""

class CityNotFoundError(WeatherAppError):
    """Raised when geocoding returns no results for a city name."""

class APIError(WeatherAppError):
    """Raised when an HTTP or network error occurs during an API call."""


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_get(key: str):
    """Return the cached value for *key* if it has not expired, else None."""
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value) -> None:
    """Store *value* under *key* with the current timestamp."""
    _cache[key] = (time.time(), value)


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def _geocode(city: str) -> tuple[float, float, str]:
    """
    Resolve *city* to (latitude, longitude, display_name).

    Results are cached to avoid redundant geocoding API calls.

    Raises:
        CityNotFoundError: if the API returns no matches.
        APIError: on network or HTTP failures.
    """
    cache_key = f"geo:{city.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        response = SESSION.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "format": "json", "language": "en"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise APIError(f"Geocoding request timed out for '{city}'.")
    except requests.exceptions.ConnectionError:
        raise APIError("Cannot reach the geocoding API. Check your internet connection.")
    except requests.exceptions.HTTPError as exc:
        raise APIError(f"Geocoding API error: {exc}") from exc

    data = response.json()
    if not data.get("results"):
        raise CityNotFoundError(f"City not found: '{city}'")

    r = data["results"][0]
    result = (round(r["latitude"], 4), round(r["longitude"], 4), r["name"])
    _cache_set(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# Weather retrieval
# ---------------------------------------------------------------------------

def get_weather(city: str) -> dict:
    """
    Retrieve current weather data for *city*.

    Returns a dict with keys:
        city (str), temperature_c (float), wind_speed_kmh (float),
        condition (str), cached (bool)

    Raises:
        ValueError: if *city* exceeds MAX_CITY_LEN characters.
        CityNotFoundError: if the city cannot be geocoded.
        APIError: on network or HTTP failures.
    """
    # --- Input sanitization ---
    city = city.strip()
    if len(city) > MAX_CITY_LEN:
        raise ValueError(f"City name must be at most {MAX_CITY_LEN} characters.")

    # --- Cache lookup ---
    cache_key = f"weather:{city.lower()}"
    cached = _cache_get(cache_key)
    if cached:
        return {**cached, "cached": True}

    # --- Geocode ---
    lat, lon, display_name = _geocode(city)

    # --- Fetch weather ---
    try:
        response = SESSION.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weathercode,windspeed_10m",
                "forecast_days": 1,
                "timeformat": "unixtime",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise APIError(f"Weather request timed out for '{city}'.")
    except requests.exceptions.ConnectionError:
        raise APIError("Cannot reach the weather API. Check your internet connection.")
    except requests.exceptions.HTTPError as exc:
        raise APIError(f"Weather API error: {exc}") from exc

    current = response.json()["current"]
    code = current.get("weathercode", -1)

    result = {
        "city":            display_name,
        "temperature_c":   current["temperature_2m"],
        "wind_speed_kmh":  current["windspeed_10m"],
        "condition":       WMO_CODES.get(code, "Unknown"),
        "cached":          False,
    }
    # Store without the transient 'cached' flag
    _cache_set(cache_key, {k: v for k, v in result.items() if k != "cached"})
    return result


def get_weather_multiple(cities: list[str]) -> list[dict]:
    """
    Retrieve weather for every city in *cities*.

    Always returns one entry per city. On failure the entry contains an
    'error' key instead of weather data, so a single bad city does not
    abort the entire batch.
    """
    results = []
    for city in cities:
        try:
            results.append(get_weather(city))
        except (WeatherAppError, ValueError) as exc:
            results.append({"city": city, "error": str(exc)})
    return results


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _format_row(data: dict) -> str:
    """Format a single weather result (or error) as a human-readable string."""
    if "error" in data:
        return f"  {'ERROR':>6}  {data['city']}: {data['error']}"
    cached_tag = " (cached)" if data.get("cached") else ""
    return (
        f"  {data['temperature_c']:>5.1f}°C  "
        f"{data['condition']:<30} "
        f"Wind {data['wind_speed_kmh']:>5.1f} km/h  "
        f"{data['city']}{cached_tag}"
    )


def display_weather(cities: list[str]) -> None:
    """Print a formatted weather table for each city in *cities*."""
    print("\n=== Current Weather ===")
    print(f"  {'Temp':>7}  {'Condition':<30} {'Wind':>13}  City")
    print("  " + "-" * 70)
    for row in get_weather_multiple(cities):
        print(_format_row(row))
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Advanced feature: multi-city weather dashboard
    DEFAULT_CITIES = ["Rome", "Tokyo", "New York", "Sydney", "London"]
    display_weather(DEFAULT_CITIES)
