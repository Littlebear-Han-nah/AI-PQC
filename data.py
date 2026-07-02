"""Network flow CSV loading and test-data simulation helpers."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd

BASE_FEATURE_COLUMNS = [
    "duration",
    "packet_count",
    "byte_size",
    "src_bytes",
    "dst_bytes",
    "flow_rate",
]

CICIDS_REPRESENTATIVE_FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + [
    "flow_packets_s",
    "fwd_packets_s",
    "bwd_packets_s",
    "flow_iat_mean",
    "flow_iat_std",
    "fwd_iat_mean",
    "bwd_iat_mean",
    "packet_length_mean",
    "packet_length_std",
    "syn_flag_count",
    "ack_flag_count",
    "rst_flag_count",
    "psh_flag_count",
    "down_up_ratio",
    "init_win_bytes_forward",
    "init_win_bytes_backward",
    "active_mean",
    "idle_mean",
]

# Public name used by the UI. Standardized dataframes may contain only the
# base subset when a non-CICIDS CSV is uploaded.
FEATURE_COLUMNS = CICIDS_REPRESENTATIVE_FEATURE_COLUMNS

LABEL_COLUMN = "label"

_COLUMN_ALIASES = {
    "duration": [
        "duration",
        "flow_duration",
        "flow duration",
    ],
    "packet_count": [
        "packet_count",
        "packet count",
        "total_packets",
        "total packets",
    ],
    "src_packets": [
        "total_fwd_packets",
        "total fwd packets",
        "tot fwd pkts",
        "fwd packet count",
    ],
    "dst_packets": [
        "total_backward_packets",
        "total backward packets",
        "tot bwd pkts",
        "bwd packet count",
    ],
    "byte_size": [
        "byte_size",
        "byte size",
        "total_bytes",
        "total bytes",
    ],
    "src_bytes": [
        "src_bytes",
        "src bytes",
        "total_length_of_fwd_packets",
        "total length of fwd packets",
        "totlen fwd pkts",
        "fwd bytes",
    ],
    "dst_bytes": [
        "dst_bytes",
        "dst bytes",
        "total_length_of_bwd_packets",
        "total length of bwd packets",
        "totlen bwd pkts",
        "bwd bytes",
    ],
    "flow_rate": [
        "flow_rate",
        "flow rate",
        "flow_bytes/s",
        "flow bytes/s",
        "flow bytes per second",
    ],
    "flow_packets_s": [
        "flow_packets_s",
        "flow packets/s",
        "flow packets per second",
    ],
    "fwd_packets_s": [
        "fwd_packets_s",
        "fwd packets/s",
        "forward packets/s",
    ],
    "bwd_packets_s": [
        "bwd_packets_s",
        "bwd packets/s",
        "backward packets/s",
    ],
    "flow_iat_mean": [
        "flow_iat_mean",
        "flow iat mean",
    ],
    "flow_iat_std": [
        "flow_iat_std",
        "flow iat std",
    ],
    "fwd_iat_mean": [
        "fwd_iat_mean",
        "fwd iat mean",
    ],
    "bwd_iat_mean": [
        "bwd_iat_mean",
        "bwd iat mean",
    ],
    "packet_length_mean": [
        "packet_length_mean",
        "packet length mean",
    ],
    "packet_length_std": [
        "packet_length_std",
        "packet length std",
    ],
    "syn_flag_count": [
        "syn_flag_count",
        "syn flag count",
    ],
    "ack_flag_count": [
        "ack_flag_count",
        "ack flag count",
    ],
    "rst_flag_count": [
        "rst_flag_count",
        "rst flag count",
    ],
    "psh_flag_count": [
        "psh_flag_count",
        "psh flag count",
    ],
    "down_up_ratio": [
        "down_up_ratio",
        "down/up ratio",
        "down up ratio",
    ],
    "init_win_bytes_forward": [
        "init_win_bytes_forward",
        "init win bytes forward",
        "init_win_bytes_forward",
    ],
    "init_win_bytes_backward": [
        "init_win_bytes_backward",
        "init win bytes backward",
        "init_win_bytes_backward",
    ],
    "active_mean": [
        "active_mean",
        "active mean",
    ],
    "idle_mean": [
        "idle_mean",
        "idle mean",
    ],
    "label": [
        "label",
        "class",
        "target",
    ],
}


def standardize_flow_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Return a dataframe with the internal feature names used by the app."""
    source = df.copy()
    source.columns = [str(col).strip() for col in source.columns]
    lookup = {_canonical_name(col): col for col in source.columns}

    features: dict[str, Optional[pd.Series]] = {}

    features["duration"] = _numeric_series(source, lookup, "duration")
    src_packets = _numeric_series(source, lookup, "src_packets")
    dst_packets = _numeric_series(source, lookup, "dst_packets")
    packet_count = _numeric_series(source, lookup, "packet_count")
    if packet_count is None and src_packets is not None and dst_packets is not None:
        packet_count = src_packets + dst_packets
    features["packet_count"] = packet_count

    features["src_bytes"] = _numeric_series(source, lookup, "src_bytes")
    features["dst_bytes"] = _numeric_series(source, lookup, "dst_bytes")
    byte_size = _numeric_series(source, lookup, "byte_size")
    if byte_size is None and features["src_bytes"] is not None and features["dst_bytes"] is not None:
        byte_size = features["src_bytes"] + features["dst_bytes"]
    features["byte_size"] = byte_size

    flow_rate = _numeric_series(source, lookup, "flow_rate")
    if flow_rate is None and features["byte_size"] is not None and features["duration"] is not None:
        duration_seconds = features["duration"].replace(0, np.nan)
        flow_rate = features["byte_size"] / duration_seconds
    features["flow_rate"] = flow_rate

    for column in FEATURE_COLUMNS:
        if column in features:
            continue
        features[column] = _numeric_series(source, lookup, column)

    missing = [col for col in BASE_FEATURE_COLUMNS if features[col] is None]
    if missing:
        raise ValueError(
            "CSV missing required feature columns or recognized CICIDS2017 aliases: "
            f"{missing}"
        )

    available_features = [
        col for col in FEATURE_COLUMNS if features.get(col) is not None
    ]
    result = pd.DataFrame(
        {col: features[col] for col in available_features},
        index=source.index,
    )
    result = result[available_features].apply(pd.to_numeric, errors="coerce")
    result = result.replace([np.inf, -np.inf], np.nan)
    result = _fill_numeric_gaps(result)

    label = _label_series(source, lookup)
    if label is not None:
        result[LABEL_COLUMN] = label

    return result


