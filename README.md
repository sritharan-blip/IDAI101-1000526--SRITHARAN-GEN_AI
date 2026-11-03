# 🌾 Gen AI – Smart Farming Assistant

> AgroNova pilot · Generative AI · Formative Assessment 2 (Web App Building, API Integration, Deployment)

A Streamlit web app that turns **Google Gemini** responses into clear, region-specific farming advice for farmers in
🇮🇳 India, 🇬🇭 Ghana and 🇨🇦 Canada – with a **"why"** behind every suggestion.

**🔗 Live app:** `PASTE-YOUR-STREAMLIT-URL-HERE`  ·  **📦 Repo:** `PASTE-YOUR-GITHUB-URL-HERE`

![Home](docs/01_home.png)

## Features

| | Feature | Brief step |
|---|---|---|
| 🌱 | **Advisor** – location, month, crop stage, soil, water, farm size, preferences, focus (crops / pests / irrigation / soil / harvest / free question) → Gemini → cards, action plan, warnings | Step 6 |
| 💡 | **Formatted output + reasoning** – JSON schema forces bullets, numbered steps and a one-sentence *why*; messy text is auto-cleaned | Step 4 |
| 🧪 | **Validation Lab** – 6 regional test prompts, V1 baseline vs V2 optimised prompt, auto-scored on the 5-point checklist, temperature experiment, manual review form, exportable report | Step 5 |
| 📊 | **Insights** – usage monitoring (queries, latency, success rate) and feedback analytics (star ratings, comments) | Step 6 |
| 🌦️ | **Live weather** (Open-Meteo, via `requests`) fed into the prompt + `matplotlib` forecast chart | extra |
| 🌍 | **Multilingual answers** (Hindi, French, Twi, Hausa, Tamil, Punjabi, Marathi) | extra |
| 💬 | **Follow-up questions**, **download advice**, **confidence level**, **safety warnings** | extra |
| 🛡️ | Session rate limit & cool-down, API-key via Secrets, automatic **model fallback** (Gemini 1.5 is retired), demo mode without a key | extra |

![Advice](docs/02_advice.png)

## Step 4 – Output formatting & reasoning
Example (input: *"What to grow in Rajasthan in August?"*):

- **Pearl Millet (Bajra)** – Drought-resistant, thrives in arid soil.
- **Cluster Bean (Guar)** – Ideal for sandy soil, tolerates low water.
- **Green Gram (Moong)** – Quick-growing legume, suits short monsoon cycles.

## Step 5 – Model validation & optimisation
**Test prompts** (see `TEST_CASES` in `app.py`):

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
| Model retired | Automatic fallback across Gemini models |

> 📝 **Add your real results here:** open the *Validation Lab* with your API key, press **Run validation**, download
> the **validation report (.md)** and paste it below. (Screenshots in `docs/` were captured in *demo mode*, where
> responses are built-in samples, so don't quote those scores as Gemini results.)

![Validation](docs/03_validation.png)

## Step 6 – Deployment
- `app.py` – all code and UI · `requirements.txt` – streamlit, google-generativeai, google-genai, requests, pandas, matplotlib
- Hosted on Streamlit Community Cloud from this GitHub repo; API key stored in **Secrets** (never in code).
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
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # add your Gemini key
streamlit run app.py
```
No key? Toggle **Demo mode** in the sidebar.

## Responsible AI
AI can hallucinate; every answer shows a confidence level and a "verify with your local expert" reminder. No personal
data is stored. Automatic scores are heuristics and don't replace expert review.
