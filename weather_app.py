import requests

SESSION = requests.Session()
TIMEOUT = 10

def get_weather(city):
    geo_response = SESSION.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "format": "json", "language": "en"},
        timeout=TIMEOUT
    )
    geo_response.raise_for_status()
    geo_data = geo_response.json()

    if not geo_data.get("results"):
        return {"error": "City not found"}

    result = geo_data["results"][0]
    lat, lon = round(result["latitude"], 2), round(result["longitude"], 2)

    weather_response = SESSION.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weathercode,windspeed_10m",
            "forecast_days": 1,
            "timeformat": "unixtime"
        },
        timeout=TIMEOUT
    )
    weather_response.raise_for_status()
    return weather_response.json()

print(get_weather("Tokyo"))