"""
Lightweight local AI log analyst for Elasticsearch + Ollama.

Quick start (first time on your laptop):
  1) python3 -m venv .venv && source .venv/bin/activate
  2) pip install fastapi "uvicorn[standard]" requests python-dotenv
  3) export ES_URL=http://localhost:9200
     export ES_INDEX=logstash-*
     # If your ES needs auth:
     # export ES_USERNAME=elastic
     # export ES_PASSWORD=changeme
     export OLLAMA_URL=http://localhost:11434
     export OLLAMA_MODEL=gpt-oss-20b   # or any local model you have pulled
  4) uvicorn agent.app:app --reload --port 5055

Then query:
  curl -s 'http://localhost:5055/ask' \
    -H 'Content-Type: application/json' \
    -d '{"question":"Top 5 log levels and counts for today"}' | jq .
"""

from __future__ import annotations

import json
import os
import textwrap
import re
from typing import Any, Dict, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

APP_NAME = "Local AI Log Analyst"
DEFAULT_ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "springboot-logs-*")
ES_USERNAME = os.getenv("ES_USERNAME")
ES_PASSWORD = os.getenv("ES_PASSWORD")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")

TIMEOUT = float(os.getenv("AGENT_HTTP_TIMEOUT", "60"))

app = FastAPI(title=APP_NAME)

# Allow browser calls from localhost tools (Kibana, your app, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    time_range: Optional[str] = None  # e.g., "last 24 hours"
    size: int = 25  # max docs to summarize when DSL path is used
    prefer: Optional[str] = None  # "esql" or "dsl" if you want to force a mode


class AskResponse(BaseModel):
    mode: str
    query: Dict[str, Any] | str
    hits: int
    sample: Any
    answer: str
    llm_raw: Dict[str, Any]


def _es_auth() -> Optional[Tuple[str, str]]:
    if ES_USERNAME and ES_PASSWORD:
        return (ES_USERNAME, ES_PASSWORD)
    return None


def _ollama_generate_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    Call Ollama /api/generate with JSON/structured-output mode and return a JSON object.
    Be tolerant of models that still emit narration around the JSON by:
      1) trying to parse wrapper['response'] directly;
      2) extracting a fenced ```json block or the first balanced JSON object;
      3) as a last resort, if the text looks like an ESQL pipeline, wrap it in
         {"mode":"esql","query":"..."} so the rest of the code can proceed.
    """
    url = f"{OLLAMA_URL.rstrip('/')}/api/generate"

    # Preferred: ask for strict JSON (or schema) and no streaming
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system_prompt}\n\nUSER:\n{user_prompt}",
        "format": "json",  # forces JSON mode in Ollama (response becomes a JSON *string*)
        "stream": False,
        "options": {"temperature": 0.1},
    }

    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

    wrapper = r.json()
    # Expose the raw Ollama wrapper in logs for debugging, but remove "context" key if present
    try:
        clean_wrapper = dict(wrapper)
        clean_wrapper.pop("context", None)
        print("[Ollama raw]:", json.dumps(clean_wrapper, indent=2)[:4000])
    except Exception:
        pass

    resp_text = (wrapper.get("response") or "").strip()
    if not resp_text:
        raise HTTPException(status_code=500, detail="Model returned an empty 'response'.")

    # 1) Try straight JSON first
    try:
        return json.loads(resp_text)
    except json.JSONDecodeError:
        pass

    # Helper: extract first fenced ```json block
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", resp_text, re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            # keep going
            pass

    # Helper: extract first balanced JSON object from arbitrary text
    def _extract_first_json_object(s: str) -> Optional[str]:
        start = s.find('{')
        if start == -1:
            return None
        depth = 0
        in_str = False
        esc = False
        for i, ch in enumerate(s[start:], start):
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return s[start:i + 1]
        return None

    block = _extract_first_json_object(resp_text)
    if block:
        try:
            return json.loads(block)
        except Exception:
            pass

    # 3) Heuristic: if the model clearly produced an ESQL pipeline, salvage it
    looks_like_esql = bool(re.search(r"\bFROM\b\s+\S+|\bfrom\b\s+\S+", resp_text))
    if looks_like_esql:
        # Try to pull the pipeline portion (after possible colon/quote noise)
        pipeline = resp_text
        # common pattern: ": \"SELECT ...\""
        m = re.search(r":\s*\"([^\"]+)\"", resp_text)
        if m:
            pipeline = m.group(1)
        return {
            "mode": "esql",
            "query": pipeline.strip(),
            "explanation": "Heuristically recovered ESQL from a non-JSON response"
        }

    # Give up with a clear error so the caller still returns 500 with context
    raise HTTPException(
        status_code=500,
        detail=("Model did not return valid JSON in 'response' and no parsable JSON/ESQL could be recovered. "
                "Review the server logs for the raw output and adjust the prompt/model.")
    )


