"""Pipeline orchestration, logging, and visualization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from model import AnomalyResult, FlowAnomalyDetector, train_detector
from pqc import PQCDecision, PQCSimulator


@dataclass
class SampleResult:
    sample_id: int
    status: str
    risk: float
    raw_score: float
    pqc_action: str
    algorithm: str


@dataclass
class PipelineResult:
    rows: list[SampleResult] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    scores: np.ndarray = field(default_factory=lambda: np.array([]))
    labels: np.ndarray = field(default_factory=lambda: np.array([]))


def build_log_entry(level: str, message: str) -> str:
    return f"[{level}] {message}"


def run_detection_pipeline(
    X: np.ndarray,
    y: Optional[np.ndarray] = None,
    random_state: int = 42,
    live_callback: Optional[Callable[[SampleResult, list[str]], None]] = None,
) -> PipelineResult:
    """
    Run Isolation Forest + PQC integration.

    Optionally invoke live_callback after each sample for animated UI updates.
    """
    detector, metrics = train_detector(X, y, random_state=random_state)
    predictions = detector.predict_with_scores(X)
    pqc = PQCSimulator()

    result = PipelineResult(metrics=metrics)
    result.scores = detector.score_samples(X)
    result.labels = detector.predict(X)

    for idx, pred in enumerate(predictions):
        is_anomaly = pred.label == -1
        decision = pqc.process_sample(idx, is_anomaly)
        sample = _build_sample_result(idx, pred, decision)
        result.rows.append(sample)

        batch_logs = _build_sample_logs(sample, decision)
        result.logs.extend(batch_logs)

        if live_callback:
            live_callback(sample, batch_logs)

    anomaly_count = sum(1 for r in result.rows if r.status == "ANOMALY")
    result.summary = {
        "total": len(result.rows),
        "anomalies": anomaly_count,
        "normal": len(result.rows) - anomaly_count,
        "renegotiations": pqc.state.renegotiation_count,
        "final_algorithm": pqc.current_algorithm,
    }
    return result


def _build_sample_result(
    idx: int,
    pred: AnomalyResult,
    decision: PQCDecision,
) -> SampleResult:
    return SampleResult(
        sample_id=idx,
        status=decision.status,
        risk=pred.risk,
        raw_score=pred.score,
        pqc_action=decision.pqc_action,
        algorithm=decision.algorithm,
    )


def _build_sample_logs(sample: SampleResult, decision: PQCDecision) -> list[str]:
    logs: list[str] = []
    if sample.status == "ANOMALY":
        logs.append(
            build_log_entry(
                "WARNING",
                f"Sample {sample.sample_id} → ANOMALY → Switching to Kyber768",
            )
        )
        logs.append(build_log_entry("INFO", "Key renegotiation triggered"))
    else:
        logs.append(
            build_log_entry(
                "INFO",
                f"Sample {sample.sample_id} → NORMAL → Kyber512",
            )
        )
    return logs


def results_to_dataframe(rows: list[SampleResult]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Sample ID": r.sample_id,
                "Status": r.status,
                "Risk": round(r.risk, 2),
                "PQC Action": r.pqc_action,
            }
            for r in rows
        ]
    )


def styled_results_table(df: pd.DataFrame):
    """Return a pandas Styler with green/red row highlighting."""

    def _row_style(row):
        if row["Status"] == "ANOMALY":
            return [
                "background-color: #fdecea; color: #922b21; font-weight: 600"
            ] * len(row)
        return [
            "background-color: #eafaf1; color: #1e8449; font-weight: 500"
        ] * len(row)

    return df.style.apply(_row_style, axis=1)


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
