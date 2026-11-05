# 🌱 AgroNova – Farm Intelligence

> AgroNova pilot · Generative AI · Formative Assessment 2 (Web App Building, API Integration, Deployment)

A modular Streamlit farming assistant powered by Google's current `google-genai` SDK. Its command center combines
farm-profile-aware chat, crop-image triage, a live weather forecast, a map, and an explicitly illustrative yield
scenario. The original Advisor, Validation Lab, and Insights workflows remain available as a separate page.

**🔗 Live app:** `PASTE-YOUR-STREAMLIT-URL-HERE`  ·  **📦 Repo:** `PASTE-YOUR-GITHUB-URL-HERE`

![Home](docs/01_home.png)

## Features

| | Feature | Brief step |
|---|---|---|
| 🌱 | **Advisor** – location, month, crop stage, soil, water, farm size, preferences, focus (crops / pests / irrigation / soil / harvest / free question) → Gemini → cards, action plan, warnings | Existing workflow |
| 💡 | **Formatted output + reasoning** – JSON schema forces bullets, numbered steps and a one-sentence *why*; messy text is auto-cleaned | Step 4 |
| 🧪 | **Validation Lab** – 6 regional test prompts, V1 baseline vs V2 optimised prompt, auto-scored on the 5-point checklist, temperature experiment, manual review form, exportable report | Step 5 |
| 📊 | **Insights** – usage monitoring (queries, latency, success rate) and feedback analytics (star ratings, comments) | Step 6 |
| 🌦️ | **Live weather and map** – cached Open-Meteo conditions, seven-day forecast, coordinates, and optional modeled surface-soil-moisture data | New |
| 💬 | **Context-aware agronomist chat** – Gemini streaming, farm/weather context, short conversation memory, and local safety-note retrieval | New |
| 📷 | **Crop health scanner** – multimodal Gemini JSON assessment with confidence, cautious treatment notes, and scan history | New |
| 📈 | **Yield & finance simulator** – interactive rainfall/fertilizer/price scenarios with a dual-axis Plotly chart | New |
| 📄 | **Farm action plan PDF** – exports the saved profile, weather, scans, and scenario from the current session | New |
| 🌍 | **Multilingual AI answers and crop scans** – all 22 Indian scheduled languages plus English, Arabic, Chinese, French, German, Japanese, Portuguese, Russian, Spanish, Swahili, Twi, and Hausa | extra |
| 💬 | **Follow-up questions**, **download advice**, **confidence level**, **safety warnings** | extra |
| 🛡️ | Session rate limit & cool-down, API key via Secrets, live Gemini model list for the entered key, fallback, and demo mode in the preserved workflow | Existing + new |

The sidebar groups appearance and language, farm details, Gemini settings, and the downloadable action plan. Its light/dark switch updates the full app palette, including the shared Advisor page, with reduced-motion support.

### Gemini model options

- `gemini-4-argon` – newest flagship reasoning model and the default.
- `gemini-3.8-flash` and `gemini-3.6-flash` – faster general-purpose choices.
- `gemini-3.5-flash-lite` and `gemini-3.1-flash-lite` – cost-efficient choices.
- With a Gemini API key, the picker also lists models available to that key. A custom model ID can be entered when needed.

## Architecture

```text
app.py                     Streamlit router and shared layout
styles/global.css          Eco-futurist glass UI and theme variables
config/settings.py         App configuration, secrets, model defaults
config/prompts.py          Context-aware LangChain prompt templates
components/                Command center, chat, vision, simulator, legacy page, UI components
services/                  Gemini text/vision, local-note retrieval, async weather, analytics
utils/                     Session state, cached clients/styles, PDF exports
knowledge/                 Reviewable local safety notes used by retrieval
assets/                    Bundled farm animation
Dockerfile                 Multi-stage, non-root container image
```

![Advice](docs/02_advice.png)

## Step 4 – Output formatting & reasoning
Example (input: *"What to grow in Rajasthan in August?"*):

- **Pearl Millet (Bajra)** – Drought-resistant, thrives in arid soil.
- **Cluster Bean (Guar)** – Ideal for sandy soil, tolerates low water.
- **Green Gram (Moong)** – Quick-growing legume, suits short monsoon cycles.

