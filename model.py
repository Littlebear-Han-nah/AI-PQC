"""Isolation Forest 网络流量异常检测模块。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix


@dataclass
class AnomalyResult:
    label: int
    score: float
    risk: float


class FlowAnomalyDetector:
    def __init__(
        self,
        contamination: float = 0.1,
        random_state: int = 42,
        n_estimators: int = 100,
    ) -> None:
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self._fitted = False

    def fit(self, X: np.ndarray) -> "FlowAnomalyDetector":
        self.model.fit(X)
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("模型尚未训练")
        return self.model.predict(X)

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("模型尚未训练")
        return self.model.score_samples(X)

    @staticmethod
    def scores_to_risk(scores: np.ndarray) -> np.ndarray:
        inverted = -scores
        lo, hi = inverted.min(), inverted.max()
        if hi == lo:
            return np.full(len(scores), 0.5)
        return (inverted - lo) / (hi - lo)

    def predict_with_scores(self, X: np.ndarray) -> list[AnomalyResult]:
        labels = self.predict(X)
        scores = self.score_samples(X)
        risks = self.scores_to_risk(scores)
        return [
            AnomalyResult(label=int(lbl), score=float(scr), risk=float(rsk))
            for lbl, scr, rsk in zip(labels, scores, risks)
        ]


def train_detector(
    X: np.ndarray,
    y: Optional[np.ndarray] = None,
    random_state: int = 42,
) -> tuple[FlowAnomalyDetector, dict]:
    detector = FlowAnomalyDetector(random_state=random_state)
    detector.fit(X)
    metrics: dict = {}
    if y is not None:
        y_pred = detector.predict(X)
        metrics = {
            "confusion_matrix": confusion_matrix(y, y_pred).tolist(),
            "classification_report": classification_report(
                y, y_pred, target_names=["anomaly", "normal"], zero_division=0
            ),
            "accuracy": float(np.mean(y == y_pred)),
        }
    return detector, metrics
