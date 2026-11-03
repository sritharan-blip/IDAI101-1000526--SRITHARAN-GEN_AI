"""
🌾 Gen AI Smart Farming Assistant  (AgroNova pilot – FA-2)
===========================================================
A Streamlit web app that turns Gemini's answers into clear, trustworthy,
region-specific farming advice for farmers in India, Ghana and Canada.

Features
  1. Advisor        – structured inputs -> Gemini -> cards, steps, warnings, "why" for each tip
  2. Validation Lab – runs 6 regional test prompts (baseline vs optimised prompt), auto-scores
                      them on a 5-point feedback checklist, parameter (temperature) experiment
  3. Insights       – usage monitoring + user-feedback analytics
  4. About          – how it works, limitations, responsible-AI notes

Run locally:   streamlit run app.py
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import os
import re
import time
import uuid
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402
import streamlit as st  # noqa: E402

from google import genai as genai_new
from google.genai import types as genai_types

# ─────────────────────────────────────────────────────────────────────────────
# 0. CONFIG
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("GENAI_DATA_DIR", "data"))
DATA_DIR.mkdir(exist_ok=True)
USAGE_LOG = DATA_DIR / "usage_log.csv"
FEEDBACK_LOG = DATA_DIR / "feedback.csv"
VALIDATION_LOG = DATA_DIR / "validation_results.csv"
MANUAL_LOG = DATA_DIR / "manual_checklist.csv"

# Used when no key is available yet or the API model catalog cannot be loaded.
# With a key, the picker is populated from the models enabled for that key.
MODEL_CHOICES = [
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]
MAX_QUERIES_PER_SESSION = 40  # protects the free API quota on a public deployment
COOLDOWN_SECONDS = 2

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
STAGES = ["Planning (nothing planted yet)", "Land preparation", "Sowing / planting", "Seedling",
          "Vegetative growth", "Flowering", "Fruiting / grain filling", "Harvest", "Post-harvest / storage"]
SOILS = ["Not sure", "Sandy", "Loamy", "Clay", "Silty", "Black (regur)", "Red", "Laterite"]
WATER = ["Rain-fed only", "Limited irrigation", "Good irrigation"]
FARM_SIZES = ["Small (under 2 ha)", "Medium (2–10 ha)", "Large (over 10 ha)"]
PREFERENCES = ["Organic methods", "Low water use", "Low cost", "High profit", "Pest-resistant",
               "Fast-growing", "Beginner-friendly"]
LANGUAGES = ["English", "Hindi (हिन्दी)", "French (Français)", "Twi", "Hausa", "Tamil (தமிழ்)",
             "Punjabi (ਪੰਜਾਬੀ)", "Marathi (मराठी)"]

COUNTRIES = {
    "India": {
        "flag": "🇮🇳",
        "regions": ["Rajasthan", "Punjab", "Maharashtra", "Tamil Nadu", "Uttar Pradesh",
                    "West Bengal", "Karnataka", "Gujarat"],
        "authority": "your nearest Krishi Vigyan Kendra (KVK), state agriculture department, "
                     "or the Kisan Call Centre (1800-180-1551)",
    },
    "Ghana": {
        "flag": "🇬🇭",
        "regions": ["Ashanti", "Northern", "Eastern", "Volta", "Bono", "Western", "Greater Accra"],
        "authority": "your district Ministry of Food and Agriculture (MoFA) extension office",
    },
    "Canada": {
        "flag": "🇨🇦",
        "regions": ["Saskatchewan", "Ontario", "Alberta", "Manitoba", "Quebec",
                    "British Columbia", "Nova Scotia"],
        "authority": "your provincial agriculture ministry or local agrologist / extension service",
    },
    "Other": {
        "flag": "🌍",
        "regions": [],
        "authority": "your local agricultural extension office",
    },
}

FOCUS = {
    "🌱 What to grow": ("crop selection",
                        "Recommend the best crops to grow now. For each crop say what to do and why it suits "
                        "this place, month, soil and water situation."),
    "🐛 Pests & diseases": ("pest and disease management",
                            "Explain the most likely pest/disease risks right now and how to scout for and control "
                            "them, starting with low-risk, low-cost methods."),
    "💧 Irrigation & water": ("irrigation and water management",
                              "Give a practical irrigation / water-saving plan for this crop stage and weather."),
    "🧪 Soil & fertiliser": ("soil health and fertiliser",
                             "Give soil preparation and nutrient-management advice suited to this crop stage."),
    "🧺 Harvest & storage": ("harvest and post-harvest storage",
                             "Explain when and how to harvest, dry and store to avoid losses."),
    "💬 Free question": ("the farmer's own question",
                         "Answer the farmer's own question directly using the profile as context."),
}

TRUSTED_SOURCES = [
    ("FAO – Food and Agriculture Organization", "https://www.fao.org/"),
    ("India – Dept. of Agriculture & Farmers Welfare", "https://agriwelfare.gov.in/"),
    ("India – ICAR (research council)", "https://icar.org.in/"),
    ("Ghana – Ministry of Food and Agriculture", "https://mofa.gov.gh/"),
    ("Canada – Agriculture and Agri-Food Canada", "https://agriculture.canada.ca/"),
]

DISCLAIMER = ("⚠️ AI-generated advice can be wrong. Check important decisions (especially pesticide use) "
              "with a local agriculture expert before acting.")

# ─────────────────────────────────────────────────────────────────────────────
# 1. STYLING
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
.stApp {background: radial-gradient(ellipse at 85% 0%, rgba(116, 196, 159, .16), transparent 34%),
         linear-gradient(145deg, #f8fbf8 0%, #eff6f0 54%, #f5f8f2 100%);}
.block-container {padding-top: 1.7rem; max-width: 1380px;}
[data-testid="stSidebar"] {background: linear-gradient(155deg, rgba(12, 48, 37, .98), rgba(22, 91, 67, .95));}
[data-testid="stSidebar"] > div:first-child {background: transparent;}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] label, [data-testid="stSidebar"] .stCaption {
    color: #eef9f2;
}
.hero {background: linear-gradient(120deg, rgba(10, 69, 49, .96), rgba(28, 132, 91, .88) 58%, rgba(132, 189, 105, .82));
       border: 1px solid rgba(255,255,255,.35); border-radius: 24px; padding: 1.55rem 1.8rem;
       color: #fff; margin-bottom: 1.15rem; box-shadow: 0 18px 48px rgba(13, 69, 48, .16);
       backdrop-filter: blur(18px);}
.hero h1 {margin: 0; font-size: 2.1rem; color:#fff; padding:0;}
.hero p {margin: .35rem 0 0 0; opacity: .95; font-size: 1.02rem;}
.pill {display:inline-block; padding:.12rem .6rem; border-radius:999px; font-size:.78rem;
       background:rgba(46,125,50,.14); color:#2e7d32; margin-right:.3rem; font-weight:600;}
.pill.warn {background:rgba(239,108,0,.14); color:#e65100;}
.pill.bad {background:rgba(198,40,40,.14); color:#c62828;}
.summary {border-left: 5px solid #43a879; background: rgba(255,255,255,.68);
          padding: .9rem 1.05rem; border-radius: 16px; font-size: 1.05rem;
          box-shadow: 0 8px 26px rgba(31, 83, 58, .07); backdrop-filter: blur(14px);}
.why {color:#33691e; font-size:.95rem;}
.small-note {font-size:.85rem; opacity:.8;}
.stTabs [data-baseweb="tab-list"] {gap: .35rem; padding: .35rem; border: 1px solid rgba(78, 132, 99, .17);
    border-radius: 18px; background: rgba(255,255,255,.56); backdrop-filter: blur(18px);
    box-shadow: 0 8px 28px rgba(27, 74, 51, .07);}
.stTabs button[role="tab"] {border-radius: 13px; padding: .55rem .85rem;}
.stTabs button[role="tab"][aria-selected="true"] {background: rgba(38, 133, 91, .13); color: #146343;}
div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea, .stNumberInput input {
    border-radius: 14px; border: 1px solid rgba(68, 122, 91, .2);
    background: rgba(255,255,255,.67); backdrop-filter: blur(16px);
    box-shadow: inset 0 1px 0 rgba(255,255,255,.72), 0 5px 16px rgba(31,83,58,.045);
}
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] .stTextInput input {
    background: rgba(244,255,248,.12); border-color: rgba(220,255,234,.2); color: #f2fff7;
}
[data-testid="stSidebar"] input::placeholder {color: rgba(239,255,245,.56);}
[data-baseweb="popover"], [data-baseweb="menu"] {
    border: 1px solid rgba(255,255,255,.66); border-radius: 16px;
    background: rgba(248, 253, 249, .84); backdrop-filter: blur(24px) saturate(1.45);
    box-shadow: 0 18px 54px rgba(16, 57, 40, .2); overflow: hidden;
}
[data-baseweb="popover"] [role="option"], [data-baseweb="menu"] li {
    border-radius: 10px; margin: 3px 6px; transition: background .16s ease, color .16s ease;
}
[data-baseweb="popover"] [role="option"]:hover, [data-baseweb="menu"] li:hover {
    background: rgba(57, 151, 105, .14); color: #145b3e;
}
.stMultiSelect [data-baseweb="tag"] {border-radius: 999px; background: rgba(48, 139, 94, .14);}
.stRadio [role="radiogroup"] label {padding: .35rem .55rem; border-radius: 12px;}
.stButton button, .stDownloadButton button, [data-testid="stPopover"] button {
    border-radius: 14px; transition: transform .16s ease, box-shadow .16s ease;
}
.stButton button:hover, .stDownloadButton button:hover, [data-testid="stPopover"] button:hover {
    transform: translateY(-1px); box-shadow: 0 8px 20px rgba(24, 103, 70, .16);
}
[data-testid="stExpander"], [data-testid="stMetric"] {
    border-radius: 16px; border-color: rgba(68, 122, 91, .17);
    background: rgba(255,255,255,.48); backdrop-filter: blur(14px);
}
@media (max-width: 640px){ .hero h1{font-size:1.5rem;} .hero p{font-size:.92rem;} }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. SMALL HELPERS (logging, secrets)
# ─────────────────────────────────────────────────────────────────────────────

def append_csv(path: Path, row: dict) -> None:
    """Append one row to a CSV file (creates it with a header if needed). Never crashes the app."""
    try:
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if new:
                w.writeheader()
            w.writerow(row)
    except Exception:
        pass


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def get_api_key() -> str:
    """Key priority: Streamlit secrets -> environment variable -> sidebar box."""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "") or st.session_state.get("sidebar_key", "")


@st.cache_data(ttl=900, show_spinner=False)
def list_gemini_models(api_key: str) -> list[str]:
    """Return text-generation Gemini models currently available to this API key."""
    client = genai_new.Client(api_key=api_key)
    models = client.models.list()
    available = []
    for model in models:
        name = (getattr(model, "name", "") or "").rsplit("/", 1)[-1]
        actions = getattr(model, "supported_actions", None) or []
        if name.startswith("gemini-") and "generateContent" in actions:
            available.append(name)

    priority = {name: index for index, name in enumerate(MODEL_CHOICES)}
    return sorted(set(available), key=lambda name: (priority.get(name, len(priority)), name))


# ─────────────────────────────────────────────────────────────────────────────
# 3. PROMPTS  (Step 5 – prompt optimisation: V1 baseline  ->  V2 optimised)
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA = """{
  "summary": "2 short sentences: the key message for the farmer",
  "recommendations": [
    {"icon": "one emoji", "name": "crop / practice name (local name in brackets)",
     "action": "what to do, one short sentence",
     "why": "one short sentence explaining WHY (climate, soil, water or crop stage)",
     "timing": "when to do it, e.g. 'Next 2 weeks'"}
  ],
  "steps": ["numbered action steps, in order, each one short sentence"],
  "warnings": ["risks or safety notes the farmer must know"],
  "local_tip": "one practical tip specific to this place",
  "confidence": "High | Medium | Low"
}"""


def build_prompt(inp: dict, version: str, weather_text: str = "") -> str:
    focus_label, focus_instruction = FOCUS[inp["focus"]]
    place = f'{inp["region"]}, {inp["country"]}'
    crop = inp.get("crop") or "not specified"
    if version == "V1":  # naive baseline, intentionally minimal
        q = inp.get("question") or f"Give me advice on {focus_label}"
        return f"{q} for farming in {place} in {inp['month']}."
    prefs = ", ".join(inp["preferences"]) or "none"
    authority = COUNTRIES.get(inp["country"], COUNTRIES["Other"])["authority"]
    return f"""You are AgroNova's Smart Farming Assistant, an agronomy adviser for farmers with little formal education.

