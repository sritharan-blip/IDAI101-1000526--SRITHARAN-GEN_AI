from __future__ import annotations

import asyncio

import requests
import streamlit as st

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_weather_async(latitude: float, longitude: float) -> dict:
    """Fetch current conditions and a short forecast without blocking the event loop."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
        "hourly": "soil_moisture_0_to_1cm",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min",
        "forecast_days": 7,
        "timezone": "auto",
    }

    def request() -> dict:
        response = requests.get(WEATHER_URL, params=params, timeout=12)
        response.raise_for_status()
        return response.json()

    return await asyncio.to_thread(request)


@st.cache_data(ttl=3600, show_spinner=False)
def get_weather(latitude: float, longitude: float) -> dict:
    return asyncio.run(fetch_weather_async(latitude, longitude))
