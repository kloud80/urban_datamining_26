# -*- coding: utf-8 -*-
"""04 · RAG — 단계마다 멈추고 승인을 받는다.

  ① 문서 → 조각      721쪽을 512토큰 조각으로 (저장된 인덱스를 불러온다. 없으면 만든다)
  ② 질문 → 벡터      질문을 1536차원 숫자 배열로
  ③ 검색            질문 벡터와 가장 가까운 조각 k개 (코사인 유사도)
  ④ 프롬프트 조립    그 조각들을 system 에 싣는다 — 03 에서 손으로 하던 일
  ⑤ 생성            모델이 그 안에서 답한다

03 의 [보고서 5쪽 싣기]를 '검색'으로 바꾼 것뿐이다. 단, 검색이 틀리면 답도 틀린다 —
③ 에서 어떤 쪽이 올라왔는지를 꼭 볼 것.
"""
import rag
from common import EMBED_MODEL, QUESTION, SAMPLING_MODEL, client
from labs.runtime import alert, answer, ask, chunks, code, kv, messages, show, text

META = {
    "no": "04", "title": "RAG · llama_index", "sub": "721쪽을 벡터로 — 검색해서 싣고 답한다",
    "fields": [
        {"name": "question", "label": "질문", "type": "textarea", "default": QUESTION},
        {"name": "k", "label": "가져올 조각 수 (top-k)", "type": "range", "min": 1, "max": 10,
         "step": 1, "default": 5},
    ],
}


def run(p):
    q, k = p["question"], int(p["k"])

    # ① 문서 → 조각
    if rag.index_exists():
        yield ask("① 인덱스 불러오기", "data/index/ 에 저장해 둔 조각·벡터를 읽는다 (비용 없음).",
                  kind="local")
    else:
        yield ask("① 인덱스 만들기", "글자가 있는 PDF 약 680쪽을 512토큰 조각으로 자르고 전부 임베딩한다. "
                  "처음 한 번만 — 1~2분, 몇십 원.", kind="cost")
    s = rag.stats()
    smp = s["sample"]
    yield show("① 문서 → 조각", [
        kv([("글자가 있는 쪽", s["pages"]), ("조각 수", f"{s['chunks']:,}"),
            ("조각 크기", f"{rag.CHUNK} 토큰 (겹침 {rag.OVERLAP})"), ("임베딩 모델", EMBED_MODEL)]),
        text(f"조각 하나의 예 — p.{smp.metadata['page']}"),
        chunks([{"page": smp.metadata["page"], "score": None, "text": smp.get_content()}])])

    # ② 질문 → 벡터
    yield ask("② 질문을 벡터로", f"“{q}” 를 {EMBED_MODEL} 로 임베딩한다 (아주 싼 호출).")
    vec = rag.embed(q)
    yield show("② 질문 → 벡터", [
        {"type": "vector", "values": vec[:160], "dims": len(vec)},
        alert(f"질문 한 줄이 숫자 {len(vec):,}개가 됐다. 조각 {s['chunks']:,}개도 모두 이런 벡터로 저장돼 있다.")])

    # ③ 검색
    yield ask("③ 가까운 조각 찾기", f"질문 벡터와 코사인 유사도가 가장 높은 조각 {k}개를 고른다 (내 컴퓨터 안).",
              kind="local")
    nodes = rag.retrieve(q, vec=vec, k=k)
    found = sorted({n.metadata["page"] for n in nodes})
    yield show(f"③ 검색 결과 — {k}개 조각 (쪽: {', '.join(map(str, found))})", [
        chunks([{"page": n.metadata["page"], "score": round(n.score, 3), "text": n.get_content()}
                for n in nodes]),
        alert("정답이 적힌 쪽(5·107·132·590 등)이 올라왔는가? 검색이 틀리면 생성도 틀린다.", "warn")])

    # ④ 프롬프트 조립
    yield ask("④ 프롬프트 조립", "검색된 조각을 [자료]로 묶어 system 에 싣는다 (비용 없음).", kind="local")
    ctx = "\n\n".join(f"[p.{n.metadata['page']}]\n{n.get_content()}" for n in nodes)
    system = ("너는 도시계획 리서치 조수다. 아래 [자료]에 있는 내용만으로 답하고, 문장마다 근거 쪽 번호를 "
              "(p.N) 꼴로 붙인다. [자료]에 없으면 '자료에서 찾지 못함'이라고 답한다.\n\n[자료]\n" + ctx)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": q}]
    yield show("④ 모델에게 갈 프롬프트", [messages(msgs),
                                         kv([("system 길이", f"{len(system):,}자"),
                                             ("보고서 전체 대비", f"{len(ctx) / 1_000_000:.2%} 남짓")])])

    # ⑤ 생성
    yield ask("⑤ 답 생성", f"{SAMPLING_MODEL} 에 위 프롬프트를 보낸다 (temperature=0).",
              [code({"model": SAMPLING_MODEL, "temperature": 0, "messages": "(④의 메시지)"}, "요청")])
    r = client().chat.completions.create(model=SAMPLING_MODEL, temperature=0, messages=msgs)
    yield show("⑤ 답", [answer(r.choices[0].message.content),
                        kv([("입력 토큰", r.usage.prompt_tokens), ("출력 토큰", r.usage.completion_tokens)])])
