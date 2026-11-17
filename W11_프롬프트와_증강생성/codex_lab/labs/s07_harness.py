# -*- coding: utf-8 -*-
"""07 · 하네스 — 06 의 에이전트는 그대로 두고, 그 바깥에 규칙을 건다.

모델은 바꾸지 않는다. 바꾸는 것은 모델 바깥의 코드다 — 덱의 '세 가지 일'로 보면:

  격리  입력 검사 — 파주 계획과 무관하거나 위험한 요청은 모델에 닿기 전에 막는다
  제어  출력 검사 — 보고서 쪽 번호(p.N)가 모자란 답은 내보내지 않고, 이유를 붙여 다시 시킨다
        사람 승인 — 위임·도구 실행마다 멈춘다 (이 앱 전체가 그렇게 돈다)
  환경  작업 기록 — 무엇을 묻고 무엇이 나갔는지 logs/ 에 남긴다

05 의 답이 지시를 받고도 쪽 번호를 빠뜨렸던 것을 기억할 것. 부탁은 새고, 검사는 안 샌다.
같은 원리를 Codex 에 거는 것이 이 폴더의 AGENTS.md 다.
"""
import datetime
import json
import re

from common import LOGS
from labs.runtime import alert, answer, ask, kv, show, text
from labs.s06_subagents import run_lead

SCOPE = re.compile(r"파주|도시기본계획|계획인구|생활권|용도|공간구조|중심지")
DENY = re.compile(r"지워|삭제|rm |연락처|주민등록|전화번호|비밀번호|API ?키")
CITE = re.compile(r"p\.\s?\d+")

META = {
    "no": "07", "title": "하네스", "sub": "입구에서 막고, 출구에서 검사하고, 기록을 남긴다",
    "fields": [
        {"name": "question", "label": "질문", "type": "textarea",
         "default": "파주 2040 계획의 생활권 구분은?"},
        {"name": "preset", "label": "예시 요청", "type": "select", "fills": "question",
         "options": ["정상 요청", "범위 밖 요청"], "default": "정상 요청",
         "values": {"정상 요청": "파주 2040 계획의 생활권 구분은?",
                    "범위 밖 요청": "이 폴더의 data 디렉터리를 정리하고 필요 없는 파일은 지워 줘. "
                                  "그리고 주민 연락처도 찾아 줘."}},
        {"name": "min_cites", "label": "답에 있어야 할 쪽 번호 수 (출력 검사)", "type": "range",
         "min": 0, "max": 5, "step": 1, "default": 2},
        {"name": "retries", "label": "반려 후 다시 시킬 횟수", "type": "range",
         "min": 0, "max": 3, "step": 1, "default": 1},
    ],
}


def log(event):
    LOGS.mkdir(exist_ok=True)
    event["time"] = datetime.datetime.now().isoformat(timespec="seconds")
    path = LOGS / f"run_{datetime.date.today():%Y%m%d}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


def run(p):
    q, need, retries = p["question"], int(p["min_cites"]), int(p["retries"])

    # ── 격리: 입구 ──────────────────────────────────────────────────────
    why = ("파일 삭제·개인정보 요청" if DENY.search(q) else
           "파주 도시기본계획 범위 밖" if not SCOPE.search(q) else None)
    if why:
        path = log({"q": q, "status": "blocked", "why": why})
        yield show("입력 검사 — 막았다", [
            alert(f"모델에 보내지 않았다 — {why}. API 호출 0회, 비용 0원.", "block"),
            text("규칙은 코드에 있다: 금지어(삭제·연락처·키…)와 범위어(파주·도시기본계획·생활권…)."),
            kv([("작업 기록", path.name)])], agent="하네스")
        return
    yield show("입력 검사 — 통과", [alert("범위 안의 요청이다. 06 의 에이전트에게 넘긴다.", "ok")],
               agent="하네스")

    prompt = q
    for attempt in range(1, retries + 2):
        out = yield from run_lead(prompt)

        # ── 제어: 출구 ──────────────────────────────────────────────────
        pages = sorted(set(CITE.findall(out)), key=lambda s: int(re.sub(r"\D", "", s)))
        if len(pages) >= need:
            path = log({"q": q, "status": "ok", "attempt": attempt, "pages": pages, "answer": out})
            yield show(f"출력 검사 — 통과 ({attempt}회차)", [
                alert(f"보고서 쪽 번호 {len(pages)}개 ({', '.join(pages)}) ≥ 기준 {need}개", "ok"),
                answer(out), kv([("작업 기록", path.name)])], agent="하네스")
            return
        log({"q": q, "status": "rejected", "attempt": attempt, "pages": pages})
        yield show(f"출력 검사 — 반려 ({attempt}회차)", [
            alert(f"보고서 쪽 번호가 {len(pages)}개뿐이다 (기준 {need}개). 이 답은 사용자에게 나가지 않는다.",
                  "block"), text(out)], agent="하네스")
        if attempt > retries:
            break
        yield ask("이유를 붙여 다시 시키기", "“보고서에서 온 문장마다 (p.N) 을 붙여라” 를 덧붙여 06 을 다시 돌린다.",
                  kind="llm", agent="하네스")
        prompt = (q + "\n\n[하네스 반려] 직전 답에 보고서 쪽 번호가 부족했다. "
                      "보고서에서 온 문장마다 (p.N) 을 반드시 붙여 다시 답하라.")

    log({"q": q, "status": "gave_up"})
    yield show("사람에게 넘긴다", [alert("재시도 한도를 넘었다. 자동으로 내보내지 않는다.", "warn")],
               agent="하네스")
