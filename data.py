"""网络流量数据集加载与合成数据生成。"""

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

FEATURE_LABELS_ZH = {
    "duration": "持续时间",
    "packet_count": "包数量",
    "byte_size": "字节数",
    "src_bytes": "源流量",
    "dst_bytes": "目标流量",
    "flow_rate": "流速",
}


def generate_synthetic_dataset(
    n_samples: int = 200,
    anomaly_ratio: float = 0.1,
    random_state: int = 42,
) -> pd.DataFrame:
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


def process_cicids2017(df: pd.DataFrame) -> pd.DataFrame:
    """处理 CICIDS2017 原始数据集"""
    df.columns = df.columns.str.strip()
    
    duration = df['Flow Duration'] / 1e6
    packet_count = df['Total Fwd Packets'] + df['Total Backward Packets']
    src_bytes = df['Total Length of Fwd Packets']
    dst_bytes = df['Total Length of Bwd Packets']
    byte_size = src_bytes + dst_bytes
    flow_rate = byte_size / duration.clip(lower=0.01)
    
    label = df['Label'].apply(lambda x: 1 if x == 'BENIGN' else -1)
    
    new_df = pd.DataFrame({
        "duration": duration,
        "packet_count": packet_count,
        "byte_size": byte_size,
        "src_bytes": src_bytes,
        "dst_bytes": dst_bytes,
        "flow_rate": flow_rate,
        "label": label
    })
    
    new_df = new_df.replace([np.inf, -np.inf], np.nan).dropna()
    return new_df


def dataframe_to_arrays(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, np.ndarray, Optional[np.ndarray]]:
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"数据集缺少必要字段: {missing}")
    y = df["label"].values if "label" in df.columns else None
    X = df[FEATURE_COLUMNS].values.astype(float)
    return df, X, y
