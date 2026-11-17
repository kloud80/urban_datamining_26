# -*- coding: utf-8 -*-
"""파주 보고서 → 벡터 인덱스. 04~07 이 함께 쓴다.

처음 한 번만 임베딩하고 data/index/ 에 저장한다. 다음부터는 불러오기만 한다
(글자가 있는 약 680쪽 → 조각 약 1,500개, text-embedding-3-small 로 몇십 원·1~2분).
쪽 번호는 PDF 뷰어 기준(1부터)이다 — 보고서 본문에 찍힌 쪽 번호와는 12쪽쯤 다르다.
"""
import re

import pypdf
from llama_index.core import (Document, QueryBundle, Settings, StorageContext, VectorStoreIndex,
                              load_index_from_storage)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI

from common import EMBED_MODEL, INDEX_DIR, PDF, SAMPLING_MODEL, clean, need_pdf

Settings.embed_model = OpenAIEmbedding(model=EMBED_MODEL)
Settings.llm = LlamaOpenAI(model=SAMPLING_MODEL, temperature=0)
CHUNK, OVERLAP = 512, 64
_INDEX = None


def page_text(i: int) -> str:
    """i 쪽(1부터)의 글자를 다듬어 돌려준다."""
    need_pdf()
    t = clean(pypdf.PdfReader(str(PDF)).pages[i - 1].extract_text() or "")
    # 모든 쪽 머리에 '2040년 파주도시기본계획 - 37 -' 이 찍혀 있다. 그대로 두면 짧은
    # 질문이 들어왔을 때 이 머리글끼리 닮았다고 엉뚱한 쪽을 가져온다(실제로 겪었다).
    t = re.sub(r"^\s*2040년 파주도시기본계획\s*(-\s*\d+\s*-)?\s*", "", t)
    return re.sub(r"^\s*-\s*\d+\s*-\s*", "", t)


def load_pages():
    need_pdf()
    n = len(pypdf.PdfReader(str(PDF)).pages)
    docs = []
    for i in range(1, n + 1):
        t = page_text(i)
        if len(t) < 50:            # 도면·간지 — 글자가 거의 없다
            continue
        docs.append(Document(text=t, metadata={"page": i, "source": "2040 파주도시기본계획"},
                             excluded_embed_metadata_keys=["source"]))
    return docs


def index_exists() -> bool:
    return (INDEX_DIR / "docstore.json").exists()


def get_index(rebuild=False):
    global _INDEX
    if _INDEX is not None and not rebuild:
        return _INDEX
    if index_exists() and not rebuild:
        _INDEX = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(INDEX_DIR)))
        return _INDEX
    docs = load_pages()
    _INDEX = VectorStoreIndex.from_documents(
        docs, transformations=[SentenceSplitter(chunk_size=CHUNK, chunk_overlap=OVERLAP)])
    _INDEX.storage_context.persist(persist_dir=str(INDEX_DIR))
    return _INDEX


def stats():
    idx = get_index()
    nodes = list(idx.docstore.docs.values())
    pages = {n.metadata.get("page") for n in nodes}
    sample = next((n for n in nodes if n.metadata.get("page") == 107), nodes[0])
    return {"pages": len(pages), "chunks": len(nodes), "sample": sample}


def embed(q: str):
    return Settings.embed_model.get_query_embedding(q)


def retrieve(q: str, vec=None, k: int = 5):
    bundle = QueryBundle(query_str=q, embedding=vec) if vec is not None else q
    return get_index().as_retriever(similarity_top_k=k).retrieve(bundle)


def search(query: str, k: int = 5) -> str:
    """질문과 가까운 조각 k 개를 '[p.쪽] 본문' 꼴로 — 도구가 모델에게 돌려줄 문자열."""
    nodes = retrieve(query, k=k)
    if not nodes:
        return "검색 결과 없음 — 질문을 바꿔 다시 찾을 것."
    return "\n\n".join(f"[p.{n.metadata['page']} · 유사도 {n.score:.2f}]\n{n.get_content()}"
                       for n in nodes)