FARMER PROFILE
- Location: {place}
- Month: {inp['month']}
- Current crop: {crop}
- Crop stage: {inp['stage']}
- Soil: {inp['soil']}
- Water: {inp['water']}
- Farm size: {inp['farm_size']}
- Preferences: {prefs}
- Farmer's own question: {inp.get('question') or 'none'}
{('- Weather forecast: ' + weather_text) if weather_text else ''}

TASK: Advise on {focus_label}. {focus_instruction}

RULES
1. Be specific to {place} and {inp['month']}; use local crop names, e.g. "Pearl millet (Bajra)".
2. Use simple words and short sentences (grade-6 reading level). Explain any technical term in brackets.
3. EVERY recommendation must include a one-sentence "why" based on climate, soil, water or crop stage.
4. Give 3 to 5 recommendations, then 3 to 6 ordered action steps.
5. Never invent pesticide brand names or exact chemical doses. Say "follow the product label" and prefer
   low-risk methods (scouting, crop rotation, natural enemies, neem) first.
6. If information is missing or you are unsure, say so, set confidence to "Low" and advise checking with
   {authority}.
7. Respect the farmer's preferences and stay realistic for their farm size and water access.
8. Write ALL text values in {inp['language']}. Keep the JSON keys in English.

OUTPUT: return ONLY valid JSON, exactly in this shape (no markdown fences):
{SCHEMA}"""


# ─────────────────────────────────────────────────────────────────────────────
# 4. GEMINI CALL  (+ automatic model fallback)
# ─────────────────────────────────────────────────────────────────────────────
class GeminiError(Exception):
    pass


def _generate(name: str, prompt: str, api_key: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    """Generate content with Google's current Gemini SDK."""
    cfg = {"temperature": temperature, "max_output_tokens": max_tokens}
    if json_mode:
        cfg["response_mime_type"] = "application/json"
    if "flash" in name and "2.5" in name:
        cfg["thinking_config"] = genai_types.ThinkingConfig(thinking_budget=0)
    client = genai_new.Client(api_key=api_key)
    return (client.models.generate_content(
        model=name,
        contents=prompt,
        config=genai_types.GenerateContentConfig(**cfg),
    ).text or "").strip()


