from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from services.analytics import estimate_yield

st.markdown(
    '<section class="hero-panel"><div class="eyebrow">Scenario planner · not a guarantee</div>'
    '<h1>Explore a season.</h1><p>Adjust assumptions to compare an illustrative yield and revenue '
    'scenario. Replace the defaults with local records before making decisions.</p></section>',
    unsafe_allow_html=True,
)


@st.fragment
def render_simulator() -> None:
    profile = st.session_state["farm_profile"]
    controls, chart_col = st.columns([1, 1.7], gap="large")
    with controls:
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
        farm_size = float(profile.get("size_ha", 0))
        st.caption(f"Farm area: {farm_size:g} ha · change it in the sidebar.")

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
    with chart_col:
        st.subheader("Yield and price scenario")
        figure = go.Figure()
        figure.add_trace(go.Bar(
            x=months, y=[result["yield_per_ha"]] * len(months),
            name="Illustrative yield (tonnes/ha)", marker_color="#10b981", opacity=.74,
        ))
        figure.add_trace(go.Scatter(
            x=months, y=price_trend, name=f"Illustrative price ({currency}/tonne)",
            yaxis="y2", line={"color": "#64ffda", "width": 3},
        ))
        text_color = "#e6f1ff" if st.session_state.get("active_theme") == "dark" else "#0f172a"
        figure.update_layout(
            height=390, margin={"l": 10, "r": 10, "t": 28, "b": 10},
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font={"color": text_color}, legend={"orientation": "h", "y": 1.14},
            xaxis={"gridcolor": "rgba(160,180,190,.12)"},
            yaxis={"title": "Yield (tonnes/ha)",
                   "range": [0, max(1, result["yield_per_ha"] * 1.25)],
                   "gridcolor": "rgba(160,180,190,.12)"},
            yaxis2={"title": f"Price ({currency}/tonne)", "overlaying": "y", "side": "right"},
        )
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

    metric1, metric2, metric3 = st.columns(3)
    with metric1:
        yield_value = f"{result['total_yield']:.2f} t" if farm_size else "Set farm size"
        st.metric("Total scenario yield", yield_value,
                  f"{result['yield_per_ha']:.2f} t/ha")
    with metric2:
        revenue = f"{currency} {result['total_yield'] * market_price:,.0f}" if farm_size else "Set farm size"
        st.metric("Illustrative gross revenue", revenue,
                  "Before costs, losses, and transport")
    with metric3:
        total_investment = f"{currency} {investment * farm_size:,.0f}" if farm_size else "Set farm size"
        st.metric("Fertilizer investment", total_investment,
                  "Scenario input only")
    st.session_state["yield_simulation"] = {
        **result,
        "rainfall_mm": rainfall,
        "fertilizer_per_ha": investment,
        "market_price_per_tonne": market_price,
        "currency": currency,
        "farm_size_ha": farm_size,
        "gross_revenue": result["total_yield"] * market_price,
    }


render_simulator()
st.info(
    "This is a simple sensitivity scenario, not a validated yield or price forecast. "
    "It does not include crop variety, planting date, pests, water stress timing, or local price feeds."
)
