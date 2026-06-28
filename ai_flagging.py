def _extract_json(text):
    """从模型输出里稳健地抠出 JSON —— 自动跳过 ```json 围栏和前言/后缀。"""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {text[:80]!r}")
    return json.loads(text[start:end + 1])


def get_ai_flag(case_id, case_type, call_reason, priority, narrative, conn):
    _c = conn.cursor()
    _c.execute("SELECT ai_flag, ai_reason FROM cases WHERE case_id=%s", (case_id,))
    cached = _c.fetchone()
    if cached and cached[0]:
        return cached[0], cached[1]

    prompt = f"""..."""  # 保持不变

    api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    cacheable = True       # 临时性失败不写死缓存,允许下次重试

    if not api_key:
        flag, reason = "Not Sure", "API key not configured"
    else:
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key,
                         "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": "claude-haiku-4-5-20251001",
                      "max_tokens": 150,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=15,
            )
            if resp.status_code != 200:
                # 非 200(包含空体的网关错误)在这里就拦掉,不进 resp.json()
                print(f"[ai_flagging] HTTP {resp.status_code}: {resp.text[:300]!r}")
                flag, reason, cacheable = "Not Sure", f"API HTTP {resp.status_code}", False
            else:
                data = resp.json()
                text = data["content"][0]["text"]
                result = _extract_json(text)          # ← 用稳健解析替代 json.loads
                flag = result.get("flag", "Not Sure")
                reason = result.get("reason", "")
                if flag not in ("Yes", "No", "Not Sure"):
                    flag, reason = "Not Sure", f"unexpected flag: {flag!r}"
        except requests.exceptions.RequestException as e:
            # 超时/连接错误属于临时故障,不写死缓存
            flag, reason, cacheable = "Not Sure", f"Network error: {str(e)[:60]}", False
        except Exception as e:
            # 解析失败时把原始文本打出来,方便定位
            print(f"[ai_flagging] parse error: {e} | raw={locals().get('text','')[:200]!r}")
            flag, reason = "Not Sure", f"Analysis unavailable ({str(e)[:60]})"

    if cacheable:
        _c2 = conn.cursor()
        _c2.execute("UPDATE cases SET ai_flag=%s, ai_reason=%s WHERE case_id=%s",
                    (flag, reason, case_id))
        conn.commit()          # ← 关键:缺这一行缓存根本不生效
    return flag, reason
