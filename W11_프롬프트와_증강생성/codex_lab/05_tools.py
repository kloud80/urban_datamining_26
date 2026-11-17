# -*- coding: utf-8 -*-
"""05 · 툴 콜링 — 모델에게 '찾는 법'을 쥐여 주고, 무엇을 언제 찾을지는 모델이 정한다.

    python 05_tools.py
    python 05_tools.py "파주 계획인구 76만은 통계청 추계보다 얼마나 많은가?"

도구 두 개:
  search_paju_plan  — 04 의 벡터 검색을 함수로 감쌌다 (우리가 만든 도구)
  web_search        — OpenAI 가 제공하는 웹 검색 (내장 도구)

모델은 도구를 직접 실행하지 못한다. "이 도구를 이 인자로 불러 달라"는 구조체를 낼
뿐이고, 실행해서 결과를 돌려주는 것은 아래 while 루프 — 우리 코드다. 그 왕복을
화면에 그대로 찍는다. 이 루프가 커진 것이 에이전트이고, 그 바깥이 하네스다.
"""
import json
import sys

from common import AGENT_MODEL, client, rule
from rag import search

Q = (sys.argv[1] if len(sys.argv) > 1 else
     "2040 파주 도시기본계획의 계획인구는 몇 명이고, 최근 언론은 그 숫자를 어떻게 평가했나?")
c = client()

TOOLS = [
    {"type": "function", "name": "search_paju_plan",
     "description": "2040년 파주 도시기본계획 최종 보고서(2026.06, 721쪽)에서 관련 조각을 찾는다. "
                    "결과에는 PDF 쪽 번호가 붙어 있다.",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string", "description": "찾을 내용 (한국어)"}},
         "required": ["query"], "additionalProperties": False},
     "strict": True},
    {"type": "web_search"},
]
INSTRUCTIONS = ("너는 도시계획 리서치 조수다. 계획 내용은 search_paju_plan 으로, "
                "보고서에 없는 최근 평가·보도는 web_search 로 찾는다. "
                "답에는 보고서 쪽 번호(p.N)와 웹 출처를 붙인다.")

rule(f"Q. {Q}")
inputs = [{"role": "user", "content": Q}]
for turn in range(1, 8):                                    # 무한히 돌지 않게 상한을 둔다
    r = c.responses.create(model=AGENT_MODEL, instructions=INSTRUCTIONS,
                           tools=TOOLS, input=inputs)
    calls = []
    for item in r.output:
        if item.type == "web_search_call":
            q = getattr(getattr(item, "action", None), "query", None)
            print(f"[{turn}] 모델 → web_search  {q or ''}   (OpenAI 쪽에서 실행)")
        elif item.type == "function_call":
            calls.append(item)
    if not calls:                                           # 더 부를 도구가 없다 = 끝
        rule("답")
        print(r.output_text)
        break
    inputs += r.output                                      # 모델이 낸 호출을 대화에 붙이고
    for call in calls:
        args = json.loads(call.arguments)
        print(f"[{turn}] 모델 → {call.name}({args})")
        result = search(**args)                             # 실행은 우리가 한다
        print(f"     우리 코드가 실행 → {len(result)}자 돌려줌 "
              f"(쪽: {', '.join(l.split(' ·')[0][1:] for l in result.splitlines() if l.startswith('[p.'))})")
        inputs.append({"type": "function_call_output", "call_id": call.call_id,
                       "output": result})
