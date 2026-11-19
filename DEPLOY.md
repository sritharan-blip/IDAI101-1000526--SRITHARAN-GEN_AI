# Deploy in 10 minutes

1. **Gemini key** – https://aistudio.google.com/apikey → Create API key (free). The app uses Google's current `google-genai` SDK and loads the text-generation models available to that key.
2. **GitHub** – use this repository as the deployment source. Keep your real `.streamlit/secrets.toml` out of Git.
3. **Streamlit Cloud** – https://share.streamlit.io → sign in with GitHub → *Create app* →
   pick the repo, branch `main`, main file `app.py` → *Advanced settings → Secrets*, paste:
   `GEMINI_API_KEY = "your-key"` → **Deploy**.
4. Open the public URL. Chat and image analysis need the configured Gemini key; the retained Advisor page also offers Demo mode.
5. Open **Advisor & insights → Validation Lab → Run validation**, download the report, paste it in the README.
6. Open **Gemini connection** and check for key or quota messages. Verify chat and a crop scan with a sample image.

## Docker

Alternatively, build and run the multi-stage container with Docker:

```bash
docker build -t agronova .
docker run --rm -p 8501:8501 -e GEMINI_API_KEY agronova
```
