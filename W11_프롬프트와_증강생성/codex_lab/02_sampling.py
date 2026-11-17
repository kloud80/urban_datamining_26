# -*- coding: utf-8 -*-
"""02 · temperature 와 top_p — 확률표에서 무엇을 뽑을지 흔드는 두 손잡이.

    python 02_sampling.py
    python 02_sampling.py "파주시를 대표하는 단어 하나만 답해."

1) 모델이 낸 첫 토큰 확률표(상위 5개)를 보여 주고, 온도를 바꾸면 그 표가 어떻게
   뾰족해지고 평평해지는지 계산해 본다:  p_T ∝ p^(1/T)
2) 같은 질문을 설정마다 5번씩 실제로 보낸다 — 답이 얼마나 갈리는지 본다.

API 가 돌려주는 logprobs 는 온도를 적용하기 전 확률이다. 그래서 1) 은 우리가 직접
다시 계산한 것이고, 상위 5개만으로 다시 정규화한 근사다.
"""
import math
import sys

from common import SAMPLING_MODEL, client, rule

Q = sys.argv[1] if len(sys.argv) > 1 else "파주시를 대표하는 단어 하나만 답해. 설명 없이 단어만."
c = client()

# ── 1) 확률표 ────────────────────────────────────────────────────────────
r = c.chat.completions.create(model=SAMPLING_MODEL, messages=[{"role": "user", "content": Q}],
                              logprobs=True, top_logprobs=5, max_tokens=5, temperature=0)
top = r.choices[0].logprobs.content[0].top_logprobs
rule(f"Q. {Q}\n 첫 토큰 확률표 (상위 5개)")


def bar(p):
    return "█" * max(1, round(p * 40))


for T in (0.5, 1.0, 1.5):
    w = [math.exp(t.logprob / T) for t in top]
    z = sum(w)
    print(f"\nT = {T}")
    for t, wi in zip(top, w):
        p = wi / z
        print(f"  {t.token!r:>12}  {p:5.2f}  {bar(p)}")

# ── 2) 실제로 5번씩 ──────────────────────────────────────────────────────
SETTINGS = [
    ("temperature=0", dict(temperature=0)),
    ("temperature=1.0", dict(temperature=1.0)),
    ("temperature=1.5", dict(temperature=1.5)),
    ("temperature=1.5, top_p=0.3", dict(temperature=1.5, top_p=0.3)),
]
for name, kw in SETTINGS:
    r = c.chat.completions.create(model=SAMPLING_MODEL, n=5, max_tokens=20,
                                  messages=[{"role": "user", "content": Q}], **kw)
    answers = [ch.message.content.strip() for ch in r.choices]
    rule(f"{name}  →  서로 다른 답 {len(set(answers))}개")
    for a in answers:
        print("  ·", a)

print("\n온도를 올리면 순위가 무너지고, top_p 를 낮추면 꼬리를 잘라 다시 모인다."
      "\ntemperature=0 이어도 다섯 번이 완전히 같지 않을 수 있다 — 서버 쪽 연산 순서 차이다."
      "\n그리고 기억할 것 — 1등 토큰은 '가장 자주 이어졌던 것'이지 '사실'이 아니다.")