def call_gemini(prompt: str, api_key: str, model: str, temperature: float,
                max_tokens: int, json_mode: bool,
                fallback_models: list[str] | None = None) -> tuple[str, str]:
    """Returns (text, model actually used), trying current key-enabled models on model errors."""
    order = [model] + [m for m in (fallback_models or MODEL_CHOICES) if m != model]
    last_err = None
    for name in order:
        try:
            text = _generate(name, prompt, api_key, temperature, max_tokens, json_mode)
            if text:
                return text, name
            last_err = GeminiError("Empty response (possibly blocked by safety filters).")
        except Exception as e:  # noqa: BLE001
            last_err = e
            msg = str(e).lower()
            # only fall back for "model missing / unsupported"; stop on key/quota problems
            if not any(k in msg for k in ("not found", "404", "not supported", "deprecated", "no longer")):
                break
    raise GeminiError(str(last_err) if last_err else "Unknown Gemini error")


# ─────────────────────────────────────────────────────────────────────────────
# 5. OUTPUT CLEANING  (Step 4 – formatting & reasoning)
# ─────────────────────────────────────────────────────────────────────────────

def extract_json(text: str):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def parse_plain_text(text: str) -> dict:
    """Turn a messy wall of text (baseline prompt) into the same structure as the JSON path."""
    clean = re.sub(r"[*_#`>]+", "", text)
    lines = [re.sub(r"^\s*(?:[-•]|\d+[.)])\s*", "", l).strip() for l in clean.splitlines() if l.strip()]
    if len(lines) < 4:
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean.strip()) if s.strip()]
    pat = r"^(.{3,45}?)(?::\s+|\s[-–—]\s)(.+)$"
    if lines and re.match(pat, lines[0]):  # list straight away, no intro sentence
        summary, items = "Here is the advice, tidied into a list.", lines[:6]
    else:
        summary, items = (lines[0] if lines else clean[:200]), lines[1:7]
    recs = []
    for it in items:
        m = re.match(pat, it)
        name, action = (m.group(1).strip(), m.group(2).strip()) if m else (" ".join(it.split()[:4]), it)
        recs.append({"icon": "🌾", "name": name, "action": action, "why": "", "timing": ""})
    return {"summary": summary, "recommendations": recs, "steps": [], "warnings": [],
            "local_tip": "", "confidence": "Unknown"}


def normalise(data: dict) -> dict:
    """Make sure every field exists and has the right type, whatever Gemini returned."""
    def s(x):
        return str(x).strip() if x is not None else ""

    recs = []
    for r in data.get("recommendations", []) or []:
        if isinstance(r, dict):
            recs.append({"icon": s(r.get("icon")) or "🌾", "name": s(r.get("name")) or "Recommendation",
                         "action": s(r.get("action")), "why": s(r.get("why")), "timing": s(r.get("timing"))})
        elif isinstance(r, str):
            recs.append({"icon": "🌾", "name": r[:40], "action": r, "why": "", "timing": ""})
    as_list = lambda v: [s(i) for i in v if s(i)] if isinstance(v, list) else ([s(v)] if s(v) else [])  # noqa: E731
    return {"summary": s(data.get("summary")), "recommendations": recs, "steps": as_list(data.get("steps")),
            "warnings": as_list(data.get("warnings")), "local_tip": s(data.get("local_tip")),
            "confidence": s(data.get("confidence")) or "Medium"}


def result_text(d: dict) -> str:
    """Flatten a result to plain text (used for scoring + downloads)."""
    parts = [d["summary"]]
    for r in d["recommendations"]:
        parts += [r["name"], r["action"], r["why"], r["timing"]]
    parts += d["steps"] + d["warnings"] + [d["local_tip"]]
    return " ".join(p for p in parts if p)


def to_markdown(inp: dict, d: dict) -> str:
    out = [f"# Smart Farming Advice – {inp['region']}, {inp['country']} ({inp['month']})", "",
           f"**Focus:** {inp['focus']}  |  **Stage:** {inp['stage']}  |  **Confidence:** {d['confidence']}", "",
           f"> {d['summary']}", "", "## Recommendations"]
    for r in d["recommendations"]:
        out.append(f"- **{r['name']}** – {r['action']}  \n  *Why:* {r['why'] or '—'}"
                   + (f"  \n  *When:* {r['timing']}" if r["timing"] else ""))
    if d["steps"]:
        out += ["", "## Action steps"] + [f"{i}. {x}" for i, x in enumerate(d["steps"], 1)]
    if d["warnings"]:
        out += ["", "## Warnings"] + [f"- ⚠️ {w}" for w in d["warnings"]]
    if d["local_tip"]:
        out += ["", f"**Local tip:** {d['local_tip']}"]
    out += ["", f"_{DISCLAIMER}_", f"_Generated {dt.datetime.now():%Y-%m-%d %H:%M} by Gen AI Smart Farming Assistant_"]
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# 6. DEMO MODE  (works with no API key – used for offline demos / screenshots)
# ─────────────────────────────────────────────────────────────────────────────
DEMO_KB = {
    "India": {
        "crops": [("🌾", "Pearl Millet (Bajra)", "Sow with the first good rain.", "Drought-resistant and thrives in arid, sandy soil."),
                  ("🫘", "Cluster Bean (Guar)", "Sow in lines on well-drained soil.", "Ideal for sandy soil and tolerates low water."),
                  ("🌱", "Green Gram (Moong)", "Use a short-duration variety.", "Quick-growing legume that suits a short monsoon cycle."),
                  ("🫛", "Moth Bean", "Sow after the monsoon sets in.", "Very hardy kharif legume that needs little water and also enriches the soil.")],
        "pest": "Pink bollworm and whitefly are common in monsoon. Scout weekly.",
        "tip": "Your Krishi Vigyan Kendra (KVK) can test your soil for free or at low cost.",
    },
    "Ghana": {
        "crops": [("🌽", "Maize", "Plant when rains are steady for two weeks.", "Needs reliable rain; the main rainy season suits it well."),
                  ("🫘", "Cowpea (Beans)", "Plant after maize or between rows.", "Fast-growing legume that adds nitrogen to the soil."),
                  ("🥜", "Groundnut", "Plant on loose, sandy-loam soil.", "Handles light soils common in the region and sells well."),
                  ("🍠", "Cassava", "Use healthy stem cuttings.", "Tolerates dry spells and gives food security.")],
        "pest": "Fall armyworm attacks young maize. Check the leaf whorl (the funnel at the top) twice a week.",
        "tip": "Join a farmer-based organisation to share seed and get extension visits.",
    },
    "Canada": {
        "crops": [("🌾", "Spring Wheat", "Seed as soon as soil is workable and above 5°C.", "Cool-season crop that grows well in short Prairie summers."),
                  ("🌼", "Canola", "Seed into warm soil (about 8–10°C).", "Strong cash crop that fits wheat rotations and cool nights."),
                  ("🫛", "Field Peas", "Seed early and shallow.", "Fixes its own nitrogen, lowering fertiliser cost."),
                  ("🌿", "Oats", "Seed early for best yield.", "Hardy, low-input crop that tolerates cool, wet spring conditions.")],
        "pest": "Flea beetles attack young canola. Check seedlings daily for the first 3 weeks.",
        "tip": "Check soil temperature and your last frost date before seeding.",
    },
}
DEMO_KB["Other"] = DEMO_KB["India"]

DEMO_FOCUS_STEPS = {
    "🐛 Pests & diseases": ["Walk through the field twice a week and check 20 plants.",
                            "Remove and bury badly damaged plants.",
                            "Use neem-based sprays or natural enemies first.",
                            "Only use chemicals if the label and local expert say so."],
    "💧 Irrigation & water": ["Water early in the morning to lose less to the sun.",
                              "Irrigate at critical stages: flowering and grain filling.",
                              "Mulch the soil with straw to keep moisture in.",
                              "Skip irrigation for 2 days after heavy rain."],
    "🧪 Soil & fertiliser": ["Add well-rotted compost before planting.",
                             "Test your soil (pH and nutrients) at a local lab.",
                             "Apply fertiliser in small split doses, not all at once.",
                             "Rotate with a legume crop next season."],
    "🧺 Harvest & storage": ["Harvest on a dry, sunny day.",
                             "Dry the produce until it is properly dry before storing.",
                             "Store in clean, airtight bags off the ground.",
                             "Check stored grain every 2 weeks for insects."],
}