def generate_simulated_test_data(
    source_df: pd.DataFrame,
    n_samples: int = 200,
    random_state: Optional[int] = None,
) -> pd.DataFrame:
    """Create test data by resampling rows and perturbing base flow features.

    Only independent base features are directly perturbed. Dependent features are
    recomputed afterward so simulated rows keep basic network-flow consistency:
    byte_size = src_bytes + dst_bytes and flow_rate = byte_size / duration.
    """
    if source_df.empty:
        raise ValueError("Training CSV is empty; cannot simulate test data.")

    base = standardize_flow_dataframe(source_df)
    rng = np.random.default_rng(random_state)
    sample_indices = rng.integers(0, len(base), size=n_samples)
    simulated = base.iloc[sample_indices].reset_index(drop=True).copy()

    min_duration = _positive_floor(base["duration"], fallback=1.0)
    _perturb_positive_continuous(simulated, base, "duration", rng, min_value=min_duration)
    _perturb_count(simulated, base, "packet_count", rng)
    _perturb_count(simulated, base, "src_bytes", rng)
    _perturb_count(simulated, base, "dst_bytes", rng)

    simulated["byte_size"] = simulated["src_bytes"] + simulated["dst_bytes"]
    simulated["flow_rate"] = (
        simulated["byte_size"] / simulated["duration"].clip(lower=min_duration)
    )

    selected_columns = feature_columns_from_dataframe(simulated)
    if LABEL_COLUMN in simulated.columns:
        selected_columns.append(LABEL_COLUMN)
    simulated = simulated[selected_columns]

    if LABEL_COLUMN in simulated.columns:
        simulated[LABEL_COLUMN] = simulated[LABEL_COLUMN].astype(int)

    return simulated


