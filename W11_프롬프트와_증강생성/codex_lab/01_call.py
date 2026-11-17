# -*- coding: utf-8 -*-
"""01 · API 를 직접 부른다 — messages 에 user 한 줄.

    python 01_call.py                 기본 질문 한 번
    python 01_call.py --chat          대화 모드 (빈 줄이나 'q' 로 끝)

모델은 2026년 6월에 승인된 파주 계획을 학습했을 리 없다. 그런데도 숫자를 말한다면
그 숫자는 어디서 왔을까? — 이 질문으로 수업을 시작한다.
"""
import sys

from common import QUESTION, SAMPLING_MODEL, client, rule

c = client()


def ask(messages):
    r = c.chat.completions.create(model=SAMPLING_MODEL, messages=messages)
    return r.choices[0].message.content, r.usage


if "--chat" not in sys.argv:
    rule(f"Q. {QUESTION}")
    answer, usage = ask([{"role": "user", "content": QUESTION}])
    print(answer)
    print(f"\n[토큰] 입력 {usage.prompt_tokens} · 출력 {usage.completion_tokens}")
    print("[정답] 약 76.0만 명 — 보고서 PDF 5쪽 '주요 변경사항' 표")
    sys.exit()

# 대화는 결국 messages 리스트에 계속 붙이는 것뿐이다. 모델은 기억하지 않는다.
history = []
print(f"대화 모드 · {SAMPLING_MODEL} (빈 줄 또는 q 로 끝)")
while True:
    q = input("\n나> ").strip()
    if q in ("", "q"):
        break
    history.append({"role": "user", "content": q})
    answer, usage = ask(history)
    history.append({"role": "assistant", "content": answer})
    print(f"AI> {answer}\n    (이번 호출에 보낸 메시지 {len(history) - 1}개 · 입력 토큰 {usage.prompt_tokens})")