def build_system_prompt() -> str:
    # We coach the model to either produce ESQL or a safe DSL query.
    return textwrap.dedent(
        f"""
        You are an expert Elastic analyst assisting with ad-hoc log analytics.
        You can output *either* an Elasticsearch ESQL pipeline string or an Elasticsearch DSL JSON.
        The index pattern to search is: {ES_INDEX}
        If you use ESQL, **include the index in the first stage** like:
          FROM {ES_INDEX}
        If you use DSL, return a safe request body JSON for POST /{ES_INDEX}/_search.
        Always return a *single JSON object* with the following schema:

        {{
          "mode": "esql" | "dsl",
          "query": "ESQL pipeline string if mode=esql" | {{ &lt;DSL JSON if mode=dsl&gt; }},
          "explanation": "1-2 sentences explaining the approach"
        }}

        Constraints:
        - Prefer ESQL for aggregations, grouping, and time filtering.
        - If the user asks for raw examples, you may choose DSL with a match/match_phrase/range.
        - Respect time hints like "today", "last 24 hours", "past 15m".
        - Limit result volume: if DSL, set "size" to a small number; if ESQL, use LIMIT where reasonable.
        - Use fields that are typical in Logstash-formatted logs: @timestamp, level, message, logger_name, thread, host.name, service.name, trace.id, span.id, http.* etc.
        - Do not use kibana-specific features.
        - Never include destructive operations.
        """
    ).strip()


def build_user_prompt(question: str, time_range: Optional[str], size: int, prefer: Optional[str]) -> str:
    extras = []
    if time_range:
        extras.append(f"time_range hint: {time_range}")
    if prefer:
        extras.append(f"prefer mode: {prefer}")
    hint = f" ({'; '.join(extras)})" if extras else ""
    return f"User question{hint}: {question}"


def run_es_dsl(dsl: Dict[str, Any], size_cap: int) -> Tuple[int, Any]:
    """Run a DSL _search and return (hits_total, sample_docs)."""
    # Cap size if user/LLM forgot to
    if "size" not in dsl or int(dsl.get("size", 0)) > size_cap:
        dsl["size"] = size_cap
    url = f"{DEFAULT_ES_URL.rstrip('/')}/{ES_INDEX}/_search"
    try:
        resp = requests.post(url, auth=_es_auth(), json=dsl, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Elasticsearch DSL error: {e}")
    data = resp.json()
    total = data.get("hits", {}).get("total", {}).get("value", len(data.get("hits", {}).get("hits", [])))
    return total, data.get("hits", {}).get("hits", [])


def _normalize_esql(esql: str) -> str:
    """
    Ensure the ESQL starts with a FROM stage that uses our ES_INDEX.
    If the string already contains a FROM at the beginning, leave it as-is.
    Otherwise, prepend 'FROM {ES_INDEX} | '.
    """
    s = (esql or "").strip()
    try:
        print(f"[ESQL raw from model]: {s}")
    except Exception:
        pass
    # If it already starts with FROM (case-insensitive), don't touch.
    if re.match(r"^\s*from\s+\S+", s, re.IGNORECASE):
        return s
    normalized = f"FROM {ES_INDEX} | {s}"
    try:
        print(f"[ESQL normalized]: {normalized}")
    except Exception:
        pass
    return normalized

def _expand_short_esql(token: str) -> Optional[str]:
    """Expand very short natural tokens (e.g. "today") into a sane ESQL pipeline tail.
    Returns an ESQL tail that can follow a FROM stage, or None if not recognized.
    """
    if not token:
        return None
    t = token.strip().lower()

    # Today: [start of current day, start of next day)
    if t in {"today", "today()"}:
        return (
            "WHERE @timestamp >= DATE_TRUNC(1 day, NOW()) AND @timestamp < DATE_TRUNC(1 day, NOW()) + 1 day | STATS c = COUNT(*) BY level | SORT c DESC | LIMIT 5"
        )

    # Yesterday: [start of previous day, start of current day)
    if t == "yesterday":
        return (
            "WHERE @timestamp >= DATE_TRUNC(1 day, NOW()) - 1 day AND @timestamp < DATE_TRUNC(1 day, NOW()) | STATS c = COUNT(*) BY level | SORT c DESC | LIMIT 5"
        )

    # Last 24 hours rolling window
    if t in {"last 24 hours", "last 24h", "past day", "24h"}:
        return (
            "WHERE @timestamp >= NOW() - 1 day | STATS c = COUNT(*) BY level | SORT c DESC | LIMIT 5"
        )

    return None


def run_es_esql(esql: str) -> Tuple[int, Any]:
    """
    Run an ESQL query. Requires Elasticsearch 8.11+.
    Returns (row_count, rows_or_tables).
    """
    url = f"{DEFAULT_ES_URL.rstrip('/')}/_query"
    body = {"query": esql}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, auth=_es_auth(), headers=headers, json=body, timeout=TIMEOUT)
        if resp.status_code == 404:
            # Endpoint missing (older cluster) – guide the user to DSL mode
            raise HTTPException(
                status_code=400,
                detail="ESQL endpoint '/_query' not found on this cluster. Switch to DSL mode.",
            )
        if resp.status_code >= 400:
            # Bubble up ES error body to the client so we can see *why*
            try:
                err = resp.json()
            except Exception:
                err = {"raw": resp.text}
            raise HTTPException(
                status_code=400,
                detail={"message": "Elasticsearch ESQL error", "es_response": err, "query": esql},
            )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"message": "Elasticsearch ESQL transport error", "error": str(e), "query": esql})

    data = resp.json()
    values = data.get("values") or []
    return len(values), data