def _perturb_positive_continuous(
    simulated: pd.DataFrame,
    base: pd.DataFrame,
    column: str,
    rng: np.random.Generator,
    min_value: float = 0.0,
) -> None:
    values = simulated[column].astype(float).to_numpy()
    scale = _noise_scale(base[column])
    multiplicative = rng.normal(1.0, 0.03, size=len(simulated))
    additive = rng.normal(0.0, scale, size=len(simulated))
    simulated[column] = np.maximum(values * multiplicative + additive, min_value)


def _perturb_count(
    simulated: pd.DataFrame,
    base: pd.DataFrame,
    column: str,
    rng: np.random.Generator,
) -> None:
    values = simulated[column].astype(float).to_numpy()
    scale = _noise_scale(base[column])
    multiplicative = rng.normal(1.0, 0.03, size=len(simulated))
    additive = rng.normal(0.0, scale, size=len(simulated))
    simulated[column] = np.rint(np.maximum(values * multiplicative + additive, 0.0)).astype(int)


def _noise_scale(series: pd.Series) -> float:
    values = series.astype(float).to_numpy()
    spread = float(np.nanstd(values))
    return max(spread * 0.02, 1e-9)


def _positive_floor(series: pd.Series, fallback: float) -> float:
    values = series.astype(float).to_numpy()
    positive = values[np.isfinite(values) & (values > 0)]
    if len(positive) == 0:
        return fallback
    return max(float(np.quantile(positive, 0.01)), fallback)


def dataframe_to_arrays(
    df: pd.DataFrame,
    feature_columns: Optional[list[str]] = None,
) -> Tuple[pd.DataFrame, np.ndarray, Optional[np.ndarray]]:
    """Extract feature matrix and optional labels from a flow dataframe."""
    standardized = standardize_flow_dataframe(df)
    selected_features = feature_columns or feature_columns_from_dataframe(standardized)
    missing = [col for col in selected_features if col not in standardized.columns]
    if missing:
        raise ValueError(
            "CSV is missing feature columns required by the trained model: "
            f"{missing}"
        )
    y = standardized[LABEL_COLUMN].values if LABEL_COLUMN in standardized.columns else None
    X = standardized[selected_features].values.astype(float)
    return standardized, X, y


def feature_columns_from_dataframe(df: pd.DataFrame) -> list[str]:
    """Return supported feature columns present in a standardized dataframe."""
    return [col for col in FEATURE_COLUMNS if col in df.columns]


def _canonical_name(value: str) -> str:
    return " ".join(str(value).strip().lower().replace("_", " ").split())


def _numeric_series(
    df: pd.DataFrame,
    lookup: dict[str, str],
    alias_group: str,
) -> Optional[pd.Series]:
    for alias in _COLUMN_ALIASES[alias_group]:
        column = lookup.get(_canonical_name(alias))
        if column is not None:
            return pd.to_numeric(df[column], errors="coerce")
    return None


def _label_series(df: pd.DataFrame, lookup: dict[str, str]) -> Optional[pd.Series]:
    column = None
    for alias in _COLUMN_ALIASES["label"]:
        column = lookup.get(_canonical_name(alias))
        if column is not None:
            break
    if column is None:
        return None

    raw = df[column]
    numeric = pd.to_numeric(raw, errors="coerce")
    if numeric.notna().all():
        values = set(numeric.astype(int).unique().tolist())
        if values.issubset({-1, 1}):
            return numeric.astype(int)
        if values.issubset({0, 1}):
            return numeric.apply(lambda value: -1 if int(value) == 1 else 1).astype(int)
        return numeric.apply(lambda value: -1 if value < 0 else 1).astype(int)

    labels = raw.astype(str).str.strip().str.lower()
    return labels.apply(lambda value: 1 if value in {"benign", "normal", "1"} else -1).astype(int)


def _fill_numeric_gaps(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        raise ValueError("CSV has no rows.")

    cleaned = df.copy()
    medians = cleaned.median(numeric_only=True).replace([np.inf, -np.inf], np.nan)
    medians = medians.fillna(0.0)
    cleaned = cleaned.fillna(medians)

    if cleaned.isna().any().any():
        raise ValueError("CSV contains feature columns that could not be converted to numbers.")

    return cleaned