def demo_response(inp: dict, version: str) -> str:
    kb = DEMO_KB.get(inp["country"], DEMO_KB["India"])
    place = f'{inp["region"]}, {inp["country"]}'
    if version == "V1":  # deliberately generic, long-winded baseline output
        return (f"Farming in {place} depends on many agronomic factors including the phenological stage of the "
                f"cultivar, edaphic conditions and evapotranspiration. Farmers should consider growing suitable crops "
                f"and managing their land well. It is important to use good practices, fertilizers, and water "
                f"management. Crop selection should be based on the market and the season. Consult resources for more "
                f"information. Monitoring is recommended throughout the growing cycle.")
    if inp["focus"] == "🌱 What to grow":
        recs = [{"icon": i, "name": n, "action": a, "why": w, "timing": "Next 2 weeks"} for i, n, a, w in kb["crops"][:4]]
        steps = ["Check the rain forecast before sowing.", "Prepare a fine, weed-free seedbed.",
                 "Buy certified seed from a trusted shop.", "Sow in lines to make weeding easier.",
                 "Weed 3–4 weeks after sowing."]
    else:
        base = DEMO_FOCUS_STEPS.get(inp["focus"], DEMO_FOCUS_STEPS["🐛 Pests & diseases"])
        steps = base
        recs = [{"icon": "🔍", "name": f"Step {k}", "action": st_, "why": "Small, early actions cost less and protect yield.",
                 "timing": "This week"} for k, st_ in enumerate(base[:3], 1)]
        recs[0]["name"] = "Monitor first"
    data = {"summary": f"For {place} in {inp['month']}, focus on options that fit your {inp['soil'].lower()} soil and "
                       f"{inp['water'].lower()} water. {kb['pest']}",
            "recommendations": recs, "steps": steps,
            "warnings": ["Never spray chemicals without reading the product label.",
                         "Wear gloves and a mask when handling any crop-protection product."],
            "local_tip": kb["tip"], "confidence": "Medium"}
    return json.dumps(data, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# 7. WEATHER  (Open-Meteo, free, no key – uses `requests`)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_weather(place: str) -> dict | None:
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": place, "count": 1}, timeout=8).json()
        if not g.get("results"):
            return None
        loc = g["results"][0]
        w = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": loc["latitude"], "longitude": loc["longitude"], "timezone": "auto", "forecast_days": 7,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
            "current": "temperature_2m,relative_humidity_2m"}, timeout=8).json()
        d = w["daily"]
        df = pd.DataFrame({"date": pd.to_datetime(d["time"]), "max": d["temperature_2m_max"],
                           "min": d["temperature_2m_min"], "rain": d["precipitation_sum"]})
        return {"place": f'{loc["name"]}, {loc.get("country", "")}', "df": df, "now": w.get("current", {})}
    except Exception:
        return None


def weather_summary(w: dict) -> str:
    df = w["df"]
    return (f"next 7 days in {w['place']}: highs {df['max'].min():.0f}–{df['max'].max():.0f}°C, "
            f"lows {df['min'].min():.0f}–{df['min'].max():.0f}°C, total rain {df['rain'].sum():.0f} mm")


def weather_chart(w: dict):
    df = w["df"]
    fig, ax = plt.subplots(figsize=(6.4, 2.8), facecolor="white")
    ax.bar(df["date"], df["rain"], color="#64b5f6", width=0.6, label="Rain (mm)")
    ax.set_ylabel("Rain (mm)")
    ax2 = ax.twinx()
    ax2.plot(df["date"], df["max"], color="#e53935", marker="o", label="High °C")
    ax2.plot(df["date"], df["min"], color="#1e88e5", marker="o", label="Low °C")
    ax2.set_ylabel("Temperature °C")
    ax.set_xticks(df["date"])
    ax.set_xticklabels(df["date"].dt.strftime("%a %d"), fontsize=8)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper center", ncol=3, fontsize=8, frameon=False,
              bbox_to_anchor=(0.5, 1.2))
    for a in (ax, ax2):
        a.spines["top"].set_visible(False)
    fig.tight_layout()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 8. CORE PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_advice(inp: dict, cfg: dict, version: str = "V2", temperature: float | None = None,
               weather_text: str = "", log: bool = True) -> dict:
    """prompt -> Gemini (or demo) -> parse -> clean. Always returns a dict, never raises."""
    temperature = cfg["temperature"] if temperature is None else temperature
    prompt = build_prompt(inp, version, weather_text)
    t0 = time.time()
    raw, model_used, error = "", cfg["model"], ""
    try:
        if cfg["demo"]:
            time.sleep(0.4)
            raw, model_used = demo_response(inp, version), "demo-mode"
        else:
            raw, model_used = call_gemini(prompt, cfg["api_key"], cfg["model"], temperature,
                                          cfg["max_tokens"], json_mode=(version == "V2"),
                                          fallback_models=cfg["model_choices"])
    except Exception as e:  # noqa: BLE001
        error = str(e)
    latency = round(time.time() - t0, 2)

    data, parsed_ok = None, False
    if raw:
        data = extract_json(raw) if version == "V2" else None
        parsed_ok = isinstance(data, dict)
        data = normalise(data) if parsed_ok else normalise(parse_plain_text(raw))
    result = {"data": data, "raw": raw, "prompt": prompt, "latency": latency, "model": model_used,
              "error": error, "json_ok": parsed_ok, "version": version, "temperature": temperature}
    if log:
        append_csv(USAGE_LOG, {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"), "country": inp["country"],
            "region": inp["region"], "focus": inp["focus"], "language": inp["language"],
            "model": model_used, "prompt_version": version, "temperature": temperature,
            "latency_s": latency, "success": int(bool(data)), "json_ok": int(parsed_ok)})
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 9. RENDERING
# ─────────────────────────────────────────────────────────────────────────────

def conf_pill(c: str) -> str:
    cls = {"high": "", "medium": "warn", "low": "bad"}.get(c.lower().split()[0], "warn")
    return f'<span class="pill {cls}">Confidence: {c}</span>'


def render_advice(inp: dict, res: dict) -> None:
    d = res["data"]
    st.markdown(f'<div class="summary">{d["summary"]}</div>', unsafe_allow_html=True)
    st.markdown(
        conf_pill(d["confidence"])
        + f'<span class="pill">{inp["country"]} · {inp["region"]}</span>'
        + f'<span class="pill">{inp["month"]}</span>'
        + f'<span class="pill">⏱ {res["latency"]}s · {res["model"]}</span>',
        unsafe_allow_html=True)
    st.write("")
    if d["recommendations"]:
        st.subheader("✅ Recommendations")
        cols = st.columns(2)
        for i, r in enumerate(d["recommendations"]):
            with cols[i % 2].container(border=True):
                st.markdown(f"#### {r['icon']} {r['name']}")
                st.markdown(r["action"])
                if r["why"]:
                    st.markdown(f'<div class="why">💡 <b>Why:</b> {r["why"]}</div>', unsafe_allow_html=True)
                if r["timing"]:
                    st.caption(f"🕒 {r['timing']}")
    if d["steps"]:
        st.subheader("📋 Your action plan")
        for i, s in enumerate(d["steps"], 1):
            st.markdown(f"**{i}.** {s}")
    if d["warnings"]:
        st.warning("**Be careful:**\n\n" + "\n".join(f"- {w}" for w in d["warnings"]))
    if d["local_tip"]:
        st.info(f"📍 **Local tip:** {d['local_tip']}")
    authority = COUNTRIES.get(inp["country"], COUNTRIES["Other"])["authority"]
    st.caption(f"{DISCLAIMER} Contact {authority}.")


