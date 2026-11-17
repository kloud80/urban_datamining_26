# -*- coding: utf-8 -*-
"""11주차 실습 웹 앱 — 파주 2040 도시기본계획으로 보는 프롬프트 → RAG → 에이전트 → 하네스.

    uvicorn app:app --port 8000          그리고 브라우저에서 http://127.0.0.1:8000

모든 실험은 한 칸씩 멈추고 [승인]을 기다린다 (labs/runtime.py).
"""
import importlib
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import rag
from common import PDF
from labs import runtime

STEPS = ["s01_call", "s02_sampling", "s03_system", "s04_rag", "s05_tools", "s06_subagents",
         "s07_harness"]
MODS = {m: importlib.import_module(f"labs.{m}") for m in STEPS}
STATIC = pathlib.Path(__file__).parent / "static"

app = FastAPI(title="11주차 codex_lab")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/steps")
def steps():
    return {"steps": [{"id": m, **MODS[m].META, "doc": (MODS[m].__doc__ or "").strip()} for m in STEPS],
            "ready": {"pdf": PDF.exists(), "index": rag.index_exists()}}


@app.post("/api/run/{step}")
def run(step: str, params: dict):
    if step not in MODS:
        raise HTTPException(404, "없는 단계")
    return runtime.start(MODS[step].run(params))


@app.post("/api/approve/{run_id}")
def approve(run_id: str):
    if run_id not in runtime.RUNS:
        raise HTTPException(404, "끝났거나 없는 실행")
    return runtime.approve(run_id)


@app.post("/api/stop/{run_id}")
def stop(run_id: str):
    return runtime.stop(run_id)
