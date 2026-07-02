"""Pipeline orchestration, risk policy, logging, and visualization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from model import (
    AnomalyResult,
    Contamination,
    FlowAnomalyDetector,
    evaluate_predictions,
    train_detector,
)
from pqc import PQCSimulator


@dataclass
class SampleResult:
    sample_id: int
    status: str
    risk_level: str
    risk: float
    raw_score: float
    pqc_action: str
    algorithm: str
    response_triggered: bool
    trigger_reason: str


@dataclass
class PipelineResult:
    rows: list[SampleResult] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    scores: np.ndarray = field(default_factory=lambda: np.array([]))
    labels: np.ndarray = field(default_factory=lambda: np.array([]))


@dataclass
class RiskPolicyState:
    medium_streak: int = 0
    direct_renegotiations: int = 0
    streak_renegotiations: int = 0


def build_log_entry(level: str, message: str) -> str:
    return f"[{level}] {message}"


def run_detection_pipeline(
    X_train: np.ndarray,
    X_test: Optional[np.ndarray] = None,
    y_test: Optional[np.ndarray] = None,
    random_state: int = 42,
    contamination: Contamination = 0.1,
    detector: Optional[FlowAnomalyDetector] = None,
    language: str = "en",
    risk_policy_mode: str = "manual",
    low_threshold: float = 0.45,
    high_threshold: float = 0.75,
    medium_streak_n: int = 3,
    live_callback: Optional[Callable[[SampleResult, list[str]], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> PipelineResult:
    """
    Run Isolation Forest + simulated PQC response.

    risk_policy_mode:
        "auto" uses Isolation Forest's internal contamination-derived threshold.
        "manual" uses low/high risk thresholds and the medium-streak rule.
    """
    if X_test is None:
        X_test = X_train

    if detector is None:
        detector, _ = train_detector(
            X_train,
            random_state=random_state,
            contamination=contamination,
        )

    predictions = detector.predict_with_scores(X_test)
    pqc = PQCSimulator()
    policy_state = RiskPolicyState()
    policy_labels: list[int] = []
    processed_scores: list[float] = []
    result = PipelineResult()

    for idx, pred in enumerate(predictions):
        if should_stop is not None and should_stop():
            result.logs.append(build_log_entry("INFO", _log_text(language, "stopped")))
            break

        sample, batch_logs, policy_label = build_policy_sample(
            idx,
            pred,
            pqc,
            policy_state,
            risk_policy_mode=risk_policy_mode,
            low_threshold=low_threshold,
            high_threshold=high_threshold,
            medium_streak_n=medium_streak_n,
            language=language,
        )
        result.rows.append(sample)
        result.logs.extend(batch_logs)
        policy_labels.append(policy_label)
        processed_scores.append(pred.score)

        if live_callback:
            live_callback(sample, batch_logs)

    risk_counts = _risk_counts(result.rows)
    anomaly_count = sum(1 for r in result.rows if r.status == "ANOMALY")
    result.scores = np.array(processed_scores)
    result.labels = np.array(policy_labels)
    if y_test is not None and len(policy_labels) > 0:
        result.metrics = evaluate_predictions(y_test[: len(policy_labels)], result.labels)

    result.summary = {
        "total": len(result.rows),
        "anomalies": anomaly_count,
        "normal": len(result.rows) - anomaly_count,
        "low_risk": risk_counts["LOW"],
        "medium_risk": risk_counts["MEDIUM"],
        "high_risk": risk_counts["HIGH"],
        "renegotiations": pqc.state.renegotiation_count,
        "direct_renegotiations": policy_state.direct_renegotiations,
        "streak_renegotiations": policy_state.streak_renegotiations,
        "final_algorithm": pqc.current_algorithm,
        "stopped": len(result.rows) < len(predictions),
        "configured_total": len(predictions),
        "risk_policy_mode": risk_policy_mode,
    }
    return result


def build_policy_sample(
    idx: int,
    pred: AnomalyResult,
    pqc: PQCSimulator,
    policy_state: RiskPolicyState,
    risk_policy_mode: str,
    low_threshold: float,
    high_threshold: float,
    medium_streak_n: int,
    language: str = "en",
) -> tuple[SampleResult, list[str], int]:
    if risk_policy_mode == "auto":
        return _build_auto_policy_sample(idx, pred, pqc, policy_state, language)

    risk_level = classify_risk(pred.risk, low_threshold, high_threshold)
    response_triggered = False
    trigger_reason = "pass"

    if risk_level == "LOW":
        policy_state.medium_streak = 0
        pqc.switch_to_kyber512()
        pqc_action = "Pass"
    elif risk_level == "MEDIUM":
        policy_state.medium_streak += 1
        if policy_state.medium_streak >= medium_streak_n:
            pqc.switch_to_kyber768()
            pqc.renegotiate_key()
            policy_state.streak_renegotiations += 1
            response_triggered = True
            trigger_reason = "medium_streak"
            pqc_action = "Kyber768 simulated renegotiation"
            policy_state.medium_streak = 0
        else:
            pqc.switch_to_kyber512()
            trigger_reason = "medium_monitor"
            pqc_action = "Monitor"
    else:
        policy_state.medium_streak = 0
        pqc.switch_to_kyber768()
        pqc.renegotiate_key()
        policy_state.direct_renegotiations += 1
        response_triggered = True
        trigger_reason = "high_risk"
        pqc_action = "Kyber768 simulated renegotiation"

    status = "ANOMALY" if response_triggered else "NORMAL"
    sample = _build_sample_result(
        idx,
        pred,
        risk_level=risk_level,
        status=status,
        pqc_action=pqc_action,
        algorithm=pqc.current_algorithm,
        response_triggered=response_triggered,
        trigger_reason=trigger_reason,
    )
    return sample, _build_sample_logs(sample, language, medium_streak_n), -1 if response_triggered else 1


def _build_auto_policy_sample(
    idx: int,
    pred: AnomalyResult,
    pqc: PQCSimulator,
    policy_state: RiskPolicyState,
    language: str,
) -> tuple[SampleResult, list[str], int]:
    policy_state.medium_streak = 0
    if pred.label == -1:
        pqc.switch_to_kyber768()
        pqc.renegotiate_key()
        policy_state.direct_renegotiations += 1
        sample = _build_sample_result(
            idx,
            pred,
            risk_level="MODEL_ANOMALY",
            status="ANOMALY",
            pqc_action="Kyber768 simulated renegotiation",
            algorithm=pqc.current_algorithm,
            response_triggered=True,
            trigger_reason="model_anomaly",
        )
        return sample, _build_sample_logs(sample, language), -1

    pqc.switch_to_kyber512()
    sample = _build_sample_result(
        idx,
        pred,
        risk_level="MODEL_NORMAL",
        status="NORMAL",
        pqc_action="Pass",
        algorithm=pqc.current_algorithm,
        response_triggered=False,
        trigger_reason="model_normal",
    )
    return sample, _build_sample_logs(sample, language), 1


def classify_risk(risk: float, low_threshold: float, high_threshold: float) -> str:
    if risk < low_threshold:
        return "LOW"
    if risk < high_threshold:
        return "MEDIUM"
    return "HIGH"


def _build_sample_result(
    idx: int,
    pred: AnomalyResult,
    risk_level: str,
    status: str,
    pqc_action: str,
    algorithm: str,
    response_triggered: bool,
    trigger_reason: str,
) -> SampleResult:
    return SampleResult(
        sample_id=idx,
        status=status,
        risk_level=risk_level,
        risk=pred.risk,
        raw_score=pred.score,
        pqc_action=pqc_action,
        algorithm=algorithm,
        response_triggered=response_triggered,
        trigger_reason=trigger_reason,
    )


def _build_sample_logs(
    sample: SampleResult,
    language: str = "en",
    medium_streak_n: int = 3,
) -> list[str]:
    if sample.trigger_reason == "model_anomaly":
        return [
            build_log_entry("WARNING", _log_text(language, "model_anomaly", sample.sample_id)),
            build_log_entry("INFO", _log_text(language, "renegotiation")),
        ]
    if sample.trigger_reason == "model_normal":
        return [build_log_entry("INFO", _log_text(language, "model_normal", sample.sample_id))]
    if sample.trigger_reason == "high_risk":
        return [
            build_log_entry("WARNING", _log_text(language, "high", sample.sample_id)),
            build_log_entry("INFO", _log_text(language, "renegotiation")),
        ]
    if sample.trigger_reason == "medium_streak":
        return [
            build_log_entry(
                "WARNING",
                _log_text(language, "medium_trigger", sample.sample_id, medium_streak_n),
            ),
            build_log_entry("INFO", _log_text(language, "renegotiation")),
        ]
    if sample.trigger_reason == "medium_monitor":
        return [
            build_log_entry(
                "INFO",
                _log_text(language, "medium_monitor", sample.sample_id, medium_streak_n),
            )
        ]
    return [build_log_entry("INFO", _log_text(language, "low", sample.sample_id))]


def _log_text(
    language: str,
    key: str,
    sample_id: int | None = None,
    medium_streak_n: int = 3,
) -> str:
    zh = language == "zh"
    if key == "stopped":
        return "用户已中止检测" if zh else "Detection stopped by user"
    if key == "renegotiation":
        return "已触发模拟密钥重协商" if zh else "Simulated key renegotiation triggered"
    if key == "model_anomaly":
        return (
            f"样本 {sample_id} -> 模型判定异常 -> 模拟重协商"
            if zh
            else f"Sample {sample_id} -> model anomaly -> simulated renegotiation"
        )
    if key == "model_normal":
        return (
            f"样本 {sample_id} -> 模型判定正常 -> 通过"
            if zh
            else f"Sample {sample_id} -> model normal -> pass"
        )
    if key == "high":
        return (
            f"样本 {sample_id} -> 高风险 -> 立即模拟重协商"
            if zh
            else f"Sample {sample_id} -> HIGH risk -> immediate simulated renegotiation"
        )
    if key == "medium_trigger":
        return (
            f"样本 {sample_id} -> 中风险连续 {medium_streak_n} 次 -> 模拟重协商"
            if zh
            else f"Sample {sample_id} -> MEDIUM risk streak {medium_streak_n}/{medium_streak_n} -> simulated renegotiation"
        )
    if key == "medium_monitor":
        return (
            f"样本 {sample_id} -> 中风险 -> 持续监测"
            if zh
            else f"Sample {sample_id} -> MEDIUM risk -> monitor"
        )
    return f"样本 {sample_id} -> 低风险 -> 通过" if zh else f"Sample {sample_id} -> LOW risk -> pass"


def _risk_counts(rows: list[SampleResult]) -> dict[str, int]:
    return {
        "LOW": sum(1 for row in rows if row.risk_level in {"LOW", "MODEL_NORMAL"}),
        "MEDIUM": sum(1 for row in rows if row.risk_level == "MEDIUM"),
        "HIGH": sum(1 for row in rows if row.risk_level in {"HIGH", "MODEL_ANOMALY"}),
    }


def results_to_dataframe(rows: list[SampleResult], language: str = "en") -> pd.DataFrame:
    labels = {
        "sample_id": "样本 ID" if language == "zh" else "Sample ID",
        "status": "状态" if language == "zh" else "Status",
        "risk_level": "风险等级" if language == "zh" else "Risk Level",
        "risk": "风险" if language == "zh" else "Risk",
        "pqc_action": "PQC 动作" if language == "zh" else "PQC Action",
    }
    return pd.DataFrame(
        [
            {
                labels["sample_id"]: r.sample_id,
                labels["status"]: _display_status(r.status, language),
                labels["risk_level"]: _display_risk_level(r.risk_level, language),
                labels["risk"]: round(r.risk, 2),
                labels["pqc_action"]: r.pqc_action,
            }
            for r in rows
        ]
    )


def styled_results_table(df: pd.DataFrame, language: str = "en"):
    """Return a pandas Styler with green/red row highlighting."""
    status_col = "状态" if language == "zh" else "Status"

    def _row_style(row):
        if row[status_col] in {"ANOMALY", "异常"}:
            return [
                "background-color: #fdecea; color: #922b21; font-weight: 600"
            ] * len(row)
        return [
            "background-color: #eafaf1; color: #1e8449; font-weight: 500"
        ] * len(row)

    return df.style.apply(_row_style, axis=1)


def _display_status(status: str, language: str) -> str:
    if language != "zh":
        return status
    return "异常" if status == "ANOMALY" else "正常"


def _display_risk_level(risk_level: str, language: str) -> str:
    if language != "zh":
        return risk_level
    mapping = {
        "LOW": "低",
        "MEDIUM": "中",
        "HIGH": "高",
        "MODEL_NORMAL": "模型正常",
        "MODEL_ANOMALY": "模型异常",
    }
    return mapping.get(risk_level, risk_level)


def create_anomaly_score_figure(scores: np.ndarray, labels: np.ndarray) -> go.Figure:
    colors = ["#e74c3c" if lbl == -1 else "#27ae60" for lbl in labels]
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(range(len(scores))),
                y=scores,
                marker_color=colors,
                name="Anomaly score",
            )
        ]
    )
    fig.add_hline(
        y=float(np.median(scores)),
        line_dash="dash",
        line_color="#2980b9",
        annotation_text="Median",
    )
    fig.update_layout(
        title="Anomaly Scores per Network Flow",
        xaxis_title="Sample Index",
        yaxis_title="Isolation Forest Score",
        template="plotly_white",
        height=360,
        margin=dict(l=40, r=20, t=50, b=40),
        showlegend=False,
    )
    return fig


def create_status_count_figure(normal: int, anomaly: int) -> go.Figure:
    fig = px.bar(
        x=["Normal", "Anomaly"],
        y=[normal, anomaly],
        color=["Normal", "Anomaly"],
        color_discrete_map={"Normal": "#27ae60", "Anomaly": "#e74c3c"},
        text=[normal, anomaly],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        title="Traffic Classification Summary",
        yaxis_title="Count",
        template="plotly_white",
        height=360,
        showlegend=False,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def format_log_html(logs: list[str]) -> str:
    """Render event logs with color-coded levels."""
    lines = []
    for entry in logs:
        if "[WARNING]" in entry:
            color = "#c0392b"
            bg = "#fdf2f2"
        elif "[INFO]" in entry:
            color = "#1f618d"
            bg = "#f4f9fd"
        else:
            color = "#566573"
            bg = "#f8f9fa"
        lines.append(
            f'<div style="padding:6px 10px;margin:4px 0;border-radius:6px;'
            f'background:{bg};color:{color};font-family:monospace;font-size:13px;">'
            f"{entry}</div>"
        )
    return "".join(lines)
