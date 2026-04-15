# Weather App

A simple Python script that retrieves current weather data for any city using the [Open-Meteo](https://open-meteo.com/) API. No API key required.

## How it works

1. The city name is resolved to coordinates via the **Open-Meteo Geocoding API**
2. The coordinates are used to fetch current weather from the **Open-Meteo Forecast API**

## Requirements

- Python 3.x
- `requests` library

## Setup

```bash
# Create and activate the virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install requests
```

## Usage

```bash
python weather_app.py
```

To use `get_weather` in your own code:

```python
from weather_app import get_weather

result = get_weather("Roma")
print(result["current"]["temperature_2m"])  # e.g. 18.4
```

## Response format

```json
{
  "current": {
    "temperature_2m": 12.9,
    "weathercode": 55,
    "windspeed_10m": 7.8
  }
}
```

| Field | Unit | Description |
|---|---|---|
| `temperature_2m` | °C | Air temperature at 2 m |
| `weathercode` | WMO code | Weather condition code |
| `windspeed_10m` | km/h | Wind speed at 10 m |

WMO weather codes reference: https://open-meteo.com/en/docs#weathervariables

## Error handling

| Situation | Behaviour |
|---|---|
| City not found | Returns `{"error": "City not found"}` |
| HTTP error (4xx/5xx) | Raises `requests.exceptions.HTTPError` |
| Network error | Raises `requests.exceptions.ConnectionError` |

## Known limitations

- `results` being an empty list is not handled (causes `IndexError`) — use `if not geo_data.get("results"):` as a fix
- No `timeout` set on HTTP requests — the call can hang indefinitely
- City name accepts any string without validation
