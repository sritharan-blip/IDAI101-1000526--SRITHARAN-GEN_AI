from __future__ import annotations

from fpdf import FPDF


def _safe_text(value: object) -> str:
    text = str(value).replace("\u2022", "-").replace("\u2014", "-").replace("\u2013", "-")
    return text.encode("cp1252", errors="replace").decode("cp1252")


def generate_farm_report(state: dict) -> bytes:
    profile = state.get("farm_profile", {})
    simulation = state.get("yield_simulation", {})
    scans = state.get("disease_scans", [])
    weather = state.get("weather_snapshot") or {}
    current = weather.get("current", {})

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_title("Farm Action Plan")
    pdf.set_author("AgroNova Farm Intelligence")
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(11, 92, 67)
    pdf.multi_cell(_usable_width(pdf), 12, "Farm Action Plan")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(65, 81, 93)
    pdf.multi_cell(_usable_width(pdf), 6, "Prepared from the information saved in this app session.")
    pdf.ln(3)

    _section(pdf, "Farm profile")
    for label, value in (
        ("Location", profile.get("location", "Not specified")),
        ("Coordinates", f"{profile.get('latitude', '—')}, {profile.get('longitude', '—')}"),
        ("Farm size", f"{profile.get('size_ha', 0)} hectares"),
        ("Soil type", profile.get("soil_type", "Unknown")),
        ("Soil pH", profile.get("ph", "Unknown")),
    ):
        _line(pdf, f"{label}: {value}")

    _section(pdf, "Weather snapshot")
    if current:
        _line(pdf, f"Temperature: {current.get('temperature_2m', '—')} C")
        _line(pdf, f"Humidity: {current.get('relative_humidity_2m', '—')}%")
        _line(pdf, f"Precipitation: {current.get('precipitation', '—')} mm")
    else:
        _line(pdf, "No live weather snapshot is saved for this session.")

    _section(pdf, "Yield scenario")
    if simulation:
        _line(pdf, f"Crop: {simulation.get('crop', 'Unspecified crop')}")
        _line(pdf, f"Illustrative yield: {simulation.get('total_yield', 0):.2f} tonnes")
        _line(pdf, f"Assumed gross revenue: {simulation.get('currency', 'USD')} "
                   f"{simulation.get('gross_revenue', 0):,.2f}")
        _line(pdf, "Scenario only; not a validated yield or price forecast.")
    else:
        _line(pdf, "No yield scenario has been saved yet.")

    _section(pdf, "Crop image assessments")
    if scans:
        for index, scan in enumerate(scans, 1):
            _line(pdf, f"{index}. {scan.get('disease', 'Assessment unavailable')} "
                       f"(model confidence {scan.get('confidence', 0)}%)")
            for action in scan.get("treatment_organic", []):
                _line(pdf, f"  Lower-risk action: {action}")
    else:
        _line(pdf, "No crop images have been assessed in this session.")

    _section(pdf, "Important")
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(
        _usable_width(pdf),
        5,
        _safe_text(
            "AI-generated assessments are preliminary and may be incorrect. Confirm diagnoses, "
            "chemical use, and other high-stakes decisions with a qualified local agriculture "
            "professional. Always follow registered product labels and local rules."
        ),
    )
    result = pdf.output()
    return bytes(result)


def _section(pdf: FPDF, title: str) -> None:
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(11, 92, 67)
    pdf.multi_cell(0, 7, _safe_text(title))
    pdf.set_draw_color(210, 230, 219)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _line(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(39, 55, 68)
    pdf.multi_cell(_usable_width(pdf), 6, _safe_text(text))


def _usable_width(pdf: FPDF) -> float:
    return pdf.w - pdf.l_margin - pdf.r_margin
