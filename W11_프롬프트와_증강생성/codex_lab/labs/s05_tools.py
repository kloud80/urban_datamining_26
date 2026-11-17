# -*- coding: utf-8 -*-
"""05 · 툴 콜링 — 모델에게 '찾는 법'을 쥐여 주고, 무엇을 언제 찾을지는 모델이 정한다.

모델은 도구를 직접 실행하지 못한다. "이 도구를 이 인자로 불러 달라"는 구조체를 낼
뿐이고, 실행해서 결과를 돌려주는 것은 우리 코드다 — 그리고 여기서는 실행 전마다
사람이 승인한다. 이 루프가 커진 것이 에이전트이고, 그 바깥이 하네스다.
"""
from labs import tools
from labs.runtime import tool_loop

INSTRUCTIONS = ("너는 도시계획 리서치 조수다. 계획 내용은 search_paju_plan 으로, "
                "보고서에 없는 최근 평가·보도는 web_search 로 찾는다. "
                "답에는 보고서 쪽 번호(p.N)와 웹 출처를 붙인다.")

META = {
    "no": "05", "title": "툴 콜링", "sub": "보고서 검색 · 웹 검색을 도구로 쥐여 준다",
    "fields": [{"name": "question", "label": "질문", "type": "textarea",
                "default": "2040 파주 도시기본계획의 계획인구는 몇 명이고, 최근 언론은 그 숫자를 어떻게 평가했나?"}],
}


def run(p):
    yield from tool_loop("모델", INSTRUCTIONS, [tools.SEARCH_PLAN, tools.WEB_SEARCH],
                         p["question"], tools.executors("모델"))
