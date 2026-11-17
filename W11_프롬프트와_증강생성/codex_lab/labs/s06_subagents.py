# -*- coding: utf-8 -*-
"""06 · 서브에이전트 — 총괄이 일을 쪼개 전문 담당에게 맡긴다.

  총괄
   ├─ 계획문서 담당  search_paju_plan 만 쓴다 — 보고서 안의 사실만
   └─ 웹 리서치 담당 web_search 만 쓴다      — 보고서 밖의 최근 보도만

담당은 자기 대화창(컨텍스트)에서 따로 일하고 총괄에게는 요약만 돌려준다. 총괄의
컨텍스트가 검색 원문으로 넘치지 않는 것 — 서브에이전트를 쓰는 진짜 이유다.
위임도, 담당의 도구 실행도 전부 승인을 받는다. 화면의 색 띠가 누가 일하는지 표시한다.
(Agents SDK 의 agent.as_tool 과 같은 구조를, 보이게 하려고 직접 짰다.)
"""
from labs import tools
from labs.runtime import ask, fn_tool, show, text, tool_loop

LEAD, PLAN, WEB = "총괄", "계획문서 담당", "웹 리서치 담당"

PLAN_INSTR = ("너는 계획문서 담당이다. search_paju_plan 결과에 있는 내용만 쓴다. 문장마다 (p.N) 을 붙인다. "
              "보고서에 없으면 '보고서에서 찾지 못함'이라고 쓴다. 다섯 줄 이내로 요약한다.")
WEB_INSTR = ("너는 웹 리서치 담당이다. 2026년 이후의 보도·평가만 web_search 로 찾는다. "
             "항목마다 매체명과 URL 을 붙인다. 다섯 줄 이내로 요약한다.")
LEAD_INSTR = ("너는 총괄이다. 질문을 보고서 쪽과 웹 쪽으로 나눠 ask_plan_researcher, ask_web_researcher 에게 "
              "맡긴 뒤 두 결과를 합쳐 답한다. 직접 검색하지 않는다. 보고서 근거(p.N)와 웹 출처를 구분해 보여 준다.")

LEAD_TOOLS = [fn_tool("ask_plan_researcher", "보고서 안의 사실을 계획문서 담당에게 맡긴다", "task", "맡길 일"),
              fn_tool("ask_web_researcher", "보고서 밖의 최근 보도·평가를 웹 리서치 담당에게 맡긴다", "task", "맡길 일")]

META = {
    "no": "06", "title": "서브에이전트", "sub": "총괄이 계획문서 담당·웹 리서치 담당에게 나눠 맡긴다",
    "fields": [{"name": "question", "label": "질문", "type": "textarea",
                "default": "2040 파주 도시기본계획의 계획인구 76만 명은 어떻게 산정됐고, "
                           "그 숫자가 과하다는 지적은 없었는지 정리해 줘."}],
}


def delegate(who, instr, tool, task):
    yield ask(f"{who}에게 위임", f"총괄이 맡기려는 일: “{task}”", kind="tool", agent=LEAD)
    yield show(f"{who} 시작 — 새 대화창에서 일한다", [text(task)], agent=who)
    ex = tools.executors(who)
    out = yield from tool_loop(who, instr, [tool], task, {tool["name"]: ex[tool["name"]]}, max_turns=4)
    yield show(f"{who} → 총괄에게 보고", [text(out)], agent=LEAD)
    return out


def lead_executors():
    return {"ask_plan_researcher": lambda task: delegate(PLAN, PLAN_INSTR, tools.SEARCH_PLAN, task),
            "ask_web_researcher": lambda task: delegate(WEB, WEB_INSTR, tools.WEB_SEARCH, task)}


def run_lead(question):
    return (yield from tool_loop(LEAD, LEAD_INSTR, LEAD_TOOLS, question, lead_executors(), max_turns=5))


def run(p):
    yield from run_lead(p["question"])