@app.get("/health")
def health():
    # Quick smoke checks to help troubleshooting
    info = {"ok": True, "es_url": DEFAULT_ES_URL, "es_index": ES_INDEX, "ollama_url": OLLAMA_URL, "model": OLLAMA_MODEL}
    try:
        r = requests.get(f"{OLLAMA_URL.rstrip('/')}/api/tags", timeout=10)
        info["ollama_models"] = [m.get("model") for m in r.json().get("models", [])]
    except Exception as e:
        info["ollama_models_error"] = str(e)
    return info


@app.get("/models")
def list_models():
    """Expose Ollama tags for quick debugging (what the CI step was checking)."""
    try:
        r = requests.get(f"{OLLAMA_URL.rstrip('/')}/api/tags", timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama tags error: {e}")
    return r.json()


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    system = build_system_prompt()
    user = build_user_prompt(req.question, req.time_range, req.size, req.prefer)
    llm = _ollama_generate_json(system, user)

    mode = (llm.get("mode") or "esql").lower()
    query = llm.get("query")

    if mode not in {"esql", "dsl"}:
        raise HTTPException(status_code=400, detail=f"Model returned invalid mode: {mode}")

    if mode == "dsl":
        if not isinstance(query, dict):
            raise HTTPException(status_code=400, detail="Expected DSL JSON object for 'query'.")
        hits, sample = run_es_dsl(query, req.size)
    else:  # esql
        if not isinstance(query, str):
            raise HTTPException(status_code=400, detail="Expected ESQL string for 'query'.")
        # If the model returned a very short natural token (e.g., "today"), expand it
        expanded_tail = _expand_short_esql(query)
        effective_query = expanded_tail if expanded_tail else query
        try:
            if expanded_tail:
                print(f"[ESQL expanded from token]: {query!r} -> {expanded_tail}")
            else:
                print(f"[ESQL no expansion applied]: {query!r}")
        except Exception:
            pass
        # Ensure the pipeline begins with our index
        normalized = _normalize_esql(effective_query)
        try:
            print(f"[ESQL final to execute]: {normalized}")
        except Exception:
            pass
        try:
            hits, sample = run_es_esql(normalized)
        except HTTPException as e:
            # One pragmatic fallback the user asked for: a deterministic query that is known to work
            fallback = (
                f"FROM {ES_INDEX} | "
                "WHERE @timestamp >= DATE_TRUNC(1 day, NOW()) "
                "AND @timestamp < DATE_TRUNC(1 day, NOW()) + 1 day | "
                "STATS c = COUNT(*) BY level | SORT c DESC | LIMIT 5"
            )
            try:
                try:
                    print("[ESQL falling back] original failed:")
                    print(normalized)
                    print("[ESQL fallback to execute]:", fallback)
                except Exception:
                    pass
                hits, sample = run_es_esql(fallback)
                # Also annotate the llm payload so the caller can see we fell back
                if isinstance(llm, dict):
                    llm['fallback_used'] = True
                    llm['original_esql'] = normalized
                    llm['fallback_esql'] = fallback
            except HTTPException:
                # Re-raise the original ESQL failure if fallback also fails
                raise e
        # Make sure downstream summary sees the final used query
        query = (normalized if not (isinstance(llm, dict) and llm.get('fallback_used'))
                 else llm['fallback_esql'])

    # Summarize back with the model (optional). We keep it local and short to save tokens.
    summary_prompt = textwrap.dedent(
        f"""
        Summarize the results below in 2-4 concise bullet points for an engineer.
        Focus on counts, spikes, top offenders, or anomalies. Keep it terse.

        MODE: {mode}
        QUERY: {json.dumps(query) if isinstance(query, dict) else str(query)}
        HITS: {hits}
        SAMPLE (first items):
        {json.dumps(sample[:3], default=str) if isinstance(sample, list) else json.dumps(sample, default=str)[:3000]}
        """
    ).strip()

    try:
        summary_obj = _ollama_generate_json(
            system_prompt="Return a JSON object: {\"summary\": \"...\"}. No extra text.",
            user_prompt=summary_prompt,
        )
        answer = summary_obj.get("summary") or "(no summary)"
    except HTTPException:
        # If the summarization call fails, don't fail the whole request.
        answer = "(summary unavailable; see raw results)"

    return AskResponse(
        mode=mode,
        query=query,
        hits=hits,
        sample=sample[:5] if isinstance(sample, list) else sample,
        answer=answer,
        llm_raw=llm,
    )
