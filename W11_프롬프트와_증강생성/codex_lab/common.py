# -*- coding: utf-8 -*-
"""단계 01~07 이 함께 쓰는 설정.

키는 코드에 적지 않는다. 이 폴더(또는 상위 폴더)의 .env 에서 OPENAI_API_KEY 를 읽는다.
"""
import pathlib
import re
import sys

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"
PDF = DATA / "paju_2040.pdf"
INDEX_DIR = DATA / "index"
LOGS = HERE / "logs"

# 01~03 은 temperature·top_p·logprobs 를 받는 모델이어야 한다.
SAMPLING_MODEL = "gpt-4.1-mini"
# 04~07 — 도구 호출과 에이전트용.
AGENT_MODEL = "gpt-5.4-mini"
EMBED_MODEL = "text-embedding-3-small"

QUESTION = "2040년 파주 도시기본계획의 계획인구는 몇 명인가요?"

# 윈도 터미널(cp949)에서 한글·기호가 깨지지 않게.
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv(find_dotenv(usecwd=True) or (HERE / ".env"))


def client() -> OpenAI:
    return OpenAI()


def clean(text: str) -> str:
    """PDF 에서 뽑은 글자를 다듬는다 — 글머리표가 'Ÿ'·'ž' 로 나오고 빈칸이 많다."""
    text = text.replace("Ÿ", "•").replace("ž", "•")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def need_pdf():
    if not PDF.exists():
        sys.exit("PDF 가 없다. 먼저 `python data/get_paju.py` 를 실행할 것.")


def rule(title: str):
    print("\n" + "─" * 70 + f"\n {title}\n" + "─" * 70)
