from __future__ import annotations

from datetime import date
from html import escape

import folium
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

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
    max_rainfall = max((value for value in rainfall if value is not None), default=0)
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


def _reading(value, unit: str, decimals: int = 0) -> str:
    return f"{value:.{decimals}f}<small>{unit}</small>" if isinstance(value, (float, int)) else "—"


def _metric(label: str, value: str, detail: str, icon: str, tone: str) -> str:
    return (
        f'<article class="field-metric {tone}"><span class="field-icon" aria-hidden="true">{icon}</span>'
        f'<h2>{label}</h2><p>{detail}</p><strong>{value}</strong></article>'
    )


def _rain_dots(dates: list, rainfall: list) -> str:
    days = list(zip(dates, rainfall))
    if not any(isinstance(value, (int, float)) for _, value in days):
        return '<p class="field-empty">Daily rainfall appears when a forecast is available.</p>'
    peak = max((value for _, value in days if isinstance(value, (int, float))), default=0)
    columns = []
    for day, value in days:
        label = date.fromisoformat(day).strftime("%a")
        amount = f"{value:g} mm" if isinstance(value, (int, float)) else "unavailable"
        dots = round(12 * value / peak) if peak and isinstance(value, (int, float)) else 0
        columns.append(
            f'<li title="{label}: {amount}"><span class="field-dots" aria-hidden="true" '
            f'style="--dot-height:{dots * 8}px"></span><span>{label}</span>'
            f'<span class="field-sr">: {amount}</span></li>'
        )
    return '<ul class="field-rain-chart" aria-label="Daily rainfall">' + "".join(columns) + "</ul>"


profile = st.session_state["farm_profile"]
latitude, longitude = profile["latitude"], profile["longitude"]
coordinates = (latitude, longitude)
location = escape(profile.get("location") or "Farm pin")
st.html(
    f'<section class="field-heading"><div><p>AGRONOVA / COMMAND CENTER</p>'
    f'<h1>Farm overview</h1></div><span class="field-location">⌖ &nbsp; {location}</span></section>'
)

with st.container(horizontal=True, key="field_shortcuts"):
    st.page_link("components/ai_chat.py", label="Ask Novi", icon=":material/forum:")
    st.page_link("components/vision_scanner.py", label="Scan a crop", icon=":material/psychiatry:")
    st.page_link("components/yield_simulator.py", label="Yield & finance", icon=":material/monitoring:")
    st.page_link("components/legacy_workflows.py", label="Advisor", icon=":material/agriculture:")

with st.spinner("Refreshing local forecast…"):
    try:
        weather = get_weather(*coordinates)
        st.session_state["weather_snapshot"] = weather
        st.session_state["weather_coordinates"] = coordinates
        weather_status = "Open-Meteo forecast"
    except Exception:
        weather = (st.session_state.get("weather_snapshot")
                   if st.session_state.get("weather_coordinates") == coordinates else None)
        weather_status = "Last available forecast" if weather else "Weather feed unavailable"

current = (weather or {}).get("current", {})
daily = (weather or {}).get("daily", {})
rainfall = daily.get("precipitation_sum") or []
known_rainfall = [value for value in rainfall if isinstance(value, (int, float))]
rain_total = sum(known_rainfall) if known_rainfall else None
soil_series = (weather or {}).get("hourly", {}).get("soil_moisture_0_to_1cm") or []
soil_moisture = next((value for value in soil_series if value is not None), None)
wind = current.get("wind_speed_10m")
weather_code = current.get("weather_code")
conditions = _weather_description(weather_code) if weather_code is not None else "Current conditions unavailable"

cards = [
    _metric("Air temperature", _reading(current.get("temperature_2m"), "°C"), conditions, "☼", "field-sun"),
    _metric("Humidity", _reading(current.get("relative_humidity_2m"), "%"),
            f"Wind {wind:g} km/h" if isinstance(wind, (int, float)) else "Current relative humidity", "≈", "field-leaf"),
    _metric("Rain now", _reading(current.get("precipitation"), "mm", 1), "Current precipitation", "⋮", "field-rain"),
    _metric("Surface soil moisture", _reading(soil_moisture, "m³/m³", 2),
            "Open-Meteo model estimate", "⌑", "field-soil"),
]
st.html(
    '<section class="field-overview" aria-label="Farm weather">'
    '<div class="field-metrics">' + "".join(cards) + '</div>'
    '<article class="field-outlook"><div class="field-outlook-head"><h2>Seven-day rainfall</h2>'
    '<span class="field-icon" aria-hidden="true">↗</span></div>'
    f'<strong>{_reading(rain_total, "mm", 1)}</strong><p>{weather_status}</p>'
    f'{_rain_dots(daily.get("time") or [], rainfall)}</article></section>'
)

left, right = st.columns([1.3, 1], gap="medium")
with left, st.container(border=True, key="field_forecast"):
    st.subheader("Temperature & rain")
    if weather:
        st.plotly_chart(_forecast_chart(weather), theme=None, width="stretch", config={"displayModeBar": False})
    else:
        st.info("The forecast will appear here when Open-Meteo is reachable.")
with right, st.container(border=True, key="field_map"):
    st.subheader("Farm location")
    st.caption(profile.get("location") or "Edit coordinates in the sidebar")
    map_view = folium.Map(
        location=[latitude, longitude], zoom_start=7,
        tiles="OpenStreetMap", control_scale=True,
    )
    folium.Marker(
        [latitude, longitude], tooltip=location,
        popup=escape(f"Farm · {latitude:.4f}, {longitude:.4f}"),
        icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
    ).add_to(map_view)
    st_folium(map_view, height=270, width=None, returned_objects=[])
