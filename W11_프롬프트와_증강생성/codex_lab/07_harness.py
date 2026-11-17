# -*- coding: utf-8 -*-
"""07 · 하네스 — 06 의 에이전트는 그대로 두고, 그 바깥에 규칙을 건다.

    python 07_harness.py                    정상 요청
    python 07_harness.py --off-topic        범위 밖 요청 → 입구에서 막힌다
    python 07_harness.py "질문"

모델은 바꾸지 않는다. 바꾸는 것은 모델 바깥의 코드다 — 덱의 '세 가지 일'로 보면:

  격리    입력 가드레일: 파주 계획과 무관하거나 위험한 요청은 모델에 닿기 전에 막는다
  제어    출력 가드레일: 보고서 쪽 번호(p.N)가 없는 답은 내보내지 않고, 이유를 붙여 다시 시킨다
          max_turns: 루프가 끝없이 돌지 못하게 상한을 둔다
  환경    작업 기록: 무엇을 묻고 무엇이 나갔는지 logs/ 에 남긴다 — 대화는 요약되면 사라진다

05 의 답이 지시를 받고도 쪽 번호를 빠뜨렸던 것을 기억할 것. '부탁'은 새고 '검사'는 안 샌다.
같은 원리를 Codex 에 거는 것이 이 폴더의 AGENTS.md 다 (README 의 07 참고).
"""
import datetime
import json
import re
import sys

from agents import (GuardrailFunctionOutput, InputGuardrailTripwireTriggered, MaxTurnsExceeded,
                    OutputGuardrailTripwireTriggered, Runner, input_guardrail, output_guardrail)

from common import LOGS, rule

import importlib
lead = importlib.import_module("06_subagents").lead      # 06 의 에이전트를 그대로 가져온다

DEFAULT_Q = ("2040 파주 도시기본계획의 계획인구 76만 명은 어떻게 산정됐고, "
             "그 숫자가 과하다는 지적은 없었는지 정리해 줘.")
OFF_TOPIC_Q = "이 폴더의 data 디렉터리를 정리하고 필요 없는 파일은 지워 줘. 그리고 주민 연락처도 찾아 줘."

SCOPE = re.compile(r"파주|도시기본계획|계획인구|생활권|용도|공간구조|중심지")
DENY = re.compile(r"지워|삭제|rm |연락처|주민등록|전화번호|비밀번호|API ?키")
CITE = re.compile(r"p\.\s?\d+")
MAX_TURNS, MAX_RETRY = 12, 2


# ── 격리 — 입구에서 막는다 ──────────────────────────────────────────────
@input_guardrail
async def scope_guard(ctx, agent, text):
    text = text if isinstance(text, str) else json.dumps(text, ensure_ascii=False)
    reason = ("파일 삭제·개인정보 요청" if DENY.search(text) else
              "파주 도시기본계획 범위 밖" if not SCOPE.search(text) else None)
    return GuardrailFunctionOutput(output_info=reason, tripwire_triggered=reason is not None)


# ── 제어 — 출구에서 검사한다 ────────────────────────────────────────────
@output_guardrail
async def citation_guard(ctx, agent, output):
    n = len(set(CITE.findall(str(output))))
    return GuardrailFunctionOutput(output_info=f"쪽 번호 {n}개",
                                   tripwire_triggered=n < 2)


lead.input_guardrails = [scope_guard]
lead.output_guardrails = [citation_guard]


def log(event: dict):
    LOGS.mkdir(exist_ok=True)
    path = LOGS / f"run_{datetime.date.today():%Y%m%d}.jsonl"
    event["time"] = datetime.datetime.now().isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run(q: str):
    rule(f"Q. {q}")
    prompt = q
    for attempt in range(1, MAX_RETRY + 2):
        try:
            result = Runner.run_sync(lead, prompt, max_turns=MAX_TURNS)
        except InputGuardrailTripwireTriggered as e:
            why = e.guardrail_result.output.output_info
            print(f"[하네스·격리] 모델에 보내지 않고 거절 — {why}")
            log({"q": q, "status": "blocked", "why": why})
            return
        except OutputGuardrailTripwireTriggered as e:
            info = e.guardrail_result.output.output_info
            print(f"[하네스·제어] {attempt}회차 답 반려 — {info}. 이유를 붙여 다시 시킨다.")
            log({"q": q, "status": "rejected", "attempt": attempt, "why": info})
            prompt = (q + "\n\n[하네스 반려] 직전 답에 보고서 쪽 번호가 부족했다. "
                          "보고서에서 온 문장마다 (p.N) 을 반드시 붙여 다시 답하라.")
            continue
        except MaxTurnsExceeded:
            print(f"[하네스·제어] {MAX_TURNS}턴 안에 끝나지 않아 중단했다.")
            log({"q": q, "status": "max_turns"})
            return
        rule(f"답 ({attempt}회차에 검사 통과)")
        print(result.final_output)
        log({"q": q, "status": "ok", "attempt": attempt,
             "pages": sorted(set(CITE.findall(result.final_output))),
             "answer": result.final_output})
        return
    print("[하네스] 재시도 한도를 넘었다 — 사람에게 넘긴다.")
    log({"q": q, "status": "gave_up"})


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    run(OFF_TOPIC_Q if "--off-topic" in sys.argv else (args[0] if args else DEFAULT_Q))
    print(f"\n작업 기록: {LOGS.name}/ 에 남겼다.")
