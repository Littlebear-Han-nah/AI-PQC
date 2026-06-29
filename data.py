"""Network flow dataset loading and synthetic data generation."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "duration",
    "packet_count",
    "byte_size",
    "src_bytes",
    "dst_bytes",
    "flow_rate",
]


def generate_synthetic_dataset(
    n_samples: int = 200,
    anomaly_ratio: float = 0.1,
    random_state: int = 42,
) -> pd.DataFrame:
    """Generate synthetic network flow features with injected anomalies."""
    rng = np.random.default_rng(random_state)
    n_normal = int(n_samples * (1 - anomaly_ratio))
    n_anomaly = n_samples - n_normal

    normal = pd.DataFrame(
        {
            "duration": rng.uniform(0.5, 120.0, n_normal),
            "packet_count": rng.integers(10, 500, n_normal),
            "byte_size": rng.integers(500, 50_000, n_normal),
            "src_bytes": rng.integers(200, 25_000, n_normal),
            "dst_bytes": rng.integers(200, 25_000, n_normal),
        }
    )
    normal["flow_rate"] = normal["byte_size"] / normal["duration"].clip(lower=0.1)
    normal["label"] = 1

    anomaly = pd.DataFrame(
        {
            "duration": rng.uniform(0.01, 0.5, n_anomaly),
            "packet_count": rng.integers(5_000, 50_000, n_anomaly),
            "byte_size": rng.integers(500_000, 5_000_000, n_anomaly),
            "src_bytes": rng.integers(400_000, 4_000_000, n_anomaly),
            "dst_bytes": rng.integers(1_000, 50_000, n_anomaly),
        }
    )
    anomaly["flow_rate"] = anomaly["byte_size"] / anomaly["duration"].clip(lower=0.01)
    anomaly["label"] = -1

    df = pd.concat([normal, anomaly], ignore_index=True)
    return df.sample(frac=1, random_state=random_state).reset_index(drop=True)


def dataframe_to_arrays(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, np.ndarray, Optional[np.ndarray]]:
    """Extract feature matrix and optional labels from a flow dataframe."""
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    y = df["label"].values if "label" in df.columns else None
    X = df[FEATURE_COLUMNS].values.astype(float)
    return df, X, y
