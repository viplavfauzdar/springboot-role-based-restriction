"""
Lightweight local AI log analyst for Elasticsearch + Ollama.

Quick start (first time on your laptop):
  1) python3 -m venv .venv && source .venv/bin/activate
  2) pip install fastapi "uvicorn[standard]" requests python-dotenv
  3) export ES_URL=http://localhost:9200
     export ES_INDEX=springboot-logs-*
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

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

APP_NAME = "Local AI Log Analyst"
DEFAULT_ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_INDEX = os.getenv("ES_INDEX", "springboot-logs-*")
ES_USERNAME = os.getenv("ES_USERNAME")
ES_PASSWORD = os.getenv("ES_PASSWORD")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
print(f"[agent] Using OLLAMA_MODEL={OLLAMA_MODEL}")

TIMEOUT = float(os.getenv("AGENT_HTTP_TIMEOUT", "600"))

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
    Call Ollama /api/generate and return a JSON object.

    Improvements:
      - Uses streaming mode to collect all chunks (some models return partials even with stream=False).
      - Aggregates 'response' pieces until we see {"done": true}.
      - Falls back to non-JSON parsing (```json fences or first balanced object).
      - If clear ESQL text is present but not JSON, wrap it into a JSON object for downstream.
      - Logs compact raw info (without the huge 'context').

    Returns a Python dict (parsed JSON) or a synthesized object with mode/query on ESQL heuristics.
    """
    using_chat = False
    # Choose endpoint and payload based on model name
    if OLLAMA_MODEL.lower().startswith("llama3"):
        using_chat = True
        url = f"{OLLAMA_URL.rstrip('/')}/api/chat"
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": True,
            "options": {"temperature": 0.1}
        }
    else:
        url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{system_prompt}\n\nUSER:\n{user_prompt}\n\nReturn ONLY a single JSON object matching the schema.",
            # We explicitly use streaming to handle models that trickle tokens even when asked not to.
            "stream": True,
            "options": {"temperature": 0.1},
            # Note: not setting "format": "json" here because many local models fail silently with it.
            # We'll instead parse JSON out of the text deterministically.
        }

    try:
        # Use a (connect, read) timeout tuple to allow long generations without dropping the socket.
        r = requests.post(url, json=payload, timeout=(10, TIMEOUT), stream=True)
        # If llama3 chat endpoint is not available in this Ollama build, retry using /api/generate.
        if using_chat and r is not None and getattr(r, "status_code", None) == 404:
            gen_url = f"{OLLAMA_URL.rstrip('/')}/api/generate"
            gen_payload = {
                "model": OLLAMA_MODEL,
                "prompt": f"{system_prompt}\n\nUSER:\n{user_prompt}",
                "stream": True,
                "options": {"temperature": 0.1},
            }
            url = gen_url
            payload = gen_payload
            r = requests.post(url, json=gen_payload, timeout=(10, TIMEOUT), stream=True)
        r.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {e}")

    # Ollama streaming returns one JSON object per line.
    chunks: list[Dict[str, Any]] = []
    buf: list[str] = []
    try:
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # If a line isn't JSON, ignore it (defensive)
                continue
            # Drop heavy context
            if isinstance(obj, dict) and "context" in obj:
                obj = {k: v for k, v in obj.items() if k != "context"}
            chunks.append(obj)
            piece = (
                obj.get("response") or
                (obj.get("message", {}) or {}).get("content") or
                ""
            )
            if piece:
                buf.append(piece)
            if obj.get("done") is True:
                break
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama stream error: {e}")

    combined = "".join(buf).strip()
    try:
        # Log the last chunk metadata plus the combined length.
        tail = chunks[-1] if chunks else {}
        if isinstance(tail, dict):
            tail.pop("context", None)
        print("[Ollama raw]:", json.dumps({"last_chunk": tail, "combined_len": len(combined)}, indent=2)[:2000])
    except Exception:
        pass

    if not combined:
        # Retry once with non-streaming, permissive prompt (some models behave better)
        if OLLAMA_MODEL.lower().startswith("llama3"):
            retry_payload = {
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "options": {"temperature": 0.0}
            }
            retry_url = f"{OLLAMA_URL.rstrip('/')}/api/chat"
        else:
            retry_payload = {
                "model": OLLAMA_MODEL,
                "prompt": f"{system_prompt}\n\nUSER:\n{user_prompt}\n\nRespond ONLY with a single JSON object (no prose).",
                "stream": False,
                "options": {"temperature": 0.0},
            }
            retry_url = url
        try:
            r2 = requests.post(retry_url, json=retry_payload, timeout=(10, TIMEOUT))
            r2.raise_for_status()
            wrapper2 = r2.json()
            wrapper2.pop("context", None)
            print("[Ollama raw retry]:", json.dumps({k: v for k, v in wrapper2.items() if k != "context"})[:2000])
            combined = (wrapper2.get("response") or (wrapper2.get("message", {}) or {}).get("content") or "").strip()
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Ollama retry error: {e}")

    if not combined:
        raise HTTPException(status_code=500, detail="Model returned an empty 'response'.")

    # 1) Try direct JSON
    try:
        return json.loads(combined)
    except json.JSONDecodeError:
        pass

    # 2) Try fenced ```json block
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", combined, re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3) Extract first balanced JSON object
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

    block = _extract_first_json_object(combined)
    if block:
        try:
            return json.loads(block)
        except Exception:
            pass

    # 4) Heuristic: salvage plain ESQL
    looks_like_esql = bool(re.search(r"\bFROM\b\s+\S+|\bfrom\b\s+\S+", combined))
    if looks_like_esql:
        # Try to pull the pipeline portion
        pipeline = combined
        m = re.search(r":\s*\"([^\"]+)\"", combined)
        if m:
            pipeline = m.group(1)
        return {
            "mode": "esql",
            "query": pipeline.strip(),
            "explanation": "Heuristically recovered ESQL from a non-JSON response"
        }

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
    return (
        f"User question{hint}: {question}\n\n"
        "Return a SINGLE JSON object. If mode is 'esql', 'query' MUST be a valid ESQL pipeline "
        "starting with an operator (e.g., WHERE/STATS/SORT/LIMIT) or a full pipeline, not a single word."
    )


