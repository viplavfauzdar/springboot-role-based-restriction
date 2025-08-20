# agent/ui.py
import os
import json
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Local ELK Log Analyst", layout="wide")

# --- Config ---
DEFAULT_BACKEND = os.getenv("AGENT_URL", "http://127.0.0.1:5055")

with st.sidebar:
    st.markdown("## ⚙️ Settings")
    backend_url = st.text_input("Agent URL", value=DEFAULT_BACKEND, help="FastAPI backend from app.py")
    show_models = st.checkbox("Show Ollama models", value=False)
    st.caption("Tip: start the backend with:\n\n`uvicorn agent.app:app --reload --port 5055`")

st.title("🧠 Local AI Log Analyst (Ollama + Elasticsearch)")
st.markdown(
    "Ask questions about your logs in natural language. The agent will generate **ES|SQL** or **DSL**."
)

colq1, colq2 = st.columns([3, 1])
with colq1:
    question = st.text_input("Your question", value="Top 5 log levels and counts for today")
with colq2:
    prefer = st.selectbox("Preferred mode", ["auto", "esql", "dsl"])

time_range = st.text_input("Time range hint (optional)", value="", placeholder="e.g., last 24 hours, past 15m, today")
size = st.number_input("Max documents (DSL mode)", min_value=1, max_value=500, value=25, step=1)

run = st.button("🔎 Ask")

if show_models:
    try:
        r = requests.get(f"{backend_url.rstrip('/')}/models", timeout=10)
        r.raise_for_status()
        models = r.json().get("models", [])
        st.sidebar.markdown("### 🧱 Ollama Models")
        if isinstance(models, list):
            for m in models:
                st.sidebar.write("- " + (m.get("model") or json.dumps(m)))
        else:
            st.sidebar.code(json.dumps(models, indent=2))
    except Exception as e:
        st.sidebar.error(f"Failed to fetch models: {e}")

# Health/status
with st.expander("🔌 Connection & Health", expanded=False):
    try:
        h = requests.get(f"{backend_url.rstrip('/')}/health", timeout=5).json()
        st.json(h)
    except Exception as e:
        st.warning(f"Could not reach backend: {e}")

# Main action
if run:
    payload = {
        "question": question,
        "size": int(size),
    }
    if prefer != "auto":
        payload["prefer"] = prefer
    if time_range.strip():
        payload["time_range"] = time_range.strip()

    try:
        with st.spinner("Thinking with your local model…"):
            resp = requests.post(f"{backend_url.rstrip('/')}/ask", json=payload, timeout=600)
        if resp.status_code >= 400:
            # Show detailed error body from backend (includes ES response / query)
            try:
                detail = resp.json()
            except Exception:
                detail = {"raw": resp.text}
            st.error("Backend error")
            st.code(json.dumps(detail, indent=2))
        else:
            data = resp.json()

            top = st.container()
            cols = top.columns([1, 2])
            with cols[0]:
                st.markdown(f"**Mode:** `{data['mode']}`")
                st.markdown(f"**Hits:** `{data['hits']}`")
            with cols[1]:
                st.markdown("**Answer**")
                st.write(data.get("answer") or "")

            st.markdown("---")
            st.markdown("### 🔎 Generated Query")
            if data["mode"] == "dsl":
                st.code(json.dumps(data["query"], indent=2), language="json")
            else:
                st.code(str(data["query"]), language="sql")

            st.markdown("### 📦 Sample Results")
            sample = data.get("sample")
            # If DSL → sample is hits array; if ESQL → it’s a table-like {columns, values}
            if isinstance(sample, list):
                # DSL hits
                docs = [h.get("_source", h) for h in sample]
                if docs:
                    df = pd.DataFrame(docs)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No sample docs.")
            elif isinstance(sample, dict) and "columns" in sample and "values" in sample:
                # ESQL table
                cols = [c.get("name") for c in sample["columns"]]
                df = pd.DataFrame(sample["values"], columns=cols)
                st.dataframe(df, use_container_width=True)
            else:
                st.code(json.dumps(sample, indent=2)[:5000])

            with st.expander("🪵 Raw LLM object (debug)"):
                st.code(json.dumps(data.get("llm_raw", {}), indent=2)[:8000])

    except requests.RequestException as e:
        st.error(f"Request failed: {e}")