def feedback_widget(req_id: str, inp: dict, res: dict) -> None:
    st.divider()
    st.subheader("⭐ Was this advice helpful?")
    stars = st.feedback("stars", key=f"stars_{req_id}")
    comment = st.text_input("Anything missing or wrong? (optional)", key=f"cmt_{req_id}", max_chars=300)
    if st.button("Send feedback", key=f"fb_{req_id}"):
        if stars is None:
            st.warning("Please pick a star rating first.")
        else:
            append_csv(FEEDBACK_LOG, {
                "timestamp": dt.datetime.now().isoformat(timespec="seconds"), "request_id": req_id,
                "country": inp["country"], "region": inp["region"], "focus": inp["focus"],
                "prompt_version": res["version"], "rating": stars + 1, "comment": comment})
            st.success("Thank you! Your feedback helps us improve the assistant. 🙏")
            st.balloons()


# ─────────────────────────────────────────────────────────────────────────────
# 10. VALIDATION  (Step 5 – test cases, checklist, scoring)
# ─────────────────────────────────────────────────────────────────────────────
TEST_CASES = [
    {"id": "T1", "country": "India", "region": "Rajasthan", "month": "August", "stage": "Planning (nothing planted yet)",
     "soil": "Sandy", "water": "Rain-fed only", "focus": "🌱 What to grow", "crop": "",
     "preferences": ["Low water use"],
     "expect": ["bajra|pearl millet", "guar|cluster bean", "moong|green gram|moth", "monsoon|kharif", "sandy|arid|dry"],
     "region_terms": ["rajasthan", "india", "arid", "monsoon", "kharif"],
     "source": ("Dept. of Agriculture & Farmers Welfare (India) – kharif crops", "https://agriwelfare.gov.in/")},
    {"id": "T2", "country": "India", "region": "Punjab", "month": "November", "stage": "Sowing / planting",
     "soil": "Loamy", "water": "Good irrigation", "focus": "💧 Irrigation & water", "crop": "Wheat",
     "preferences": ["Low water use"],
     "expect": ["wheat", "irrigat", "crown root|first irrigation|21|three weeks", "rabi|winter|cool", "seed|sow"],
     "region_terms": ["punjab", "india", "rabi", "canal", "tube"],
     "source": ("ICAR – wheat production guidance", "https://icar.org.in/")},
    {"id": "T3", "country": "Ghana", "region": "Ashanti", "month": "June", "stage": "Vegetative growth",
     "soil": "Loamy", "water": "Rain-fed only", "focus": "🐛 Pests & diseases", "crop": "Maize",
     "preferences": ["Low cost", "Organic methods"],
     "expect": ["fall armyworm|armyworm", "scout|check|inspect", "neem|natural|biopesticide|hand", "whorl|leaf|leaves", "extension|mofa|label"],
     "region_terms": ["ghana", "ashanti", "mofa", "maize"],
     "source": ("FAO – Fall Armyworm in Africa", "https://www.fao.org/fall-armyworm/en/")},
    {"id": "T4", "country": "Ghana", "region": "Northern", "month": "April", "stage": "Planning (nothing planted yet)",
     "soil": "Sandy", "water": "Rain-fed only", "focus": "🌱 What to grow", "crop": "",
     "preferences": ["Low cost", "Beginner-friendly"],
     "expect": ["maize|sorghum|millet", "groundnut|cowpea|soy", "rain", "onset|start|season|plant", "sandy|light|soil"],
     "region_terms": ["ghana", "northern", "savanna", "savannah", "tamale", "mofa"],
     "source": ("Ghana MoFA – crop production", "https://mofa.gov.gh/")},
    {"id": "T5", "country": "Canada", "region": "Saskatchewan", "month": "May", "stage": "Sowing / planting",
     "soil": "Loamy", "water": "Rain-fed only", "focus": "🌱 What to grow", "crop": "",
     "preferences": ["High profit"],
     "expect": ["wheat", "canola|pea|oat|barley", "soil temperature|frost|cold", "seed", "moisture|rain|soil"],
     "region_terms": ["saskatchewan", "canada", "prairie", "frost"],
     "source": ("Agriculture and Agri-Food Canada", "https://agriculture.canada.ca/")},
    {"id": "T6", "country": "Canada", "region": "Ontario", "month": "October", "stage": "Harvest",
     "soil": "Clay", "water": "Rain-fed only", "focus": "🧺 Harvest & storage", "crop": "Soybean",
     "preferences": ["Beginner-friendly"],
     "expect": ["moisture", "dry", "storage|store|bin", "frost|weather|rain", "soybean|bean"],
     "region_terms": ["ontario", "canada", "frost", "soybean"],
     "source": ("Agriculture and Agri-Food Canada", "https://agriculture.canada.ca/")},
]

CHECKLIST = [
    ("region", "Is the advice specific to the input region?"),
    ("reasoning", "Does the output provide valid and logical reasoning (a 'why' for each tip)?"),
    ("simple", "Is the language simple enough for a layperson?"),
    ("specific", "Is it specific rather than too generic or technical?"),
    ("safe", "Does it avoid misleading or unsafe advice (no invented doses, tells user to verify)?"),
]
JARGON = ["phenolog", "agronomic", "evapotranspiration", "edaphic", "cultivar", "phytosanitary", "bioavailab",
          "mycorrhiz", "photosynthat", "allelopath", "stomatal"]


def _syllables(word: str) -> int:
    word = re.sub(r"[^a-z]", "", word.lower())
    return max(1, len(re.findall(r"[aeiouy]+", word)))


def flesch(text: str) -> float:
    words = re.findall(r"[A-Za-z']+", text)
    sents = max(1, len(re.findall(r"[.!?]+", text)))
    if not words:
        return 0.0
    syl = sum(_syllables(w) for w in words)
    return round(206.835 - 1.015 * len(words) / sents - 84.6 * syl / len(words), 1)


def score_output(case: dict, d: dict | None) -> dict:
    """Automatic 5-point score using the feedback checklist. Heuristics, not a substitute for expert review."""
    if not d:
        return {**{k: False for k, _ in CHECKLIST}, "score": 0, "flesch": 0.0, "hits": 0.0}
    text = result_text(d).lower()
    recs = d["recommendations"]
    region = any(t in text for t in case["region_terms"])
    reasoning = bool(recs) and sum(1 for r in recs if len(r["why"].split()) >= 5) / len(recs) >= 0.75
    fre = flesch(result_text(d))
    simple = fre >= 50 and not any(j in text for j in JARGON)
    hits = sum(1 for e in case["expect"] if re.search(e, text)) / len(case["expect"])
    specific = hits >= 0.6
    verify = bool(re.search(r"label|extension|local expert|kvk|mofa|agrologist|verify|confirm|check with|kisan", text))
    dose = bool(re.search(r"\b\d+(\.\d+)?\s?(ml|g|kg)\s?(/|per)\s?(l|litre|liter|acre|hectare|ha)\b", text))
    safe = verify and not (dose and "label" not in text)
    flags = dict(region=region, reasoning=reasoning, simple=simple, specific=specific, safe=safe)
    return {**flags, "score": sum(flags.values()), "flesch": fre, "hits": round(hits, 2)}


