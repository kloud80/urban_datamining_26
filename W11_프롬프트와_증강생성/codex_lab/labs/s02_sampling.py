# -*- coding: utf-8 -*-
"""02 · temperature 와 top_p — 확률표에서 무엇을 뽑을지 흔드는 두 손잡이.

1) 첫 토큰 확률표(상위 10개)를 받는다. 화면의 슬라이더로 온도를 바꾸면
   p_T ∝ p^(1/T) 로 다시 계산해 막대가 뾰족해지고 평평해진다. top_p 선은 누적 확률이
   그 값에 찰 때까지만 후보로 남기는 경계다. (API 의 logprobs 는 온도 적용 전 값이고,
   화면 계산은 상위 10개만으로 다시 정규화한 근사다.)
2) 같은 질문을 지정한 설정으로 5번 보내 답이 얼마나 갈리는지 본다.
"""
from common import SAMPLING_MODEL, client
from labs.runtime import alert, ask, code, show

META = {
    "no": "02", "title": "temperature · top_p", "sub": "확률표를 뾰족하게, 평평하게 — 그리고 추첨",
    "fields": [
        {"name": "question", "label": "질문", "type": "textarea",
         "default": "파주시를 대표하는 단어 하나만 답해. 설명 없이 단어만."},
        {"name": "temperature", "label": "temperature", "type": "range",
         "min": 0, "max": 2, "step": 0.1, "default": 1.0},
        {"name": "top_p", "label": "top_p", "type": "range", "min": 0.05, "max": 1,
         "step": 0.05, "default": 1.0},
    ],
}


def run(p):
    c = client()
    msgs = [{"role": "user", "content": p["question"]}]
    T, top_p = float(p["temperature"]), float(p["top_p"])

    yield ask("첫 토큰 확률표 받기", "logprobs=True, top_logprobs=10 으로 한 토큰만 받는다.",
              [code({"model": SAMPLING_MODEL, "messages": msgs, "max_tokens": 1,
                     "logprobs": True, "top_logprobs": 10}, "요청")])
    r = c.chat.completions.create(model=SAMPLING_MODEL, messages=msgs, max_tokens=1,
                                  logprobs=True, top_logprobs=10, temperature=0)
    top = r.choices[0].logprobs.content[0].top_logprobs
    yield show("모델이 낸 다음 토큰 확률표",
               [{"type": "logprobs", "items": [{"token": t.token, "logprob": t.logprob} for t in top],
                 "temperature": T, "top_p": top_p},
                alert("슬라이더를 움직여 보라 — API 를 다시 부르지 않고 같은 확률표를 다시 계산한다.")])

    yield ask(f"같은 질문 5번 보내기", f"temperature={T}, top_p={top_p}, n=5",
              [code({"model": SAMPLING_MODEL, "messages": msgs, "n": 5, "max_tokens": 20,
                     "temperature": T, "top_p": top_p}, "요청")])
    r = c.chat.completions.create(model=SAMPLING_MODEL, messages=msgs, n=5, max_tokens=20,
                                  temperature=T, top_p=top_p)
    answers = [ch.message.content.strip() for ch in r.choices]
    yield show(f"5번의 답 — 서로 다른 답 {len(set(answers))}개",
               [{"type": "samples", "items": answers},
                alert("temperature=0 이어도 다섯 번이 완전히 같지 않을 수 있다(서버 쪽 비결정성). "
                      "그리고 1등 토큰은 '가장 자주 이어졌던 것'이지 '사실'이 아니다.")])
