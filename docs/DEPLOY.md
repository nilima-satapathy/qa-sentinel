# Deploy QA Sentinel

## Important: Vercel vs Streamlit

**QA Sentinel is a Streamlit app** (long-running Python server + WebSockets).

| Host | Full interactive app? | Notes |
|------|----------------------|--------|
| **Vercel** | No (not for Streamlit) | Serverless only — use for static project hub (`site/`) |
| **Streamlit Community Cloud** | **Yes (recommended)** | Free, built for Streamlit |
| **Render / Railway / Docker** | Yes | Use `Dockerfile` or `render.yaml` |

---

## Public code URL (already live)

https://github.com/nilima-satapathy/qa-sentinel

---

## A) Deploy project hub on Vercel (static page)

From a terminal (one-time login):

```powershell
cd C:\Users\admin\Code\qa-sentinel\site
npx vercel login
npx vercel --prod
```

This publishes `site/index.html` as a public Vercel URL (marketing / portfolio hub).

---

## B) Deploy full interactive app — Streamlit Cloud (recommended)

1. Open:  
   https://share.streamlit.io/deploy?repository=nilima-satapathy%2Fqa-sentinel&branch=master&mainModule=app.py  
2. Sign in with GitHub.  
3. App: `nilima-satapathy/qa-sentinel` · Branch: `master` · Main file: `app.py`  
4. **Advanced settings → Secrets** (for live Groq):

```toml
OPENAI_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_API_KEY = "gsk_your_key"
OPENAI_MODEL = "llama-3.1-8b-instant"
```

5. Deploy.

You will get a URL like:

`https://qa-sentinel-xxxx.streamlit.app`

The app auto-clones Project 4 harness into `vendor/` on first run if missing.

---

## C) Deploy full app on Render

1. https://dashboard.render.com → New → Blueprint  
2. Connect `nilima-satapathy/qa-sentinel`  
3. Use `render.yaml`  
4. Set secret `OPENAI_API_KEY`

---

## Local

```powershell
cd C:\Users\admin\Code\qa-sentinel
.\.venv\Scripts\activate
python -m streamlit run app.py
```

http://127.0.0.1:8501