## Step 5 – Model validation & optimisation
**Test prompts** (see `TEST_CASES` in `components/legacy_workflows.py`):

| ID | Region | Topic | Trusted source for comparison |
|---|---|---|---|
| T1 | Rajasthan, India · Aug | What to grow (sandy, rain-fed) | Dept. of Agriculture & Farmers Welfare |
| T2 | Punjab, India · Nov | Irrigation for wheat | ICAR |
| T3 | Ashanti, Ghana · Jun | Fall armyworm in maize | FAO Fall Armyworm portal |
| T4 | Northern Ghana · Apr | What to grow | Ghana MoFA |
| T5 | Saskatchewan, Canada · May | What to grow / sowing | Agriculture and Agri-Food Canada |
| T6 | Ontario, Canada · Oct | Soybean harvest & storage | Agriculture and Agri-Food Canada |

**Feedback checklist** (auto-scored + manual form in the app)
1. Is the advice specific to the input region?
2. Does the output provide valid and logical reasoning?
3. Is the language simple enough for a layperson?
4. Are outputs too generic or technical?
5. Does the model avoid misleading or unsafe advice?

**Prompt / parameter changes made**

| Problem seen with V1 baseline | Fix in V2 |
|---|---|
| Long, generic wall of text | Farmer profile + role + JSON schema → cards and steps |
| No reasoning | Mandatory one-sentence *why* per recommendation |
| Technical jargon | Grade-6 language rule, jargon explained in brackets |
| Risk of invented pesticide brands/doses | Explicit safety rules, "follow the label", verify with extension office |
| Too random (temperature 1.0) | Temperature 0.4, JSON mime type |
| Model retired | Live model discovery for the API key, plus fallback across available Gemini models |

> 📝 **Add your real results here:** open the *Validation Lab* with your API key, press **Run validation**, download
> the **validation report (.md)** and paste it below. (Screenshots in `docs/` were captured in *demo mode*, where
> responses are built-in samples, so don't quote those scores as Gemini results.)

![Validation](docs/03_validation.png)

## Step 6 – Deployment
- `app.py` – app router · `requirements.txt` – Streamlit, Gemini, LangChain, Plotly, Folium, PDF and analytics dependencies
- Hosted on Streamlit Community Cloud from this GitHub repo; API key stored in **Secrets** (never in code).
- The app uses Google's `google-genai` SDK, defaults to Gemini 4 Argon, and offers newer Flash and cost-efficient Flash-Lite options. With an API key, the picker lists models enabled for that key. Add the key as `GEMINI_API_KEY`.
- **Cross-device testing:** record results below.

| Device / browser | Result |
|---|---|
| Laptop – Chrome | ✅ / ❌ |
| Android phone – Chrome | |
| iPhone – Safari | |
| Tablet | |

![Mobile](docs/05_mobile.png)  ![Insights](docs/04_insights.png)

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

Set `GEMINI_API_KEY` in the environment or configure Streamlit Secrets (`.streamlit/secrets.toml` locally; never commit it). Choose an AI response language in the sidebar; the setting applies to chat, crop scans, and the Advisor. The app interface itself remains in English. The original Advisor page supports demo mode without a key; live chat and image analysis require one.

### Docker

```bash
docker build -t agronova .
docker run --rm -p 8501:8501 -e GEMINI_API_KEY="your-key" agronova
```

### Data and limitations

- Farm coordinates and profile values stay in the current Streamlit session unless you configure persistent hosting. Weather requests go to Open-Meteo; map tiles are loaded from OpenStreetMap for the displayed area.
- Gemini receives chat prompts, the saved farm context, and uploaded photos when those features are used.
- Surface soil moisture is a model estimate when returned by the weather service, not a sensor measurement. NDVI/satellite data is not connected.
- Disease scans are preliminary image assessments, not diagnoses. Yield and price charts are illustrative scenarios, not validated forecasts or live market data.
- The scanner and chat need a Gemini API key. Never put a real key in source control or an image.

## Responsible AI
AI can hallucinate. Confirm disease, pesticide, and other high-stakes recommendations with a qualified local expert.
The existing Validation Lab's scores are heuristics and do not replace expert review.