def run_es_dsl(dsl: Dict[str, Any], size_cap: int) -> Tuple[int, Any]:
    """Run a DSL _search and return (hits_total, sample_docs)."""
    try:
        print("[DSL from model]:", json.dumps(dsl, indent=2)[:2000])
    except Exception:
        pass
    # Cap size if user/LLM forgot to
    if "size" not in dsl or int(dsl.get("size", 0)) > size_cap:
        dsl["size"] = size_cap
    url = f"{DEFAULT_ES_URL.rstrip('/')}/{ES_INDEX}/_search"
    try:
        print(f"[DSL target URL]: {url}")
    except Exception:
        pass
    try:
        resp = requests.post(url, auth=_es_auth(), json=dsl, timeout=TIMEOUT)
        if resp.status_code >= 400:
            try:
                err_body = resp.json()
            except Exception:
                err_body = {"raw": resp.text}
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Elasticsearch DSL error",
                    "es_response": err_body,
                    "query": dsl,
                    "url": url,
                },
            )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail={"message": "Elasticsearch DSL transport error", "error": str(e), "query": dsl, "url": url})
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
        try:
            print("[DSL final to execute]:", json.dumps(query, indent=2)[:2000])
        except Exception:
            pass
        hits, sample = run_es_dsl(query, req.size)
    else:  # esql
        if not isinstance(query, str):
            raise HTTPException(status_code=400, detail="Expected ESQL string for 'query'.")
        esql_raw = (query or "").strip()
        bad_literals = {"esql", "dsl", "query", "sql"}
        if not esql_raw or esql_raw.lower() in bad_literals or len(esql_raw) < 12:
            raise HTTPException(
                status_code=400,
                detail={"message": "Model produced invalid ESQL", "llm_raw": llm}
            )
        if not re.search(r"\b(where|stats|sort|limit|eval|keep|drop|rename|grok|dissect)\b", esql_raw, re.I):
            raise HTTPException(
                status_code=400,
                detail={"message": "Model ESQL missing pipeline operators", "query": query, "llm_raw": llm}
            )
        # Ensure the pipeline begins with our index
        normalized = _normalize_esql(esql_raw)
        try:
            print(f"[ESQL final to execute]: {normalized}")
        except Exception:
            pass
        # Execute exactly what the model produced (after normalization) or bubble up the ES error
        hits, sample = run_es_esql(normalized)
        query = normalized

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
