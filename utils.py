"""检测流水线、异常解释与可视化数据构建。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generator, Optional

import numpy as np
import pandas as pd

from data import FEATURE_COLUMNS, FEATURE_LABELS_ZH
from model import AnomalyResult, train_detector
from pqc import PQCDecision, PQCSimulator


@dataclass
class SampleResult:
    sample_id: int
    duration: float
    packet_count: int
    byte_size: int
    src_bytes: int
    dst_bytes: int
    flow_rate: float
    label: str
    status: str
    risk: float
    score: float
    pqc_action: str
    algorithm: str
    explanation: str
    switched: bool = False
    renegotiated: bool = False


@dataclass
class PipelineResult:
    rows: list[SampleResult] = field(default_factory=list)
    logs: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    scores: list[float] = field(default_factory=list)
    labels: list[int] = field(default_factory=list)


def build_log(level: str, message: str, sample_id: Optional[int] = None) -> dict:
    return {"level": level, "message": message, "sample_id": sample_id}


def explain_anomaly(row: pd.Series, medians: pd.Series, status: str) -> str:
    if status == "NORMAL":
        return (
            "该流量各特征值处于正常区间，Isolation Forest 未检测到显著偏离，"
            "维持 Kyber512 标准后量子加密模式。"
        )

    reasons = []
    for col in FEATURE_COLUMNS:
        val = float(row[col])
        med = float(medians[col])
        if med == 0:
            ratio = val
        else:
            ratio = val / med
        if ratio > 2.5:
            reasons.append(
                f"{FEATURE_LABELS_ZH[col]}({val:.1f}) 显著高于中位数({med:.1f})"
            )
        elif ratio < 0.4 and val > 0:
            reasons.append(
                f"{FEATURE_LABELS_ZH[col]}({val:.1f}) 显著低于中位数({med:.1f})"
            )

    if not reasons:
        reasons.append("综合特征组合偏离正常流量分布（Isolation Forest 低分）")

    return "异常原因：" + "；".join(reasons[:3]) + "。已触发 Kyber768 升级与密钥重协商。"


def run_detection_pipeline(
    df: pd.DataFrame,
    default_pqc_mode: str = "Kyber512",
    random_state: int = 42,
) -> PipelineResult:
    X = df[FEATURE_COLUMNS].values.astype(float)
    y = df["label"].values if "label" in df.columns else None
    medians = df[FEATURE_COLUMNS].median()

    detector, metrics = train_detector(X, y, random_state=random_state)
    predictions = detector.predict_with_scores(X)
    pqc = PQCSimulator(default_mode=default_pqc_mode)

    result = PipelineResult(metrics=metrics)
    result.scores = detector.score_samples(X).tolist()
    result.labels = detector.predict(X).tolist()

    for idx, pred in enumerate(predictions):
        row = df.iloc[idx]
        is_anomaly = pred.label == -1
        decision = pqc.process_sample(idx, is_anomaly)
        sample = _build_sample(idx, row, pred, decision, medians)
        result.rows.append(sample)
        result.logs.extend(_sample_logs(sample, decision))

    anomaly_count = sum(1 for r in result.rows if r.status == "ANOMALY")
    result.summary = {
        "total": len(result.rows),
        "normal": len(result.rows) - anomaly_count,
        "anomalies": anomaly_count,
        "renegotiations": pqc.state.renegotiation_count,
        "final_algorithm": pqc.current_algorithm,
        "system_status": "alert" if anomaly_count > 0 else "secure",
    }
    return result


def stream_detection_pipeline(
    df: pd.DataFrame,
    default_pqc_mode: str = "Kyber512",
    random_state: int = 42,
) -> Generator[dict[str, Any], None, PipelineResult]:
    """逐条产出检测事件，供 SSE 实时推送。"""
    X = df[FEATURE_COLUMNS].values.astype(float)
    y = df["label"].values if "label" in df.columns else None
    medians = df[FEATURE_COLUMNS].median()

    detector, metrics = train_detector(X, y, random_state=random_state)
    predictions = detector.predict_with_scores(X)
    pqc = PQCSimulator(default_mode=default_pqc_mode)

    result = PipelineResult(metrics=metrics)
    result.scores = detector.score_samples(X).tolist()
    result.labels = detector.predict(X).tolist()

    yield {"type": "init", "total": len(predictions), "metrics": metrics}

    for idx, pred in enumerate(predictions):
        row = df.iloc[idx]
        decision = pqc.process_sample(idx, pred.label == -1)
        sample = _build_sample(idx, row, pred, decision, medians)
        logs = _sample_logs(sample, decision)
        result.rows.append(sample)
        result.logs.extend(logs)
        yield {
            "type": "sample",
            "sample": sample_to_dict(sample),
            "logs": logs,
            "progress": (idx + 1) / len(predictions),
            "pqc_mode": pqc.current_algorithm,
            "renegotiations": pqc.state.renegotiation_count,
        }

    anomaly_count = sum(1 for r in result.rows if r.status == "ANOMALY")
    result.summary = {
        "total": len(result.rows),
        "normal": len(result.rows) - anomaly_count,
        "anomalies": anomaly_count,
        "renegotiations": pqc.state.renegotiation_count,
        "final_algorithm": pqc.current_algorithm,
        "system_status": "alert" if anomaly_count > 0 else "secure",
    }
    return result


def _build_sample(
    idx: int,
    row: pd.Series,
    pred: AnomalyResult,
    decision: PQCDecision,
    medians: pd.Series,
) -> SampleResult:
    gt = row.get("label", pred.label)
    label_zh = "异常" if (gt == -1 or pred.label == -1) else "正常"
    if pred.label == -1:
        label_zh = "异常"
    elif pred.label == 1:
        label_zh = "正常"

    return SampleResult(
        sample_id=idx,
        duration=float(row["duration"]),
        packet_count=int(row["packet_count"]),
        byte_size=int(row["byte_size"]),
        src_bytes=int(row["src_bytes"]),
        dst_bytes=int(row["dst_bytes"]),
        flow_rate=float(row["flow_rate"]),
        label=label_zh,
        status=decision.status,
        risk=round(pred.risk, 2),
        score=round(pred.score, 4),
        pqc_action=decision.pqc_action,
        algorithm=decision.algorithm,
        explanation=explain_anomaly(row, medians, decision.status),
        switched=decision.switched,
        renegotiated=decision.renegotiated,
    )


def _sample_logs(sample: SampleResult, decision: PQCDecision) -> list[dict]:
    logs: list[dict] = []
    if sample.status == "ANOMALY":
        logs.append(
            build_log(
                "warning",
                f"流量 {sample.sample_id} → 触发 Kyber768 切换",
                sample.sample_id,
            )
        )
        logs.append(build_log("system", "已触发密钥重新协商", sample.sample_id))
    else:
        logs.append(
            build_log(
                "info",
                f"流量 {sample.sample_id} → 使用 Kyber512",
                sample.sample_id,
            )
        )
    return logs


def sample_to_dict(sample: SampleResult) -> dict:
    return {
        "sample_id": sample.sample_id,
        "duration": sample.duration,
        "packet_count": sample.packet_count,
        "byte_size": sample.byte_size,
        "src_bytes": sample.src_bytes,
        "dst_bytes": sample.dst_bytes,
        "flow_rate": sample.flow_rate,
        "label": sample.label,
        "status": sample.status,
        "risk": sample.risk,
        "score": sample.score,
        "pqc_action": sample.pqc_action,
        "algorithm": sample.algorithm,
        "explanation": sample.explanation,
        "switched": sample.switched,
        "renegotiated": sample.renegotiated,
    }


def pipeline_to_response(result: PipelineResult) -> dict:
    return {
        "rows": [sample_to_dict(r) for r in result.rows],
        "logs": result.logs,
        "metrics": result.metrics,
        "summary": result.summary,
        "scores": result.scores,
        "labels": result.labels,
    }
