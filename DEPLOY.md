# Deploy in 10 minutes

1. **Gemini key** – https://aistudio.google.com/apikey → Create API key (free).
2. **GitHub** – new *public* repo (e.g. `GenAI-Smart-Farming`). Upload everything in this folder
   (`app.py`, `requirements.txt`, `README.md`, `docs/`, `.streamlit/config.toml`, `.gitignore`).
   Do NOT upload a real `secrets.toml`.
3. **Streamlit Cloud** – https://share.streamlit.io → sign in with GitHub → *Create app* →
   pick the repo, branch `main`, main file `app.py` → *Advanced settings → Secrets*, paste:
   `GEMINI_API_KEY = "your-key"` → **Deploy**.
4. Open the public URL, turn Demo mode off if it's on, ask a question.
5. Open **Validation Lab → Run validation**, download the report, paste it in the README.
6. Test on your phone + another browser; fill the device table and add real screenshots to `docs/`.
7. Put the Streamlit URL at the top of the README and submit it.
