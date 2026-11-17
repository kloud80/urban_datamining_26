# -*- coding: utf-8 -*-
"""06 · 서브에이전트 — 총괄 에이전트가 일을 쪼개 전문 에이전트에게 맡긴다.

    python 06_subagents.py
    python 06_subagents.py "2040 파주 계획의 공간구조를 2030 계획과 비교하고 언론 평가를 붙여 줘"

  총괄(lead)
   ├─ 계획문서 담당  — search_paju_plan 만 쓴다. 보고서 안의 사실만.
   └─ 웹 리서치 담당 — web_search 만 쓴다. 보고서 밖의 최근 보도만.

각 담당은 자기 대화창(컨텍스트)에서 따로 일하고, 총괄에게는 요약만 돌려준다.
총괄의 컨텍스트가 검색 원문으로 넘치지 않는 것 — 서브에이전트를 쓰는 진짜 이유다.
OpenAI Agents SDK (pip install openai-agents) 의 'agent.as_tool' 을 쓴다.
"""
import sys

from agents import Agent, Runner, WebSearchTool, function_tool

from common import AGENT_MODEL, rule
from rag import search

Q = (sys.argv[1] if len(sys.argv) > 1 else
     "2040 파주 도시기본계획의 계획인구 76만 명은 어떻게 산정됐고, "
     "그 숫자가 과하다는 지적은 없었는지 정리해 줘.")


@function_tool
def search_paju_plan(query: str) -> str:
    """2040년 파주 도시기본계획 보고서(2026.06, 721쪽)에서 관련 조각을 찾는다. 결과에 PDF 쪽 번호가 붙는다."""
    print(f"   · 계획문서 담당 → search_paju_plan({query!r})")
    return search(query)


plan_agent = Agent(
    name="계획문서 담당", model=AGENT_MODEL, tools=[search_paju_plan],
    instructions="보고서 검색 결과에 있는 내용만 쓴다. 문장마다 (p.N) 을 붙인다. "
                 "보고서에 없으면 '보고서에서 찾지 못함'이라고 쓴다. 다섯 줄 이내로 요약한다.")

web_agent = Agent(
    name="웹 리서치 담당", model=AGENT_MODEL, tools=[WebSearchTool()],
    instructions="2026년 이후의 보도·평가만 찾는다. 항목마다 매체명과 URL 을 붙인다. "
                 "다섯 줄 이내로 요약한다.")

lead = Agent(
    name="총괄", model=AGENT_MODEL,
    tools=[plan_agent.as_tool("ask_plan_researcher", "보고서 안의 사실을 계획문서 담당에게 묻는다"),
           web_agent.as_tool("ask_web_researcher", "보고서 밖의 최근 보도·평가를 웹 리서치 담당에게 묻는다")],
    instructions="질문을 보고서 쪽과 웹 쪽으로 나눠 각 담당에게 맡긴 뒤, 두 결과를 합쳐 답한다. "
                 "직접 검색하지 않는다. 보고서 근거(p.N)와 웹 출처를 구분해서 보여 준다.")

if __name__ == "__main__":
    rule(f"Q. {Q}")
    result = Runner.run_sync(lead, Q, max_turns=12)
    for item in result.new_items:
        if item.type == "tool_call_item":
            print(f"[총괄] → {getattr(item.raw_item, 'name', '?')}")
    rule("답")
    print(result.final_output)
