# -*- coding: utf-8 -*-
"""05~07 이 쓰는 도구 두 개. 실행 전에 반드시 승인을 받는다.

web_search 는 OpenAI 내장 도구를 그대로 모델에 주면 OpenAI 서버 안에서 실행돼 우리가
끼어들 틈이 없다. 그래서 우리 함수로 감쌌다 — 실행 여부를 우리가(사람이) 정할 수 있게.
"""
import re

import rag
from common import AGENT_MODEL, client
from labs.runtime import alert, ask, chunks, fn_tool, show, text

SEARCH_PLAN = fn_tool("search_paju_plan",
                      "2040년 파주 도시기본계획 최종 보고서(2026.06, 721쪽)에서 관련 조각을 찾는다. "
                      "결과에는 PDF 쪽 번호(p.N)가 붙어 있다.")
WEB_SEARCH = fn_tool("web_search", "웹에서 최근 보도·평가를 찾는다. 보고서에 없는 내용용.")


def run_search_plan(query, agent=None):
    yield ask(f"도구 실행 · search_paju_plan", f"보고서 벡터 인덱스에서 “{query}” 와 가까운 조각 5개를 찾는다.",
              kind="tool", agent=agent)
    nodes = rag.retrieve(query, k=5)
    yield show(f"search_paju_plan 결과 — {len(nodes)}개 조각",
               [chunks([{"page": n.metadata["page"], "score": round(n.score, 3),
                         "text": n.get_content()} for n in nodes])], agent=agent)
    return "\n\n".join(f"[p.{n.metadata['page']} · 유사도 {n.score:.2f}]\n{n.get_content()}"
                       for n in nodes)


def run_web_search(query, agent=None):
    yield ask("도구 실행 · web_search", f"웹에서 “{query}” 를 검색한다 (OpenAI 웹 검색, 비용 발생).",
              kind="tool", agent=agent)
    r = client().responses.create(
        model=AGENT_MODEL, tools=[{"type": "web_search"}],
        input=f"다음을 웹에서 찾아 다섯 줄 이내로 요약하라. 항목마다 매체명과 URL 을 붙여라: {query}")
    out = re.sub(r"\?utm_source=openai", "", r.output_text)
    yield show("web_search 결과", [text(out),
                                   alert("이 내용은 보고서 밖에서 왔다 — 보고서 근거(p.N)와 섞지 말 것.")],
               agent=agent)
    return out


def executors(agent=None):
    return {"search_paju_plan": lambda query: run_search_plan(query, agent),
            "web_search": lambda query: run_web_search(query, agent)}
