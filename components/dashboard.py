from __future__ import annotations

import json
from datetime import date
from html import escape

import folium
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium
from streamlit_lottie import st_lottie

from components.metrics_cards import render_metric
from config.settings import ASSET_DIR
from services.weather_api import get_weather


def _weather_description(code: int) -> str:
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Partly cloudy"
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Rain"
    if code in (71, 73, 75, 85, 86):
        return "Snow"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return "Conditions available"


def _forecast_chart(weather: dict) -> go.Figure:
    daily = weather.get("daily", {})
    dates = daily.get("time", [])
    rainfall = daily.get("precipitation_sum", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    date_labels = []
    for value in dates:
        try:
            date_labels.append(date.fromisoformat(str(value)[:10]).strftime("%b %d"))
        except ValueError:
            date_labels.append(str(value))
    max_rainfall = max(rainfall, default=0) if rainfall else 0
    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=rainfall, name="Rainfall", marker_color="#10b981", opacity=.78))
    fig.add_trace(go.Scatter(x=dates, y=highs, name="High °C", yaxis="y2",
                             line={"color": "#fbbf24", "width": 2}))
    fig.add_trace(go.Scatter(x=dates, y=lows, name="Low °C", yaxis="y2",
                             line={"color": "#64ffda", "width": 2, "dash": "dot"}))
    text_color = "#e6f1ff" if st.session_state.get("active_theme") == "dark" else "#0f172a"
    fig.update_layout(
        height=320, margin={"l": 8, "r": 8, "t": 28, "b": 8},
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"color": text_color}, legend={"orientation": "h", "y": 1.14},
        xaxis={"title": None, "type": "category", "categoryorder": "array", "categoryarray": dates,
               "tickmode": "array", "tickvals": dates, "ticktext": date_labels, "tickangle": 0,
               "gridcolor": "rgba(160,180,190,.12)"},
        yaxis={"title": "Rain (mm)", "range": [0, max(1, max_rainfall * 1.2)],
               "gridcolor": "rgba(160,180,190,.12)"},
        yaxis2={"title": "Temperature (°C)", "overlaying": "y", "side": "right"},
    )
    return fig


st.markdown(
    '<section class="hero-panel"><div class="eyebrow">Precision agriculture · command center</div>'
    '<h1>Your farm, in focus.</h1><p>Local weather, clear context, and practical next steps — '
    'all in one calm workspace.</p></section>',
    unsafe_allow_html=True,
)

profile = st.session_state["farm_profile"]
latitude, longitude = profile["latitude"], profile["longitude"]
weather = None
with st.spinner("Refreshing local forecast…"):
    try:
        weather = get_weather(latitude, longitude)
        st.session_state["weather_snapshot"] = weather
    except Exception as exc:
        st.error(f"Could not load live weather from Open-Meteo: {str(exc)[:220]}", icon="🌦️")

col1, col2, col3 = st.columns([1, 2, 1], gap="medium")
current = weather.get("current", {}) if weather else {}
with col1:
    if weather:
        render_metric("Temperature", f"{current.get('temperature_2m', '—')}°C",
                      "Current local observation · Open-Meteo", "🌡️")
    else:
        render_metric("Weather", "Unavailable", "Check coordinates or try again later", "🌦️")
with col3:
    if weather:
        render_metric("Humidity", f"{current.get('relative_humidity_2m', '—')}%",
                      f"Wind {current.get('wind_speed_10m', '—')} km/h", "💧")
    else:
        render_metric("Humidity", "Unavailable", "Waiting for a weather snapshot", "💧")

with col2:
    animation_path = ASSET_DIR / "farm_lottie.json"
    try:
        with animation_path.open(encoding="utf-8") as file:
            st_lottie(json.load(file), height=130, key="farm_animation",
                      loop=True, quality="low")
    except (OSError, json.JSONDecodeError):
        st.markdown('<div class="glass-card" style="padding:1rem;text-align:center">'
                    '🌿 &nbsp; Growing a clearer picture of your farm</div>',
                    unsafe_allow_html=True)

left, right = st.columns([1.45, 1], gap="large")
with left:
    if weather:
        st.subheader("Seven-day outlook")
        st.caption("Forecast for the coordinates saved in your farm profile.")
        st.plotly_chart(_forecast_chart(weather), width="stretch", config={"displayModeBar": False})
    else:
        st.info("A live forecast will appear here when the weather service is reachable.")
with right:
    st.subheader("Farm location")
    st.caption(profile.get("location") or "Farm pin · edit in the sidebar")
    map_view = folium.Map(
        location=[latitude, longitude], zoom_start=7,
        tiles="OpenStreetMap", control_scale=True,
    )
    folium.Marker(
        [latitude, longitude],
        tooltip=escape(profile.get("location") or "Your farm"),
        popup=escape(f"Farm · {latitude:.4f}, {longitude:.4f}"),
        icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
    ).add_to(map_view)
    st_folium(map_view, height=330, width=None, returned_objects=[])
    st.caption("OpenStreetMap tiles are fetched for the displayed area.")

if weather:
    soil_moisture = (weather.get("hourly", {}).get("soil_moisture_0_to_1cm") or [None])[0]
    micro1, micro2, micro3 = st.columns(3)
    with micro1:
        render_metric("Rain now", f"{current.get('precipitation', '—')} mm",
                      "Current precipitation", "🌧️")
    with micro2:
        value = f"{soil_moisture:.2f} m³/m³" if isinstance(soil_moisture, (int, float)) else "Unavailable"
        render_metric("Surface soil moisture", value,
                      "Open-Meteo model estimate · not a field sensor", "🪴")
    with micro3:
        daily_total = sum(weather.get("daily", {}).get("precipitation_sum", []) or [])
        render_metric("Forecast rain", f"{daily_total:.1f} mm",
                      "Total over the next seven days", "☔")
    st.caption(
        f"Current weather: {_weather_description(int(current.get('weather_code', -1)))}. "
        "Satellite imagery and NDVI are not connected; no vegetation index is inferred."
    )
