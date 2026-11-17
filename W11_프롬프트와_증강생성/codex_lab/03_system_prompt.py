# -*- coding: utf-8 -*-
"""03 · system prompt — 역할로 통제하고, 그다음엔 자료를 실어 준다.

    python 03_system_prompt.py

A. system 한 줄만 바꿔서 같은 질문을 보낸다 — 말투와 태도가 바뀐다.
B. "모르면 모른다고 하라" — 지어내기를 줄일 수 있나?
C. 보고서 PDF 5쪽(주요 변경사항 표)을 손으로 잘라 system 에 붙인다 — 이게 RAG 의 원형이다.
   04 단계는 '손으로 자르기'를 '검색'으로 바꾼다.
"""
import pypdf

from common import PDF, QUESTION, SAMPLING_MODEL, clean, client, need_pdf, rule

c = client()


def ask(system, q=QUESTION):
    r = c.chat.completions.create(model=SAMPLING_MODEL, temperature=0, messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": q}])
    return r.choices[0].message.content, r.usage.prompt_tokens


# ── A. 역할 ─────────────────────────────────────────────────────────────
for sp in ["너는 초등학교 1학년이고, 반말로 대답한다.",
           "너는 도시계획 전문 공무원이다. 정중하고 간결하게 답한다."]:
    rule(f"[A] system: {sp}")
    print(ask(sp)[0])

# ── B. 모르면 모른다고 ──────────────────────────────────────────────────
sp = ("너는 도시계획 전문 공무원이다. 확실히 아는 사실만 말하고, "
      "학습 자료에 없거나 확신이 없으면 '모릅니다'라고 답한다.")
rule(f"[B] system: {sp}")
print(ask(sp)[0])
print("\n→ 지시만으로는 지어내기가 잘 안 멈춘다. 모델은 자기가 모른다는 것을 모른다.")

# ── C. 자료를 실어 준다 ─────────────────────────────────────────────────
need_pdf()
page5 = clean(pypdf.PdfReader(str(PDF)).pages[4].extract_text())
sp = ("너는 도시계획 전문 공무원이다. 아래 [자료]에 근거해서만 답하고, "
      "근거가 된 쪽 번호를 밝힌다.\n\n[자료 · 2040년 파주도시기본계획 보고서 PDF 5쪽]\n" + page5)
rule("[C] system: 역할 + 보고서 5쪽 원문")
answer, ntok = ask(sp)
print(answer)
print(f"\n[입력 토큰] {ntok} — 자료 한 쪽을 실었더니 이만큼 늘었다. 721쪽을 다 실을 수 있을까?")
