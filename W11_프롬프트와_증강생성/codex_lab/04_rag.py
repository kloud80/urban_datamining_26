# -*- coding: utf-8 -*-
"""04 · RAG — 721쪽 보고서를 벡터로 바꿔 두고, 질문과 가까운 조각만 골라 싣는다.

    python 04_rag.py                       기본 질문
    python 04_rag.py "운정·교하는 어떤 중심지인가?"
    python 04_rag.py --rebuild             인덱스를 처음부터 다시 만든다

03 의 [C] 에서 '손으로 5쪽을 잘라 붙인 것'을 '검색'으로 바꾼 것뿐이다.
  1) 검색   질문 → 임베딩 → 가까운 조각 5개 (llama_index retriever)
  2) 증강   그 조각을 프롬프트에 싣는다
  3) 생성   모델이 그 안에서 답한다
"""
import sys

from common import QUESTION, rule
from rag import get_index

args = [a for a in sys.argv[1:] if not a.startswith("--")]
q = args[0] if args else QUESTION
index = get_index(rebuild="--rebuild" in sys.argv)

engine = index.as_query_engine(similarity_top_k=5)
res = engine.query(q + "\n(근거가 된 쪽 번호를 함께 밝혀 답할 것)")

rule("1) 검색된 조각 — 이것이 모델에게 실린 '자료'다")
for n in res.source_nodes:
    head = n.get_content()[:90].replace("\n", " ")
    print(f"  p.{n.metadata['page']:>3}  유사도 {n.score:.3f}  {head}…")

rule(f"2·3) 답  —  Q. {q}")
print(res.response)
