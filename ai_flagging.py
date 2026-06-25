"""
ai_flagging.py — Calls the Claude API to flag cases for follow-up
(Fixed: the result is cached in the DB on BOTH success and failure, so the API
is never re-called on every rerun — which previously froze the page.)
"""
import streamlit as st
import requests
import json


def get_ai_flag(case_id, case_type, call_reason, priority, narrative, conn):
    """Call Claude API to recommend Yes / No / Not Sure for flagging.
    Result is cached in the DB so the API is only called once per case."""

    # Check cache first
    _c = conn.cursor()
    _c.execute("SELECT ai_flag, ai_reason FROM cases WHERE case_id=%s", (case_id,))
    cached = _c.fetchone()
    if cached and cached[0]:
        return cached[0], cached[1]

    prompt = f"""You are a public health triage assistant reviewing 911 call logs for behavioral health intervention.

Analyze this case and decide whether it should be FLAGGED for follow-up by a public health social worker.

Case details:
- Type: {case_type}
- Call Reason: {call_reason}
- Priority: {priority}
- Narrative: {narrative or "No narrative provided."}

Respond ONLY with a valid JSON object in this exact format (no other text):
{{"flag": "Yes", "reason": "brief one-sentence reason"}}

Where "flag" must be exactly one of: "Yes", "No", "Not Sure"
- Yes: clear behavioral health need requiring social worker follow-up
- No: no behavioral health concern identified
- Not Sure: some indicators present but more information needed"""

    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        flag, reason = "Not Sure", "API key not configured"
    else:
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=15,
            )
            data = resp.json()
            if "content" in data:
                text = data["content"][0]["text"].strip()
                result = json.loads(text)
                flag = result.get("flag", "Not Sure")
                reason = result.get("reason", "")
            else:
                # API returned an error object instead of content — surface the real error message
                err = data.get("error", {}).get("message", str(data)[:80])
                flag, reason = "Not Sure", f"API error: {err}"
        except Exception as e:
            flag, reason = "Not Sure", f"Analysis unavailable ({str(e)[:60]})"

    # Always cache the result (success OR failure) so Claude is never re-called on rerun
    _c2 = conn.cursor()
    _c2.execute(
        "UPDATE cases SET ai_flag=%s, ai_reason=%s WHERE case_id=%s",
        (flag, reason, case_id),
    )
    return flag, reason
