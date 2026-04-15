# Weather App

A command-line Python application that fetches current weather data for one or
more cities using the free [Open-Meteo API](https://open-meteo.com/) — no API
key or account required.

## Features

| Feature | Details |
|---|---|
| Live weather data | Temperature, wind speed, sky condition |
| **Multi-city dashboard** | Query any number of cities in a single run |
| **In-memory cache** | Results cached 5 minutes to reduce API load |
| Robust error handling | Clear messages for network errors, city not found, HTTP failures |
| Input sanitisation | Rejects blank or excessively long city names |

## How it works

1. The city name is resolved to coordinates via the **Open-Meteo Geocoding API**
2. The coordinates are used to fetch current weather from the **Open-Meteo Forecast API**
3. Results are cached in memory for 5 minutes; repeated calls for the same city skip the API entirely

## Requirements

- Python 3.10+
- `requests` library
- `pytest` for running the test suite

## Setup

```bash
# Create and activate the virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install requests pytest
```

## Usage

### Run the default multi-city dashboard

```bash
python weather_app.py
```

Sample output:

```
=== Current Weather ===
   Temp  Condition                      Wind  City
  ----------------------------------------------------------------------
   22.5°C  Clear sky                       Wind  15.0 km/h  Rome
   18.0°C  Slight rain                     Wind  20.0 km/h  Tokyo
  ...
```

### Use as a library

```python
from weather_app import get_weather, get_weather_multiple

# Single city — raises CityNotFoundError or APIError on failure
data = get_weather("Paris")
print(data["temperature_c"], data["condition"])

# Multiple cities — errors are returned as dict entries, not raised
results = get_weather_multiple(["Berlin", "Cairo", "Seoul"])
for r in results:
    if "error" in r:
        print(f"{r['city']}: {r['error']}")
    else:
        print(f"{r['city']}: {r['temperature_c']}°C, {r['condition']}")
```

## Return format (`get_weather`)

| Key | Type | Description |
|---|---|---|
| `city` | str | Display name returned by geocoding |
| `temperature_c` | float | Air temperature at 2 m (°C) |
| `wind_speed_kmh` | float | Wind speed at 10 m (km/h) |
| `condition` | str | Human-readable WMO weather description |
| `cached` | bool | `True` if the result was served from cache |

WMO weather codes reference: https://open-meteo.com/en/docs#weathervariables

## Error handling

| Situation | Exception raised |
|---|---|
| City not found | `CityNotFoundError` |
| HTTP error (4xx / 5xx) | `APIError` |
| Network / connection error | `APIError` |
| Request timeout | `APIError` |
| City name > 100 characters | `ValueError` |

Both `CityNotFoundError` and `APIError` inherit from `WeatherAppError`, so you
can catch either individually or together with `except WeatherAppError`.

## Running Tests

```bash
python -m pytest test_weather_app.py -v
```

The test suite covers:

- Successful weather data retrieval
- City not found → `CityNotFoundError`
- HTTP 500 → `APIError`
- Timeout → `APIError`
- Input validation (city name too long) → `ValueError`
- Cache hit prevents duplicate HTTP requests
- Unknown WMO codes → `"Unknown"` condition
- Batch fetch: one error does not abort others

## Security & Ethics

- **No secrets in code** — Open-Meteo is a keyless public API; no credentials
  are stored anywhere in this project.
- **Input validation** — city names are trimmed and length-checked before use,
  guarding against excessively long or malformed inputs.
- **Responsible API usage** — the built-in TTL cache limits redundant requests
  to Open-Meteo's free public infrastructure.
- **AI disclosure** — portions of this code were generated with the assistance
  of [Claude](https://claude.ai/) (Anthropic) and reviewed for correctness and
  security before inclusion.
- **Data licence** — weather data provided by
  [Open-Meteo](https://open-meteo.com/) under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

## Licence

MIT
