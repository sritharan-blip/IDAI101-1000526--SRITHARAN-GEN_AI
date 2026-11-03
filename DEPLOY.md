# Deploy in 10 minutes

1. **Gemini key** – https://aistudio.google.com/apikey → Create API key (free). The app uses Google's current `google-genai` SDK and loads the text-generation models available to that key.
2. **GitHub** – new *public* repo (e.g. `GenAI-Smart-Farming`). Upload the app source and assets:
   `app.py`, `requirements.txt`, `README.md`, `DEPLOY.md`, `components/`, `config/`, `services/`,
   `utils/`, `styles/`, `assets/`, `knowledge/`, and `.streamlit/config.toml`.
   Do NOT upload a real `secrets.toml`.
3. **Streamlit Cloud** – https://share.streamlit.io → sign in with GitHub → *Create app* →
   pick the repo, branch `main`, main file `app.py` → *Advanced settings → Secrets*, paste:
   `GEMINI_API_KEY = "your-key"` → **Deploy**.
4. Open the public URL. Chat and image analysis need the configured Gemini key; the retained Advisor page also offers Demo mode.
5. Open **Advisor & insights → Validation Lab → Run validation**, download the report, paste it in the README.
6. Test on your phone + another browser; fill the device table and add real screenshots to `docs/`.
7. Put the Streamlit URL at the top of the README and submit it.

## Docker

Alternatively, build and run the multi-stage container with Docker:

```bash
docker build -t agronova .
docker run --rm -p 8501:8501 -e GEMINI_API_KEY="your-key" agronova
```
