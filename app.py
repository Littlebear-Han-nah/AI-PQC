"""
AI + PQC Security Monitoring System — Streamlit Demo UI

Run:
    streamlit run app.py
"""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from data import FEATURE_COLUMNS, dataframe_to_arrays, generate_synthetic_dataset
from pqc import get_backend_info
from utils import (
    create_anomaly_score_figure,
    create_status_count_figure,
    format_log_html,
    results_to_dataframe,
    run_detection_pipeline,
    styled_results_table,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI + PQC Security Monitoring",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS (academic / research demo style) ───────────────────────────────
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a252f;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #566573;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #2c3e50;
        border-left: 4px solid #2980b9;
        padding-left: 10px;
        margin: 1rem 0 0.75rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #eef2f7 100%);
        border: 1px solid #dde4ea;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .status-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .pill-normal { background: #d5f5e3; color: #1e8449; }
    .pill-anomaly { background: #fadbd8; color: #922b21; }
    div[data-testid="stMetric"] {
        background: #f8f9fa;
        border: 1px solid #e5e8eb;
        border-radius: 10px;
        padding: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_session_state() -> None:
    defaults = {
        "dataset_df": None,
        "pipeline_result": None,
        "live_logs": [],
        "live_rows": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header() -> None:
    st.markdown(
        '<p class="main-title">🛡️ AI + PQC Security Monitoring System</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="subtitle">Network Traffic → Isolation Forest Anomaly Detection → '
        "Post-Quantum Cryptography Response</p>",
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[int, bool, float]:
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        st.caption(get_backend_info())

        n_samples = st.slider("Synthetic sample count", 50, 500, 200, step=50)
        live_sim = st.toggle("Enable live simulation", value=True)
        sim_delay = st.slider(
            "Live update delay (seconds)",
            0.0,
            0.3,
            0.05,
            step=0.05,
            disabled=not live_sim,
        )

        st.markdown("---")
        st.markdown("**Features analyzed**")
        for col in FEATURE_COLUMNS:
            st.markdown(f"- `{col}`")

        st.markdown("---")
        st.markdown("**PQC Policy**")
        st.markdown("- Normal → **Kyber512**")
        st.markdown("- Anomaly → **Kyber768** + key renegotiation")

    return n_samples, live_sim, sim_delay


def render_data_input(n_samples: int) -> None:
    st.markdown('<p class="section-header">📂 Data Input</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded = st.file_uploader(
            "Upload network flow CSV",
            type=["csv"],
            help=f"CSV must include columns: {', '.join(FEATURE_COLUMNS)}",
        )

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎲 Generate Synthetic Data", use_container_width=True):
            st.session_state.dataset_df = generate_synthetic_dataset(n_samples=n_samples)
            st.session_state.pipeline_result = None
            st.session_state.live_logs = []
            st.session_state.live_rows = []
            st.success(f"Generated {n_samples} synthetic network flows.")

    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
            _, _, _ = dataframe_to_arrays(df)
            st.session_state.dataset_df = df
            st.session_state.pipeline_result = None
            st.session_state.live_logs = []
            st.session_state.live_rows = []
            st.success(f"Loaded {len(df)} samples from `{uploaded.name}`.")
        except Exception as exc:
            st.error(str(exc))

    df = st.session_state.dataset_df
    if df is not None:
        with st.expander("Preview dataset", expanded=False):
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)
            st.caption(f"Total rows: {len(df)}")


def run_live_detection(df: pd.DataFrame, delay: float) -> None:
    _, X, y = dataframe_to_arrays(df)

    progress = st.progress(0, text="Initializing Isolation Forest...")
    status_box = st.empty()
    log_box = st.empty()

    st.session_state.live_logs = []
    st.session_state.live_rows = []
    total = len(X)

    def on_sample(sample, batch_logs):
        st.session_state.live_rows.append(sample)
        st.session_state.live_logs.extend(batch_logs)
        done = len(st.session_state.live_rows)
        progress.progress(
            done / total,
            text=f"Analyzing flow {done} / {total}...",
        )
        pill_class = "pill-anomaly" if sample.status == "ANOMALY" else "pill-normal"
        status_box.markdown(
            f'<span class="status-pill {pill_class}">'
            f"Sample {sample.sample_id}: {sample.status} → {sample.pqc_action}"
            f"</span>",
            unsafe_allow_html=True,
        )
        log_box.markdown(
            format_log_html(st.session_state.live_logs[-12:]),
            unsafe_allow_html=True,
        )
        if delay > 0:
            time.sleep(delay)

    result = run_detection_pipeline(X, y, live_callback=on_sample)
    st.session_state.pipeline_result = result
    progress.progress(1.0, text="Detection complete ✓")
    status_box.markdown(
        '<span class="status-pill pill-normal">✓ Analysis finished</span>',
        unsafe_allow_html=True,
    )


def run_batch_detection(df: pd.DataFrame) -> None:
    _, X, y = dataframe_to_arrays(df)
    with st.spinner("Running Isolation Forest + PQC pipeline..."):
        st.session_state.pipeline_result = run_detection_pipeline(X, y)
        st.session_state.live_logs = st.session_state.pipeline_result.logs
        st.session_state.live_rows = st.session_state.pipeline_result.rows


def render_run_section(live_sim: bool, sim_delay: float) -> None:
    st.markdown('<p class="section-header">▶️ Detection</p>', unsafe_allow_html=True)

    run_col, info_col = st.columns([1, 3])
    with run_col:
        run_clicked = st.button(
            "🚀 Run Detection",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.dataset_df is None,
        )
    with info_col:
        if st.session_state.dataset_df is None:
            st.info("Upload a CSV or generate synthetic data to begin.")
        else:
            st.caption(
                f"Ready to analyze **{len(st.session_state.dataset_df)}** network flows."
            )

    if run_clicked and st.session_state.dataset_df is not None:
        if live_sim:
            run_live_detection(st.session_state.dataset_df, sim_delay)
        else:
            run_batch_detection(st.session_state.dataset_df)


def render_results() -> None:
    result = st.session_state.pipeline_result
    if result is None:
        return

    st.markdown(
        '<p class="section-header">📊 Detection Results</p>',
        unsafe_allow_html=True,
    )

    s = result.summary
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Flows", s["total"])
    m2.metric("Normal", s["normal"])
    m3.metric("Anomalies", s["anomalies"])
    m4.metric("Key Renegotiations", s["renegotiations"])

    st.markdown(
        f"**Current PQC mode:** `{s['final_algorithm']}` &nbsp;|&nbsp; "
        f"**Backend:** {get_backend_info()}",
        unsafe_allow_html=True,
    )

    results_df = results_to_dataframe(result.rows)
    st.dataframe(
        styled_results_table(results_df),
        use_container_width=True,
        hide_index=True,
        height=min(420, 38 + len(results_df) * 35),
    )


def render_visualizations() -> None:
    result = st.session_state.pipeline_result
    if result is None or len(result.scores) == 0:
        return

    st.markdown(
        '<p class="section-header">📈 Visual Analytics</p>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(
            create_anomaly_score_figure(result.scores, result.labels),
            use_container_width=True,
        )
    with col_b:
        st.plotly_chart(
            create_status_count_figure(result.summary["normal"], result.summary["anomalies"]),
            use_container_width=True,
        )

    if result.metrics:
        with st.expander("Model evaluation metrics", expanded=False):
            st.text(result.metrics.get("classification_report", ""))
            st.metric("Accuracy", f"{result.metrics.get('accuracy', 0):.1%}")


def render_event_log() -> None:
    result = st.session_state.pipeline_result
    if result is None:
        return

    st.markdown(
        '<p class="section-header">📋 Event Log</p>',
        unsafe_allow_html=True,
    )

    logs = st.session_state.live_logs or result.logs
    st.markdown(
        f'<div style="max-height:320px;overflow-y:auto;padding:8px;'
        f'border:1px solid #dde4ea;border-radius:10px;background:#fafbfc;">'
        f"{format_log_html(logs)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇️ Download event log",
        data="\n".join(logs),
        file_name="pqc_event_log.txt",
        mime="text/plain",
    )


def main() -> None:
    init_session_state()
    render_header()

    n_samples, live_sim, sim_delay = render_sidebar()
    render_data_input(n_samples)
    render_run_section(live_sim, sim_delay)
    render_results()
    render_visualizations()
    render_event_log()


if __name__ == "__main__":
    main()
