# -*- coding: utf-8 -*-
"""단계 실행기 — 모든 실험은 '승인받고 한 칸씩' 진행한다.

실험 하나는 파이썬 제너레이터다. 두 종류의 이벤트를 낸다.

  show(...)  지금 막 한 일의 결과. 화면에 카드로 쌓인다. 멈추지 않는다.
  ask(...)   다음에 할 일. 여기서 멈추고 사람의 [승인]을 기다린다.

승인하면 다음 ask 가 나올 때까지 돌고, 그동안 나온 show 를 한꺼번에 돌려준다.
[중단]하면 제너레이터를 닫는다 — 그 뒤의 API 호출은 일어나지 않는다.
이 '사람이 중간에 끼는 자리'가 덱에서 말한 하네스의 가장 단순한 모습이다.
"""
import itertools
import json
import threading
import time

from common import AGENT_MODEL, client

# ── 이벤트 ───────────────────────────────────────────────────────────────


def show(title, blocks, agent=None):
    return {"ev": "show", "title": title, "blocks": blocks, "agent": agent}


def ask(title, detail="", blocks=None, kind="llm", agent=None):
    """kind: llm(모델 호출·비용) · tool(도구 실행) · local(내 컴퓨터에서만) · cost(시간·비용 큼)"""
    return {"ev": "ask", "title": title, "detail": detail, "blocks": blocks or [],
            "kind": kind, "agent": agent}


# ── 블록 (화면 조각) ─────────────────────────────────────────────────────


def text(t):
    return {"type": "text", "text": t}


def answer(t):
    return {"type": "answer", "text": t}


def alert(t, level="info"):
    return {"type": "alert", "text": t, "level": level}     # info · ok · warn · block


def kv(pairs):
    return {"type": "kv", "items": [[str(k), str(v)] for k, v in pairs]}


def code(obj, title="JSON", open_=False):
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2)
    return {"type": "code", "title": title, "text": s, "open": open_}


def messages(msgs):
    """ChatML 메시지를 역할별 말풍선으로."""
    out = []
    for m in msgs:
        c = m.get("content", "")
        out.append({"role": m.get("role", "?"),
                    "content": c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)})
    return {"type": "messages", "items": out}


def chunks(items):
    return {"type": "chunks", "items": items}            # [{page, score, text}]


# ── 실행 상태 ────────────────────────────────────────────────────────────

RUNS: dict = {}
_ids = itertools.count(1)
_lock = threading.Lock()


class Run:
    def __init__(self, gen):
        self.id = str(next(_ids))
        self.gen = gen
        self.pending = None
        self.done = False
        self.approvals = 0
        self.started = time.time()


def advance(run: Run):
    """다음 ask 가 나올 때까지 돌린다. 그동안의 show 들을 돌려준다."""
    shown = []
    try:
        while True:
            ev = next(run.gen)
            if ev["ev"] == "show":
                shown.append(ev)
            else:
                run.pending = ev
                break
    except StopIteration:
        run.pending, run.done = None, True
    except Exception as e:                                   # 실습 중 오류도 화면에 보인다
        shown.append(show("오류", [alert(f"{type(e).__name__}: {e}", "block")]))
        run.pending, run.done = None, True
    return {"run": run.id, "shown": shown, "pending": run.pending, "done": run.done,
            "approvals": run.approvals}


def start(gen):
    run = Run(gen)
    with _lock:
        RUNS[run.id] = run
    return advance(run)


def approve(run_id):
    run = RUNS[run_id]
    if run.done:
        return {"run": run.id, "shown": [], "pending": None, "done": True,
                "approvals": run.approvals}
    run.approvals += 1
    return advance(run)


def stop(run_id):
    run = RUNS.pop(run_id, None)
    if run:
        run.gen.close()
    return {"run": run_id, "stopped": True}


# ── 도구를 쓰는 모델 루프 (05·06·07 공용) ─────────────────────────────────


def fn_tool(name, description, prop="query", prop_desc="찾을 내용"):
    return {"type": "function", "name": name, "description": description,
            "parameters": {"type": "object", "properties": {prop: {"type": "string",
                                                                   "description": prop_desc}},
                           "required": [prop], "additionalProperties": False},
            "strict": True}


def tool_loop(agent, instructions, tools, user_input, executors, max_turns=6, result_view=None):
    """모델 호출 → 도구 호출 요청 → (승인) 우리가 실행 → 결과를 붙여 다시 호출.

    executors[name](**args) 는 제너레이터다. 그 안에서 또 ask/show 를 낼 수 있다 —
    서브에이전트가 그렇게 들어간다. 반환값(return)이 도구 결과 문자열이다.
    """
    c = client()
    inputs = [{"role": "user", "content": user_input}]
    for turn in range(1, max_turns + 1):
        yield ask(f"모델 호출 {turn}회차", f"{AGENT_MODEL} 에 지금까지의 대화와 도구 목록을 보낸다.",
                  [code({"instructions": instructions,
                         "tools": [t.get("name", t["type"]) for t in tools],
                         "input 항목 수": len(inputs)}, "보낼 것")], kind="llm", agent=agent)
        r = c.responses.create(model=AGENT_MODEL, instructions=instructions, tools=tools,
                               input=inputs)
        calls = [o for o in r.output if o.type == "function_call"]
        if not calls:
            yield show("최종 답", [answer(r.output_text),
                                   kv([("입력 토큰", r.usage.input_tokens),
                                       ("출력 토큰", r.usage.output_tokens)])], agent=agent)
            return r.output_text
        yield show("모델이 도구를 부르겠다고 했다",
                   [alert("모델은 도구를 직접 실행하지 못한다 — 이름과 인자를 적은 구조체를 냈을 뿐이다.")]
                   + [code({"name": cl.name, "arguments": json.loads(cl.arguments)},
                           f"tool_call · {cl.name}", True) for cl in calls], agent=agent)
        inputs += r.output
        for cl in calls:
            args = json.loads(cl.arguments)
            result = yield from executors[cl.name](**args)
            inputs.append({"type": "function_call_output", "call_id": cl.call_id,
                           "output": result})
    yield show("턴 상한 도달", [alert(f"{max_turns}회 안에 끝나지 않아 멈췄다.", "warn")], agent=agent)
    return "턴 상한에 걸려 답을 마치지 못했다."
