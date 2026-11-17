# -*- coding: utf-8 -*-
"""03 · system prompt — 역할로 통제하고, 그다음엔 자료를 실어 준다.

"모르면 모른다고 하라"를 넣어도 지어내기는 잘 안 멈춘다. 보고서 5쪽을 실으면 맞힌다.
이 '손으로 잘라 붙이기'가 RAG 의 원형이다 — 04 는 그것을 검색으로 바꾼다.
"""
import rag
from common import QUESTION, SAMPLING_MODEL, client
from labs.runtime import alert, answer, ask, code, kv, messages, show, text

PRESETS = {
    "초등학생": "너는 초등학교 1학년이고, 반말로 대답한다.",
    "공무원": "너는 도시계획 전문 공무원이다. 정중하고 간결하게 답한다.",
    "모르면 모른다고": "너는 도시계획 전문 공무원이다. 확실히 아는 사실만 말하고, "
                       "학습 자료에 없거나 확신이 없으면 '모릅니다'라고 답한다.",
}

META = {
    "no": "03", "title": "system prompt", "sub": "역할로 통제하고, 자료를 실어 본다",
    "fields": [
        {"name": "preset", "label": "system 프리셋", "type": "select",
         "options": list(PRESETS), "default": "모르면 모른다고", "fills": "system",
         "values": PRESETS},
        {"name": "system", "label": "system 내용 (직접 고쳐도 된다)", "type": "textarea",
         "default": PRESETS["모르면 모른다고"]},
        {"name": "attach", "label": "보고서 PDF 5쪽 원문을 system 에 싣기", "type": "checkbox",
         "default": False},
        {"name": "question", "label": "질문", "type": "textarea", "default": QUESTION},
    ],
}


def run(p):
    system = p["system"]
    if p.get("attach"):
        yield ask("PDF 5쪽 꺼내기", "보고서에서 5쪽 글자를 뽑는다 (내 컴퓨터 안에서만, 비용 없음).",
                  kind="local")
        page = rag.page_text(5)
        yield show("PDF 5쪽 — 주요 변경사항 표", [text(page[:1500] + ("…" if len(page) > 1500 else ""))])
        system += ("\n아래 [자료]에 근거해서만 답하고, 근거가 된 쪽 번호를 밝힌다."
                   "\n\n[자료 · 2040년 파주도시기본계획 보고서 PDF 5쪽]\n" + page)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": p["question"]}]
    yield ask("요청 보내기", f"system {len(system):,}자 + user 한 줄 (temperature=0)",
              [messages(msgs), code({"model": SAMPLING_MODEL, "temperature": 0, "messages": msgs},
                                    "요청 본문 (JSON)")])
    r = client().chat.completions.create(model=SAMPLING_MODEL, temperature=0, messages=msgs)
    note = ("자료 한 쪽을 실었더니 입력 토큰이 이만큼 늘었다. 721쪽을 다 실을 수 있을까? → 04"
            if p.get("attach") else
            "지시만으로는 지어내기가 잘 안 멈춘다. 모델은 자기가 모른다는 것을 모른다. "
            "이제 '보고서 5쪽 싣기'를 켜고 다시 해 볼 것.")
    yield show("응답", [answer(r.choices[0].message.content),
                        kv([("입력 토큰", r.usage.prompt_tokens), ("출력 토큰", r.usage.completion_tokens)]),
                        alert(note, "warn" if not p.get("attach") else "ok")])
