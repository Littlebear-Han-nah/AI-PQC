"""Isolation Forest anomaly detection for network flow features."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import RobustScaler

Contamination = Union[float, str]

LONG_TAIL_FEATURES = {
    "duration",
    "packet_count",
    "byte_size",
    "src_bytes",
    "dst_bytes",
    "flow_rate",
    "flow_packets_s",
    "fwd_packets_s",
    "bwd_packets_s",
    "flow_iat_mean",
    "flow_iat_std",
    "fwd_iat_mean",
    "bwd_iat_mean",
    "packet_length_mean",
    "packet_length_std",
    "active_mean",
    "idle_mean",
}


@dataclass
class AnomalyResult:
    """Per-sample anomaly detection output."""

    label: int
    score: float
    risk: float


@dataclass
class FlowPreprocessor:
    """Fit-on-train preprocessing for CICIDS-style long-tailed flow features."""

    feature_columns: Optional[list[str]] = None
    clip_low: float = 0.005
    clip_high: float = 0.995

    def __post_init__(self) -> None:
        self.medians_: Optional[np.ndarray] = None
        self.lower_bounds_: Optional[np.ndarray] = None
        self.upper_bounds_: Optional[np.ndarray] = None
        self.log_indices_: list[int] = []
        self.scaler_: Optional[RobustScaler] = None
        self.n_features_: Optional[int] = None

    def fit(self, X: np.ndarray) -> "FlowPreprocessor":
        values = self._as_float_matrix(X)
        self.n_features_ = values.shape[1]
        self.medians_ = _nanmedian_with_default(values)
        values = self._fill_missing(values)
        self.lower_bounds_ = np.nanquantile(values, self.clip_low, axis=0)
        self.upper_bounds_ = np.nanquantile(values, self.clip_high, axis=0)
        self.upper_bounds_ = np.maximum(self.upper_bounds_, self.lower_bounds_)
        values = self._clip(values)

        self.log_indices_ = self._resolve_log_indices()
        values = self._log_transform(values)

        self.scaler_ = RobustScaler()
        self.scaler_.fit(values)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        self._check_fitted()
        values = self._as_float_matrix(X)
        if values.shape[1] != self.n_features_:
            raise ValueError(
                f"Expected {self.n_features_} features, got {values.shape[1]}."
            )
        values = self._fill_missing(values)
        values = self._clip(values)
        values = self._log_transform(values)
        return self.scaler_.transform(values)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def _as_float_matrix(self, X: np.ndarray) -> np.ndarray:
        values = np.asarray(X, dtype=float)
        if values.ndim != 2:
            raise ValueError("Feature matrix must be two-dimensional.")
        return np.where(np.isfinite(values), values, np.nan)

    def _fill_missing(self, X: np.ndarray) -> np.ndarray:
        values = X.copy()
        return np.where(np.isnan(values), self.medians_, values)

    def _clip(self, X: np.ndarray) -> np.ndarray:
        return np.clip(X, self.lower_bounds_, self.upper_bounds_)

    def _log_transform(self, X: np.ndarray) -> np.ndarray:
        values = X.copy()
        if self.log_indices_:
            values[:, self.log_indices_] = np.log1p(
                np.maximum(values[:, self.log_indices_], 0.0)
            )
        return values

    def _resolve_log_indices(self) -> list[int]:
        if self.feature_columns is None:
            return list(range(self.n_features_ or 0))
        return [
            idx
            for idx, name in enumerate(self.feature_columns)
            if name in LONG_TAIL_FEATURES
        ]

    def _check_fitted(self) -> None:
        if (
            self.medians_ is None
            or self.lower_bounds_ is None
            or self.upper_bounds_ is None
            or self.scaler_ is None
            or self.n_features_ is None
        ):
            raise RuntimeError("Preprocessor must be fitted before transform.")


class FlowAnomalyDetector:
    """Isolation Forest wrapper for network traffic anomaly detection."""

    def __init__(
        self,
        contamination: Contamination = 0.1,
        random_state: int = 42,
        n_estimators: int = 100,
        feature_columns: Optional[list[str]] = None,
    ) -> None:
        self.feature_columns = feature_columns
        self.preprocessor = FlowPreprocessor(feature_columns=feature_columns)
        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=contamination,
            random_state=random_state,
        )
        self._fitted = False
        self._risk_reference: tuple[float, float] | None = None

    def fit(self, X: np.ndarray) -> "FlowAnomalyDetector":
        processed = self.preprocessor.fit_transform(X)
        self.model.fit(processed)
        train_scores = self.model.score_samples(processed)
        inverted = -train_scores
        self._risk_reference = (float(inverted.min()), float(inverted.max()))
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model must be fitted before prediction.")
        return self.model.predict(self.preprocessor.transform(X))

    def score_samples(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("Model must be fitted before scoring.")
        return self.model.score_samples(self.preprocessor.transform(X))

    def scores_to_risk(self, scores: np.ndarray) -> np.ndarray:
        """Map sklearn scores (lower = more anomalous) to risk in [0, 1]."""
        inverted = -scores
        if self._risk_reference is None:
            lo, hi = float(inverted.min()), float(inverted.max())
        else:
            lo, hi = self._risk_reference
        if hi == lo:
            return np.full(len(scores), 0.5)
        return np.clip((inverted - lo) / (hi - lo), 0.0, 1.0)

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
    contamination: Contamination = 0.1,
    feature_columns: Optional[list[str]] = None,
) -> tuple[FlowAnomalyDetector, dict]:
    """Train Isolation Forest and optionally compute evaluation metrics."""
    detector = FlowAnomalyDetector(
        random_state=random_state,
        contamination=contamination,
        feature_columns=feature_columns,
    )
    detector.fit(X)

    metrics: dict = {}
    if y is not None:
        y_pred = detector.predict(X)
        metrics = evaluate_predictions(y, y_pred)
    return detector, metrics


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    matrix = confusion_matrix(y_true, y_pred, labels=[-1, 1])
    true_anomaly_pred_anomaly, false_negative = matrix[0]
    false_positive, true_normal_pred_normal = matrix[1]
    false_positive_rate = _safe_divide(
        false_positive,
        false_positive + true_normal_pred_normal,
    )
    false_negative_rate = _safe_divide(
        false_negative,
        true_anomaly_pred_anomaly + false_negative,
    )
    return {
        "confusion_matrix": matrix.tolist(),
        "classification_report": classification_report(
            y_true,
            y_pred,
            labels=[-1, 1],
            target_names=["anomaly", "normal"],
            zero_division=0,
        ),
        "accuracy": float(np.mean(y_true == y_pred)),
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
    }


def _safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _nanmedian_with_default(X: np.ndarray) -> np.ndarray:
    with np.errstate(all="ignore"):
        medians = np.nanmedian(X, axis=0)
    return np.where(np.isfinite(medians), medians, 0.0)