def case_inputs(c: dict, language: str = "English") -> dict:
    return {"country": c["country"], "region": c["region"], "month": c["month"], "stage": c["stage"],
            "soil": c["soil"], "water": c["water"], "farm_size": FARM_SIZES[0], "focus": c["focus"],
            "crop": c["crop"], "preferences": c["preferences"], "question": "", "language": language}


def validation_report(df: pd.DataFrame) -> str:
    """Markdown summary that can be pasted straight into the README / submission."""
    lines = ["# Model validation summary", "",
             f"_Generated {dt.datetime.now():%Y-%m-%d %H:%M}_", "",
             "| Test | Region | Version | Temp | Score /5 | Reading ease | Keyword coverage | Region | Reasoning | Simple | Specific | Safe |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    tick = lambda b: "✅" if b else "❌"  # noqa: E731
    for _, r in df.iterrows():
        lines.append(f"| {r['test']} | {r['region']}, {r['country']} | {r['version']} | {r['temperature']} | "
                     f"{r['score']} | {r['flesch']} | {int(r['hits'] * 100)}% | {tick(r['region_ok'])} | "
                     f"{tick(r['reasoning_ok'])} | {tick(r['simple_ok'])} | {tick(r['specific_ok'])} | {tick(r['safe_ok'])} |")
    avg = df.groupby("version")["score"].mean().round(2)
    lines += ["", "## Average checklist score (out of 5)", ""] + [f"- **{v}**: {s}" for v, s in avg.items()]
    lines += ["", "## Changes made after testing", "",
              "1. **Role + context prompt** – added a farmer profile (location, month, soil, water, stage) so advice is region-specific.",
              "2. **Mandatory 'why'** – every recommendation must carry a one-sentence reason (fixes the 'no reasoning' failure of the baseline).",
              "3. **Plain-language rule** – grade-6 reading level, jargon explained in brackets (raises reading ease).",
              "4. **Safety rules** – no invented pesticide brands/doses, 'follow the label', verify with local extension office.",
              "5. **Structured JSON output** (`response_mime_type=application/json`) – reliable cards/steps/warnings instead of a wall of text.",
              "6. **Lower temperature (0.4)** – fewer invented details than the baseline at 1.0.",
              "7. **Live model discovery + fallback** – the app lists models enabled for the API key and switches to another enabled model if needed.",
              "", "## Trusted sources used for comparison", ""]
    lines += [f"- [{n}]({u})" for n, u in TRUSTED_SOURCES]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 11. SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 Gen AI Farming")
    st.caption("AgroNova pilot · FA-2")
    st.text_input("Gemini API key", type="password", key="sidebar_key",
                  help="Get a free key at aistudio.google.com. On Streamlit Cloud put it in Secrets instead.",
                  placeholder="Paste key or use Secrets")
    api_key = get_api_key()
    model_choices = MODEL_CHOICES
    if api_key:
        try:
            available_models = list_gemini_models(api_key)
            model_choices = available_models or MODEL_CHOICES
            if not available_models:
                st.warning("No Gemini models supporting text generation were returned for this key.")
        except Exception:
            st.warning("Gemini's model list couldn't be loaded. Check the key and connection; current model names "
                       "and custom model entry are still available.")
    demo = st.toggle("Demo mode (no API key)", value=not bool(api_key),
                     help="Uses built-in sample responses so you can explore the UI offline.")
    if not api_key and not demo:
        st.error("Add a Gemini API key or switch on Demo mode.")
    st.markdown("##### Model settings")
    model_pick = st.selectbox("Gemini model", model_choices, index=0)
    custom_model = st.text_input("…or custom model name", placeholder="e.g. gemini-4-argon")
    temperature = st.slider("Temperature (creativity)", 0.0, 1.5, 0.4, 0.1,
                            help="Lower = safer, more consistent. Higher = more varied.")
    max_tokens = st.slider("Max response length (tokens)", 512, 4096, 2048, 256)
    language = st.selectbox("Answer language", LANGUAGES)
    st.markdown("##### Prompt version")
    version = st.radio("Prompt", ["V2", "V1"], horizontal=True,
                       format_func=lambda v: "V2 Optimised" if v == "V2" else "V1 Baseline",
                       help="Compare the basic prompt with the optimised one.")
    st.divider()
    st.caption(f"Queries this session: {st.session_state.get('count', 0)}/{MAX_QUERIES_PER_SESSION}")
    st.caption("Built with Streamlit + Google Gemini + Open-Meteo.")

CFG = {"api_key": api_key, "demo": demo or not api_key, "model": custom_model.strip() or model_pick,
       "model_choices": model_choices,
       "temperature": temperature, "max_tokens": max_tokens, "language": language}

# ─────────────────────────────────────────────────────────────────────────────
# 12. PAGE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """<div class="hero"><h1>🌾 Smart Farming Assistant</h1>
    <p>Clear, region-specific farming advice powered by Gemini — with the <b>reason</b> behind every tip.
    Built for farmers in 🇮🇳 India · 🇬🇭 Ghana · 🇨🇦 Canada.</p></div>""",
    unsafe_allow_html=True)
if CFG["demo"]:
    st.info("🧪 **Demo mode** is on – answers come from built-in samples, not Gemini. "
            "Add your API key in the sidebar for live AI advice.")

tab_adv, tab_val, tab_ins, tab_about = st.tabs(["🌱 Advisor", "🧪 Validation Lab", "📊 Insights", "ℹ️ About"])

# ─────────────────────────── TAB 1 · ADVISOR ───────────────────────────
with tab_adv:
    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.subheader("Tell us about your farm")
        country = st.selectbox("Country", list(COUNTRIES), format_func=lambda c: f"{COUNTRIES[c]['flag']} {c}")
        if country == "Other":
            country = st.text_input("Country name", placeholder="e.g. Kenya") or "Other"
            region = st.text_input("Region / state / province", placeholder="e.g. Rift Valley")
        else:
            opts = COUNTRIES[country]["regions"] + ["Other…"]
            region = st.selectbox("Region / state / province", opts)
            if region == "Other…":
                region = st.text_input("Type your region", placeholder="Region or nearest town")
        c1, c2 = st.columns(2)
        month = c1.selectbox("Month", MONTHS, index=dt.date.today().month - 1)
        stage = c2.selectbox("Crop stage", STAGES, index=0)
        c3, c4 = st.columns(2)
        soil = c3.selectbox("Soil type", SOILS)
        water = c4.selectbox("Water access", WATER)
        farm_size = st.selectbox("Farm size", FARM_SIZES)
        focus = st.radio("What do you need help with?", list(FOCUS), horizontal=False)
        crop = st.text_input("Current / planned crop (optional)", placeholder="e.g. Maize, Wheat, Tomato")
        prefs = st.multiselect("Farming preferences", PREFERENCES)
        question = st.text_area("Your own question (optional)", max_chars=300, height=80,
                                placeholder="e.g. My leaves are turning yellow. What can I do?")
        use_weather = st.checkbox("🌦️ Include live 7-day weather for my location", value=True)
        go = st.button("🌾 Get advice", type="primary", width="stretch")

    with right:
        if go:
            now = time.time()
            if not region.strip():
                st.error("Please enter your region so the advice can be specific.")
            elif st.session_state.get("count", 0) >= MAX_QUERIES_PER_SESSION:
                st.error("Session limit reached – please refresh the page to start a new session.")
            elif now - st.session_state.get("last_call", 0) < COOLDOWN_SECONDS:
                st.warning("Please wait a moment before asking again.")
            else:
                st.session_state["last_call"] = now
                inp = {"country": country, "region": region.strip(), "month": month, "stage": stage, "soil": soil,
                       "water": water, "farm_size": farm_size, "focus": focus, "crop": crop.strip(),
                       "preferences": prefs, "question": question.strip(), "language": CFG["language"]}
                with st.status("Growing your advice…", expanded=True) as status:
                    weather = None
                    if use_weather:
                        st.write("🌦️ Checking the weather forecast…")
                        weather = fetch_weather(f"{inp['region']}, {inp['country']}") or fetch_weather(inp["region"])
                    st.write("🤖 Asking Gemini…" if not CFG["demo"] else "🧪 Preparing demo answer…")
                    res = run_advice(inp, CFG, version, weather_text=weather_summary(weather) if weather else "")
                    if res["error"] or not res["data"]:
                        status.update(label="Something went wrong", state="error")
                    else:
                        status.update(label="Advice ready!", state="complete", expanded=False)
                st.session_state["count"] = st.session_state.get("count", 0) + 1
                st.session_state.update(result=res, inputs=inp, weather=weather, req_id=uuid.uuid4().hex[:8],
                                        followups=[])

        res, inp = st.session_state.get("result"), st.session_state.get("inputs")
        if res and res["error"]:
            st.error(f"Couldn't get advice: {res['error'][:300]}")
            st.caption("Check your API key and internet connection, or switch on Demo mode.")
        elif res and res["data"]:
            if res["version"] == "V1":
                st.caption("🔎 Showing the **V1 baseline** prompt (cleaned from plain text) – compare it with V2!")
            render_advice(inp, res)
            if st.session_state.get("weather"):
                with st.expander(f"🌦️ Weather used – {st.session_state['weather']['place']}", expanded=False):
                    st.pyplot(weather_chart(st.session_state["weather"]), width="stretch")
            b1, b2 = st.columns(2)
            b1.download_button("⬇️ Download advice (.md)", to_markdown(inp, res["data"]),
                               file_name="farming_advice.md", mime="text/markdown", width="stretch")
            with b2.popover("🔍 See the prompt & raw output", width="stretch"):
                st.caption(f"Prompt {res['version']} · temp {res['temperature']} · JSON parsed: {res['json_ok']}")
                st.code(res["prompt"], language="text")
                st.code(res["raw"][:3000], language="json" if res["json_ok"] else "text")

            # follow-up question
            st.divider()
            st.subheader("💬 Ask a follow-up")
            fq = st.text_input("Your follow-up question", key="fq", max_chars=250,
                               placeholder="e.g. How much seed do I need per acre?")
            if st.button("Ask", key="ask_fu") and fq.strip():
                if CFG["demo"]:
                    ans = "(Demo mode) Follow-up answers need a Gemini API key. Add one in the sidebar."
                else:
                    ctx = (f"Earlier advice for a farmer in {inp['region']}, {inp['country']} ({inp['month']}): "
                           f"{result_text(res['data'])[:1500]}\n\nFollow-up question: {fq}\n"
                           f"Answer in {CFG['language']}, in at most 5 short bullet points in simple words, with a short "
                           f"'why'. No pesticide brands or exact doses. Advise checking with a local expert if unsure.")
                    try:
                        ans, _ = call_gemini(ctx, CFG["api_key"], CFG["model"], CFG["temperature"],
                                             CFG["max_tokens"], False, CFG["model_choices"])
                    except Exception as e:  # noqa: BLE001
                        ans = f"Sorry, I couldn't answer: {str(e)[:200]}"
                st.session_state.setdefault("followups", []).append((fq, ans))
            for q, a in reversed(st.session_state.get("followups", [])):
                with st.chat_message("user"):
                    st.write(q)
                with st.chat_message("assistant", avatar="🌾"):
                    st.markdown(a)
            feedback_widget(st.session_state["req_id"], inp, res)
        else:
            st.markdown("### 👈 Fill in your farm details and press **Get advice**")
            st.markdown("You'll get **simple bullet recommendations**, a **step-by-step plan**, **warnings** and a "
                        "**'why'** for every suggestion.")
            st.markdown("**Try these quick examples:**")
            st.markdown("- 🇮🇳 *Rajasthan · August · What to grow* (sandy, rain-fed)\n"
                        "- 🇬🇭 *Ashanti · Maize · Pests & diseases*\n"
                        "- 🇨🇦 *Saskatchewan · May · Sowing*")

# ─────────────────────────── TAB 2 · VALIDATION LAB ───────────────────────────
with tab_val:
    st.subheader("🧪 Model validation & prompt optimisation")
    st.markdown("Runs **6 diverse prompts** from India, Ghana and Canada through the **V1 baseline** and the "
                "**V2 optimised** prompt, then scores each answer on the **5-point feedback checklist**.")
    with st.expander("📋 The feedback checklist & how the auto-score works"):
        for _, q in CHECKLIST:
            st.markdown(f"- {q}")
        st.caption("Automatic scores are heuristics (region keywords, 'why' present, Flesch reading ease ≥ 50 with no "
                   "jargon, ≥ 60% expected agronomy keywords, verify/label advice with no invented doses). "
                   "Always follow up with a manual review below and compare to the trusted sources.")
    with st.expander("🔍 Compare the two prompts side by side"):
        pc1, pc2 = st.columns(2)
        sample = case_inputs(TEST_CASES[0], CFG["language"])
        pc1.markdown("**V1 – Baseline**")
        pc1.code(build_prompt(sample, "V1"), language="text")
        pc2.markdown("**V2 – Optimised**")
        pc2.code(build_prompt(sample, "V2"), language="text")

    cA, cB = st.columns([2, 1])
    chosen = cA.multiselect("Test cases", [c["id"] for c in TEST_CASES], default=[c["id"] for c in TEST_CASES],
                            format_func=lambda i: next(f"{c['id']} · {c['region']}, {c['country']} · {c['focus']}"
                                                       for c in TEST_CASES if c["id"] == i))
    both = cB.checkbox("Also run V1 baseline", value=True)
    if st.button("▶️ Run validation", type="primary", disabled=not chosen):
        rows, plan = [], []
        for c in TEST_CASES:
            if c["id"] in chosen:
                if both:
                    plan.append((c, "V1", 1.0))
                plan.append((c, "V2", 0.4))
        prog = st.progress(0.0, text="Running tests…")
        for n, (c, ver, temp) in enumerate(plan, 1):
            res = run_advice(case_inputs(c, CFG["language"]), CFG, ver, temperature=temp)
            sc = score_output(c, res["data"])
            rows.append({"test": c["id"], "country": c["country"], "region": c["region"], "version": ver,
                         "temperature": temp, "score": sc["score"], "flesch": sc["flesch"], "hits": sc["hits"],
                         "region_ok": sc["region"], "reasoning_ok": sc["reasoning"], "simple_ok": sc["simple"],
                         "specific_ok": sc["specific"], "safe_ok": sc["safe"], "latency": res["latency"],
                         "model": res["model"], "error": res["error"][:120],
                         "output": result_text(res["data"]) if res["data"] else ""})
            prog.progress(n / len(plan), text=f"Test {n}/{len(plan)} · {c['id']} {ver}")
        df = pd.DataFrame(rows)
        st.session_state["val_df"] = df
        for r in rows:
            append_csv(VALIDATION_LOG, {"timestamp": dt.datetime.now().isoformat(timespec="seconds"),
                                        **{k: v for k, v in r.items() if k != "output"}})
        prog.empty()

    vdf = st.session_state.get("val_df")
    if vdf is not None and not vdf.empty:
        avg = vdf.groupby("version")["score"].mean()
        m = st.columns(3)
        m[0].metric("Avg score – V2 optimised", f"{avg.get('V2', 0):.1f} / 5")
        if "V1" in avg:
            m[1].metric("Avg score – V1 baseline", f"{avg['V1']:.1f} / 5")
            m[2].metric("Improvement", f"+{avg.get('V2', 0) - avg['V1']:.1f}", delta_color="normal")
        pivot = vdf.pivot_table(index="test", columns="version", values="score")
        fig, ax = plt.subplots(figsize=(7, 3), facecolor="white")
        pivot.plot(kind="bar", ax=ax, color={"V1": "#bdbdbd", "V2": "#2e7d32"}, rot=0, width=0.7)
        ax.set_ylim(0, 5.5)
        ax.set_ylabel("Checklist score (/5)")
        ax.set_xlabel("")
        ax.legend(frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.15))
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        fig.tight_layout()
        st.pyplot(fig, width="stretch")
        show = vdf.drop(columns=["output", "error", "model"]).copy()
        for col in ("region_ok", "reasoning_ok", "simple_ok", "specific_ok", "safe_ok"):
            show[col] = show[col].map({True: "✅", False: "❌"})
        st.dataframe(show, width="stretch", hide_index=True)
        if vdf["error"].astype(bool).any():
            st.warning("Some calls failed: " + "; ".join(sorted(set(vdf["error"][vdf["error"].astype(bool)])))[:300])
        d1, d2 = st.columns(2)
        d1.download_button("⬇️ Validation report (.md)", validation_report(vdf), "validation_report.md",
                           "text/markdown", width="stretch")
        d2.download_button("⬇️ Results (.csv)", vdf.drop(columns=["output"]).to_csv(index=False),
                           "validation_results.csv", "text/csv", width="stretch")
        with st.expander("📝 Read the formatted outputs"):
            for _, r in vdf.sort_values(["test", "version"]).iterrows():
                st.markdown(f"**{r['test']} · {r['region']} · {r['version']}** (score {r['score']}/5)")
                st.write(r["output"] or "_no output_")

    st.divider()
    st.subheader("🌡️ Parameter experiment")
    st.caption("Same prompt, different temperatures – see how creativity changes the answer's quality score.")
    pe1, pe2 = st.columns([2, 1])
    tc = pe1.selectbox("Test case", [c["id"] for c in TEST_CASES], key="pe_case")
    temps = pe2.multiselect("Temperatures", [0.0, 0.2, 0.4, 0.7, 1.0, 1.3], default=[0.2, 0.7, 1.0])
    if st.button("Run experiment") and temps:
        case = next(c for c in TEST_CASES if c["id"] == tc)
        out = []
        for t in temps:
            r = run_advice(case_inputs(case, CFG["language"]), CFG, "V2", temperature=t)
            sc = score_output(case, r["data"])
            out.append({"temperature": t, "score /5": sc["score"], "reading ease": sc["flesch"],
                        "keyword coverage": f"{int(sc['hits'] * 100)}%", "latency (s)": r["latency"],
                        "tokens-ish (words)": len(result_text(r["data"]).split()) if r["data"] else 0})
        st.dataframe(pd.DataFrame(out), hide_index=True, width="stretch")

    st.divider()
    st.subheader("✍️ Manual review (human checklist)")
    st.caption("Tick each question after comparing an output with a trusted source (FAO, government portals).")
    mr1, mr2 = st.columns(2)
    mcase = mr1.selectbox("Test case", [c["id"] for c in TEST_CASES], key="man_case")
    mver = mr2.selectbox("Version", ["V2", "V1"], key="man_ver")
    ticks = {k: st.checkbox(q, key=f"man_{k}") for k, q in CHECKLIST}
    src = next(c for c in TEST_CASES if c["id"] == mcase)["source"]
    st.markdown(f"Compare with: [{src[0]}]({src[1]})")
    note = st.text_area("Reviewer notes / issues found / prompt changes made", key="man_note", height=80)
    if st.button("Save review"):
        append_csv(MANUAL_LOG, {"timestamp": dt.datetime.now().isoformat(timespec="seconds"), "test": mcase,
                                "version": mver, **ticks, "score": sum(ticks.values()), "notes": note})
        st.success(f"Saved – manual score {sum(ticks.values())}/5.")
    mdf = read_csv(MANUAL_LOG)
    if not mdf.empty:
        st.dataframe(mdf.tail(10), hide_index=True, width="stretch")

    st.markdown("**Trusted sources:** " + " · ".join(f"[{n}]({u})" for n, u in TRUSTED_SOURCES))

# ─────────────────────────── TAB 3 · INSIGHTS ───────────────────────────
with tab_ins:
    st.subheader("📊 Usage monitoring & feedback")
    st.caption("Live analytics from this deployment (stored in CSV files; on Streamlit Cloud they reset when the app "
               "restarts – export regularly).")
    u, f = read_csv(USAGE_LOG), read_csv(FEEDBACK_LOG)
    if u.empty:
        st.info("No usage yet – ask the Advisor a question and come back.")
    else:
        u = u[u["prompt_version"].notna()]
        k = st.columns(4)
        k[0].metric("Total queries", len(u))
        k[1].metric("Success rate", f"{u['success'].mean() * 100:.0f}%")
        k[2].metric("Avg response time", f"{u['latency_s'].mean():.1f}s")
        k[3].metric("Avg rating", f"{f['rating'].mean():.1f} ⭐ ({len(f)})" if not f.empty else "—")
        g1, g2 = st.columns(2)
        g1.markdown("**Queries by country**")
        g1.bar_chart(u["country"].value_counts())
        g2.markdown("**Queries by topic**")
        g2.bar_chart(u["focus"].value_counts())
        g3, g4 = st.columns(2)
        g3.markdown("**Queries per day**")
        g3.line_chart(pd.to_datetime(u["timestamp"]).dt.date.value_counts().sort_index())
        g4.markdown("**Prompt version used**")
        g4.bar_chart(u["prompt_version"].value_counts())
        if not f.empty:
            st.markdown("**Ratings distribution**")
            st.bar_chart(f["rating"].value_counts().sort_index())
            st.markdown("**Latest comments**")
            st.dataframe(f[f["comment"].notna()][["timestamp", "country", "rating", "comment"]].tail(10),
                         hide_index=True, width="stretch")
        st.download_button("⬇️ Export usage log (.csv)", u.to_csv(index=False), "usage_log.csv", "text/csv")

# ─────────────────────────── TAB 4 · ABOUT ───────────────────────────
with tab_about:
    st.subheader("ℹ️ About this app")
    st.markdown(
        """
**Gen AI Smart Farming Assistant** is an AgroNova pilot that helps farmers in India, Ghana and Canada get
practical, region-specific advice from Google Gemini — in plain language, with the *reason* behind every tip.

**How it works**
1. You describe your farm (location, month, crop stage, soil, water, preferences).
2. An optimised prompt (V2) with a farmer profile, 8 safety/clarity rules and a JSON schema is sent to Gemini.
3. The reply is parsed and cleaned into **cards, steps and warnings** (Step 4: formatting & reasoning).
4. Live weather from Open-Meteo is added to ground the advice in current conditions.
5. The **Validation Lab** tests the model on 6 regional prompts against a 5-point checklist (Step 5).
6. The **Insights** tab monitors usage and feedback (Step 6).

**Responsible AI**
- AI can hallucinate. Every answer shows a confidence level and a verify-with-an-expert reminder.
- The prompt forbids invented pesticide brands/doses.
- No personal data is stored – only country, region, topic, timing and optional feedback text.
- Session query limits and cool-downs protect the shared API quota.

**Limitations:** advice is general guidance, not a replacement for local agronomists; automatic scores are
heuristics; CSV logs on free Streamlit Cloud are not permanent.
""")
    st.markdown("**Trusted sources:** " + " · ".join(f"[{n}]({u})" for n, u in TRUSTED_SOURCES))
