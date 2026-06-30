"""FastAPI 后端 — 为 React 前端提供 AI + PQC 检测 API。"""

from __future__ import annotations

import asyncio
import io
import json
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from data import FEATURE_COLUMNS, dataframe_to_arrays, generate_synthetic_dataset, process_cicids2017
from pqc import KyberVariant
from utils import pipeline_to_response, run_detection_pipeline, stream_detection_pipeline

app = FastAPI(title="AI + PQC Security API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 演示用内存数据集
_store: dict = {"dataset": None}


class GenerateRequest(BaseModel):
    n_samples: int = Field(default=200, ge=50, le=500)


class DetectRequest(BaseModel):
    default_pqc_mode: str = "Kyber512"
    live: bool = False
    delay: float = Field(default=0.05, ge=0.0, le=0.3)


@app.get("/api/health")
def health():
    return {"status": "ok", "message": "AI + PQC 安全监控系统运行中"}


@app.get("/api/dataset/preview")
def preview_dataset(limit: int = 10):
    df = _store.get("dataset")
    if df is None:
        raise HTTPException(status_code=404, detail="请先生成或上传数据集")
    preview = df.head(limit).to_dict(orient="records")
    return {"total": len(df), "preview": preview, "columns": FEATURE_COLUMNS}


@app.post("/api/dataset/generate")
def generate_data(req: GenerateRequest):
    df = generate_synthetic_dataset(n_samples=req.n_samples)
    _store["dataset"] = df
    return {
        "message": f"已生成 {req.n_samples} 条合成网络流量",
        "total": len(df),
        "preview": df.head(10).to_dict(orient="records"),
    }


@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
        if ' Flow Duration' in df.columns or 'Flow Duration' in df.columns:
            df = process_cicids2017(df)
            
        # Sample to 10000 rows max if the dataframe is too large for UI real-time
        if len(df) > 10000:
            df = df.sample(n=10000, random_state=42).reset_index(drop=True)
            
        dataframe_to_arrays(df)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _store["dataset"] = df
    return {
        "message": f"已加载 {len(df)} 条流量数据",
        "total": len(df),
        "preview": df.head(10).to_dict(orient="records"),
    }


@app.post("/api/detect")
def detect(req: DetectRequest):
    df = _store.get("dataset")
    if df is None:
        raise HTTPException(status_code=404, detail="请先生成或上传数据集")

    if req.default_pqc_mode not in KyberVariant._value2member_map_:
        raise HTTPException(status_code=400, detail="无效的 PQC 模式")

    result = run_detection_pipeline(df, default_pqc_mode=req.default_pqc_mode)
    return pipeline_to_response(result)


@app.post("/api/detect/stream")
async def detect_stream(req: DetectRequest):
    df = _store.get("dataset")
    if df is None:
        raise HTTPException(status_code=404, detail="请先生成或上传数据集")

    async def event_stream():
        gen = stream_detection_pipeline(df, default_pqc_mode=req.default_pqc_mode)
        final_result = None
        try:
            while True:
                event = next(gen)
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if req.delay > 0:
                    await asyncio.sleep(req.delay)
        except StopIteration as stop:
            final_result = stop.value

        if final_result:
            payload = {"type": "complete", **pipeline_to_response(final_result)}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
