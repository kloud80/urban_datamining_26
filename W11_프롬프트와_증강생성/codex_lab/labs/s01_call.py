# -*- coding: utf-8 -*-
"""01 · API 를 직접 부른다 — messages 에 user 한 줄.

모델은 2026년 6월에 승인된 파주 계획을 학습했을 리 없다. 그런데도 숫자를 말한다면,
그 숫자는 어디서 왔을까? 대화를 이어 가면 messages 가 계속 길어지는 것도 본다.
"""
from common import QUESTION, SAMPLING_MODEL, client
from labs.runtime import alert, answer, ask, code, kv, messages, show

META = {
    "no": "01", "title": "API 직접 호출", "sub": "user 한 줄을 보내고 무엇이 돌아오는지 본다",
    "chat": True,
    "fields": [{"name": "question", "label": "질문", "type": "textarea", "default": QUESTION}],
}


def run(p):
    history = p.get("history") or []
    msgs = history + [{"role": "user", "content": p["question"]}]
    payload = {"model": SAMPLING_MODEL, "messages": msgs}
    yield ask("요청 보내기", "이 JSON 이 그대로 OpenAI 서버로 간다. 모델은 이것 말고는 아무것도 모른다.",
              [messages(msgs), code(payload, "요청 본문 (JSON)")])
    r = client().chat.completions.create(**payload)
    a = r.choices[0].message.content
    yield show("응답", [answer(a),
                        kv([("입력 토큰", r.usage.prompt_tokens), ("출력 토큰", r.usage.completion_tokens),
                            ("이번에 보낸 메시지 수", len(msgs))]),
                        code(r.model_dump(exclude_none=True), "응답 원문 (JSON)"),
                        alert("정답: 약 76.0만 명 — 보고서 PDF 5쪽 '주요 변경사항' 표. "
                              "같은 질문을 다시 보내 숫자가 바뀌는지 볼 것.", "warn")])
    yield show("_history", [{"type": "history", "items": msgs + [{"role": "assistant", "content": a}]}])
