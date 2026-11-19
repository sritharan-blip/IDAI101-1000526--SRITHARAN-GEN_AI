from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from components.page_header import render_page_header
from services.analytics import estimate_yield

render_page_header(
    "Yield & finance",
    "Explore how rainfall, fertilizer spending, and market price affect a season’s estimated yield and revenue.",
    "yield", "↗",
)


@st.fragment
def render_simulator() -> None:
    profile = st.session_state["farm_profile"]
    totals = st.container(key="yield_totals")
    controls, chart_col = st.columns([1, 1.7], gap="medium")
    with controls, st.container(border=True, key="yield_controls"):
        st.subheader("Scenario inputs")
        crop = st.text_input("Crop", value="Maize", key="sim_crop")
        rainfall = st.slider("Season rainfall simulation (mm)", 0, 1800, 650, 25, key="sim_rainfall")
        currency = st.selectbox("Currency", ["USD", "INR", "GHS", "CAD"], key="sim_currency")
        investment = st.slider(
            f"Fertilizer investment per hectare ({currency})", 0, 3000, 450, 50, key="sim_investment"
        )
        market_price = st.number_input(f"Assumed market price per tonne ({currency})",
                                       min_value=0.0, value=220.0, step=10.0, key="sim_market_price")
        price_change = st.slider("Illustrative price movement over 6 months (%)", -30, 50, 5,
                                 key="sim_price_change")
        farm_size = st.number_input(
            "Area in this scenario (ha)", min_value=0.0, max_value=100000.0,
            value=float(profile.get("size_ha", 0)), step=0.5, key="sim_area",
            help="Defaults to your farm profile. Leave it at zero to compare results per hectare.",
        )

    result = estimate_yield(
        farm_size,
        float(rainfall),
        float(investment),
        profile.get("soil_type", "Unknown"),
        crop,
    )
    months = ["Now", "Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"]
    price_trend = [
        market_price * (1 + price_change * step / 600) for step in range(7)
    ]
    final_price = price_trend[-1]
    gross_revenue = result["total_yield"] * final_price
    with chart_col, st.container(border=True, key="yield_chart"):
        st.subheader("Yield and price scenario")
        figure = go.Figure()
        figure.add_trace(go.Bar(
            x=months, y=[result["yield_per_ha"]] * len(months),
            name="Illustrative yield (tonnes/ha)", marker_color="#6fb681", opacity=.83,
        ))
        figure.add_trace(go.Scatter(
            x=months, y=price_trend, name=f"Illustrative price ({currency}/tonne)",
            yaxis="y2", line={"color": "#d4ee89" if st.session_state["active_theme"] == "dark" else "#426b16", "width": 3},
        ))
        text_color = "#e6f1ff" if st.session_state.get("active_theme") == "dark" else "#0f172a"
        figure.update_layout(
            height=390, margin={"l": 12, "r": 12, "t": 62, "b": 18},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": text_color}, legend={"orientation": "h", "y": 1.04},
            xaxis={"automargin": True, "showgrid": False},
            yaxis={"title": "Yield (tonnes/ha)",
                   "range": [0, max(1, result["yield_per_ha"] * 1.25)],
                   "automargin": True, "gridcolor": "rgba(108,137,123,.28)"},
            yaxis2={"title": f"Price ({currency}/tonne)", "overlaying": "y", "side": "right",
                    "automargin": True, "showgrid": False},
        )
        st.plotly_chart(figure, theme=None, width="stretch", config={"displayModeBar": False})

    metric1, metric2, metric3 = totals.columns(3)
    with metric1, st.container(border=True):
        yield_value = f"{result['total_yield']:.2f} t" if farm_size else f"{result['yield_per_ha']:.2f} t/ha"
        st.metric("Scenario yield", yield_value)
        st.caption(f"{result['yield_per_ha']:.2f} t/ha" if farm_size else "Add an area to see total yield")
    with metric2, st.container(border=True):
        revenue = gross_revenue if farm_size else result["yield_per_ha"] * final_price
        st.metric("Gross revenue at month 6", f"{currency} {revenue:,.0f}" + ("" if farm_size else "/ha"))
        st.caption("Before costs, losses, and transport")
    with metric3, st.container(border=True):
        total_investment = investment * farm_size if farm_size else investment
        st.metric("Fertilizer investment", f"{currency} {total_investment:,.0f}" + ("" if farm_size else "/ha"))
        st.caption("Scenario input")
    st.session_state["yield_simulation"] = {
        **result,
        "rainfall_mm": rainfall,
        "fertilizer_per_ha": investment,
        "market_price_per_tonne": market_price,
        "projected_price_per_tonne": final_price,
        "currency": currency,
        "farm_size_ha": farm_size,
        "gross_revenue": gross_revenue,
    }


render_simulator()
st.info(
    "This is a simple sensitivity scenario, not a validated yield or price forecast. "
    "It does not include crop variety, planting date, pests, water stress timing, or local price feeds."
)
