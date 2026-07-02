"""
AI + PQC Security Monitoring System - Streamlit demo UI.

Run:
    streamlit run app.py
"""

from __future__ import annotations

import time
from typing import Any

import importlib
import pandas as pd
import streamlit as st

import data as data_module
import model as model_module
import utils as utils_module

data_module = importlib.reload(data_module)
model_module = importlib.reload(model_module)
utils_module = importlib.reload(utils_module)

from data import (
    FEATURE_COLUMNS,
    dataframe_to_arrays,
    feature_columns_from_dataframe,
    generate_simulated_test_data,
    standardize_flow_dataframe,
)
from model import evaluate_predictions, train_detector
from pqc import PQCSimulator, get_backend_info

from utils import (
    PipelineResult,
    RiskPolicyState,
    build_policy_sample,
    build_log_entry,
    create_anomaly_score_figure,
    create_status_count_figure,
    format_log_html,
    results_to_dataframe,
    run_detection_pipeline,
    styled_results_table,
)

st.set_page_config(
    page_title="AI + PQC Security Monitoring",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="expanded",
)

MAX_RESULT_TABLE_ROWS = 1000
MAX_CHART_POINTS = 2000
MAX_EVENT_LOG_DISPLAY = 500

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
        border-radius: 8px;
        padding: 0.75rem;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricDelta"] {
        color: #1a252f !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        color: #34495e !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

TRANSLATIONS = {
    "en": {
        "language": "Language",
        "configuration": "Configuration",
        "live_testing": "Enable live testing",
        "live_delay": "Live update delay (seconds)",
        "seed_mode": "Random seed mode",
        "fixed": "Fixed",
        "dynamic": "Dynamic",
        "fixed_seed": "Fixed random seed",
        "contamination": "Contamination",
        "custom": "custom",
        "custom_contamination": "Custom contamination",
        "risk_strategy": "Risk Response Strategy",
        "risk_policy_mode": "Risk threshold mode",
        "risk_policy_auto": "auto (model contamination threshold)",
        "risk_policy_manual": "manual risk levels",
        "low_threshold": "Low/Medium risk threshold",
        "high_threshold": "Medium/High risk threshold",
        "medium_streak_n": "Medium-risk streak trigger count",
        "features_analyzed": "Features analyzed",
        "pqc_policy": "PQC Policy",
        "normal_policy": "Normal -> **Kyber512** policy simulation",
        "anomaly_policy": "Anomaly -> **Kyber768** policy simulation + simulated key renegotiation",
        "pqc_simulation_note": "PQC response is a policy simulation, not a real liboqs/Kyber key exchange.",
        "title": "AI + PQC Security Monitoring System",
        "subtitle": "CSV training data -> Isolation Forest testing -> Post-Quantum Cryptography response",
        "training_csv": "Training CSV",
        "upload_training_csv": "Upload training CSV",
        "csv_help": "Required: app feature columns or recognized CICIDS2017 columns.",
        "loaded_training": "Loaded {rows} training rows from `{name}`.",
        "train_model": "Train Model",
        "train_after_upload": "Click Train Model after uploading the training CSV.",
        "params_changed": "Model parameters changed. Click Train Model to retrain.",
        "model_trained_caption": "Model trained: contamination={contamination}, random_state={random_state}.",
        "preview_training": "Preview training data",
        "total_training_rows": "Total training rows: {rows}",
        "test_data": "Test Data",
        "upload_train_first": "Upload a training CSV before preparing test data.",
        "test_data_source": "Test data source",
        "simulate_from_train": "Simulate from training CSV",
        "upload_test_csv": "Upload test CSV",
        "simulated_test_rows": "Simulated test rows",
        "generate_test_data": "Generate Test Data",
        "generated_from_train": "Generated {rows} test rows from the training CSV.",
        "loaded_test": "Loaded {rows} test rows from `{name}`.",
        "use_uploaded_test": "Use Uploaded Test CSV",
        "using_uploaded_test": "Using uploaded test CSV as current test data.",
        "simulated_rows_from_test": "Simulated rows from test CSV",
        "simulate_from_test": "Simulate From Test CSV",
        "generated_from_test": "Generated {rows} test rows from the uploaded test CSV.",
        "preview_test": "Preview test data",
        "total_test_rows": "Total test rows: {rows}",
        "detection": "Detection",
        "run_test": "Run Test",
        "stop_test": "Stop Test",
        "upload_training_begin": "Upload a training CSV to begin.",
        "click_train_before_test": "Click Train Model before running a test.",
        "prepare_test_data": "Prepare simulated test data or upload a test CSV.",
        "running_test": "Running test: {done} / {total} rows processed.",
        "ready": "Ready: {train_rows} training rows, {test_rows} test rows.",
        "training_spinner": "Training Isolation Forest model...",
        "trained_success": "Model trained with contamination={contamination}, random_state={random_state}.",
        "running_spinner": "Running Isolation Forest + PQC pipeline...",
        "testing_row": "Testing row {done} / {total}...",
        "test_stopped": "Test stopped",
        "detection_complete": "Detection complete",
        "sample_status": "Sample {sample_id}: {status} -> {action}",
        "stopped_log": "Detection stopped by user",
        "log_anomaly": "Sample {sample_id} -> ANOMALY -> Switching to Kyber768",
        "log_normal": "Sample {sample_id} -> NORMAL -> Kyber512",
        "key_renegotiation": "Simulated key renegotiation triggered",
        "detection_results": "Detection Results",
        "processed": "Processed",
        "normal": "Normal",
        "anomalies": "Anomalies",
        "false_positive_rate": "False Positive Rate",
        "false_negative_rate": "False Negative Rate",
        "test_status": "Test status",
        "complete": "complete",
        "stopped": "stopped",
        "current_pqc_mode": "Current PQC mode",
        "key_renegotiations": "Key renegotiations",
        "risk_level_summary": "Risk levels: Low {low}, Medium {medium}, High {high}",
        "renegotiation_summary": "Renegotiations: High-risk direct {direct}, medium-streak {streak}",
        "visual_analytics": "Visual Analytics",
        "score_chart": "Anomaly Scores per Network Flow",
        "score_x": "Sample Index",
        "score_y": "Isolation Forest Score",
        "median": "Median",
        "status_chart": "Traffic Classification Summary",
        "count": "Count",
        "model_metrics": "Model evaluation metrics",
        "accuracy": "Accuracy",
        "event_log": "Event Log",
        "download_log": "Download event log",
        "sample_id": "Sample ID",
        "status": "Status",
        "risk": "Risk",
        "pqc_action": "PQC Action",
        "status_normal": "Normal",
        "status_anomaly": "Anomaly",
    },
    "zh": {
        "language": "语言",
        "configuration": "配置",
        "live_testing": "启用实时测试",
        "live_delay": "实时更新延迟（秒）",
        "seed_mode": "随机种子模式",
        "fixed": "固定",
        "dynamic": "动态",
        "fixed_seed": "固定随机种子",
        "contamination": "Contamination 参数",
        "custom": "自定义",
        "custom_contamination": "自定义 contamination",
        "risk_strategy": "风险响应策略",
        "risk_policy_mode": "风险阈值模式",
        "risk_policy_auto": "auto（使用模型 contamination 内部阈值）",
        "risk_policy_manual": "手动风险分级",
        "low_threshold": "低/中风险阈值",
        "high_threshold": "中/高风险阈值",
        "medium_streak_n": "中风险连续触发次数",
        "features_analyzed": "分析特征",
        "pqc_policy": "PQC 策略",
        "normal_policy": "正常 -> **Kyber512** 策略模拟",
        "anomaly_policy": "异常 -> **Kyber768** 策略模拟 + 模拟密钥重协商",
        "pqc_simulation_note": "PQC 响应是策略模拟，不是真实 liboqs/Kyber 密钥交换。",
        "title": "AI + PQC 安全监测系统",
        "subtitle": "CSV 训练数据 -> Isolation Forest 测试 -> 后量子密码响应",
        "training_csv": "训练 CSV",
        "upload_training_csv": "上传训练 CSV",
        "csv_help": "需要包含应用特征列，或可识别的 CICIDS2017 列。",
        "loaded_training": "已从 `{name}` 加载 {rows} 条训练数据。",
        "train_model": "训练模型",
        "train_after_upload": "上传训练 CSV 后点击训练模型。",
        "params_changed": "模型参数已改变，请点击训练模型重新训练。",
        "model_trained_caption": "模型已训练：contamination={contamination}, random_state={random_state}。",
        "preview_training": "预览训练数据",
        "total_training_rows": "训练数据总行数：{rows}",
        "test_data": "测试数据",
        "upload_train_first": "请先上传训练 CSV，再准备测试数据。",
        "test_data_source": "测试数据来源",
        "simulate_from_train": "从训练 CSV 模拟生成",
        "upload_test_csv": "上传测试 CSV",
        "simulated_test_rows": "模拟测试数据行数",
        "generate_test_data": "生成测试数据",
        "generated_from_train": "已从训练 CSV 生成 {rows} 条测试数据。",
        "loaded_test": "已从 `{name}` 加载 {rows} 条测试数据。",
        "use_uploaded_test": "使用上传测试 CSV 原始数据",
        "using_uploaded_test": "已切换为上传测试 CSV 原始数据。",
        "simulated_rows_from_test": "从测试 CSV 模拟的行数",
        "simulate_from_test": "从测试 CSV 模拟生成",
        "generated_from_test": "已从上传的测试 CSV 生成 {rows} 条测试数据。",
        "preview_test": "预览测试数据",
        "total_test_rows": "测试数据总行数：{rows}",
        "detection": "检测",
        "run_test": "运行测试",
        "stop_test": "中止测试",
        "upload_training_begin": "请上传训练 CSV 开始。",
        "click_train_before_test": "运行测试前请先点击训练模型。",
        "prepare_test_data": "请生成模拟测试数据或上传测试 CSV。",
        "running_test": "测试运行中：已处理 {done} / {total} 行。",
        "ready": "就绪：{train_rows} 条训练数据，{test_rows} 条测试数据。",
        "training_spinner": "正在训练 Isolation Forest 模型...",
        "trained_success": "模型训练完成：contamination={contamination}, random_state={random_state}。",
        "running_spinner": "正在运行 Isolation Forest + PQC 流程...",
        "testing_row": "正在测试第 {done} / {total} 行...",
        "test_stopped": "测试已中止",
        "detection_complete": "检测完成",
        "sample_status": "样本 {sample_id}: {status} -> {action}",
        "stopped_log": "用户已中止检测",
        "log_anomaly": "样本 {sample_id} -> 异常 -> 切换到 Kyber768",
        "log_normal": "样本 {sample_id} -> 正常 -> Kyber512",
        "key_renegotiation": "已触发模拟密钥重协商",
        "detection_results": "检测结果",
        "processed": "已处理",
        "normal": "正常",
        "anomalies": "异常",
        "false_positive_rate": "误报率",
        "false_negative_rate": "漏报率",
        "test_status": "测试状态",
        "complete": "完成",
        "stopped": "已中止",
        "current_pqc_mode": "当前 PQC 模式",
        "key_renegotiations": "密钥重协商次数",
        "risk_level_summary": "风险等级：低 {low}，中 {medium}，高 {high}",
        "renegotiation_summary": "重协商：高风险直接触发 {direct}，中风险连续触发 {streak}",
        "visual_analytics": "可视化分析",
        "score_chart": "网络流异常分数",
        "score_x": "样本序号",
        "score_y": "Isolation Forest 分数",
        "median": "中位数",
        "status_chart": "流量分类统计",
        "count": "数量",
        "model_metrics": "模型评估指标",
        "accuracy": "准确率",
        "event_log": "事件日志",
        "download_log": "下载事件日志",
        "sample_id": "样本 ID",
        "status": "状态",
        "risk": "风险",
        "pqc_action": "PQC 动作",
        "status_normal": "正常",
        "status_anomaly": "异常",
    },
}


def tr(lang: str, key: str, **kwargs: Any) -> str:
    text = TRANSLATIONS[lang][key]
    return text.format(**kwargs) if kwargs else text


def localized_backend_info(lang: str) -> str:
    info = get_backend_info()
    if lang != "zh":
        return info
    if "liboqs available" in info:
        return "liboqs 可用（演示使用模拟模式）"
    return "PQC 模拟模式（Kyber512 / Kyber768）"


def init_session_state() -> None:
    defaults: dict[str, Any] = {
        "train_df": None,
        "test_df": None,
        "uploaded_test_df": None,
        "pipeline_result": None,
        "live_logs": [],
        "live_rows": [],
        "live_context": None,
        "stop_requested": False,
        "trained_detector": None,
        "trained_model_config": None,
        "last_train_upload": None,
        "last_test_upload": None,
        "ui_lang": "en",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_header(lang: str) -> None:
    st.markdown(
        f'<p class="main-title">{tr(lang, "title")}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="subtitle">{tr(lang, "subtitle")}</p>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        lang_label = st.selectbox(
            "Language / 语言",
            ["en", "zh"],
            format_func=lambda value: "English" if value == "en" else "中文",
        )
        lang = str(lang_label)
        st.session_state.ui_lang = lang

        st.markdown(f"### {tr(lang, 'configuration')}")
        st.caption(localized_backend_info(lang))

        live_sim = st.toggle(tr(lang, "live_testing"), value=True)
        sim_delay = st.slider(
            tr(lang, "live_delay"),
            0.0,
            0.3,
            0.05,
            step=0.05,
            disabled=not live_sim,
        )

        st.markdown("---")
        seed_mode = st.selectbox(
            tr(lang, "seed_mode"),
            ["Fixed", "Dynamic"],
            index=0,
            format_func=lambda value: tr(lang, "fixed")
            if value == "Fixed"
            else tr(lang, "dynamic"),
        )
        fixed_seed = st.number_input(
            tr(lang, "fixed_seed"),
            min_value=0,
            max_value=2_147_483_647,
            value=42,
            step=1,
            disabled=seed_mode == "Dynamic",
        )

        st.markdown("---")
        contamination_mode = st.radio(
            tr(lang, "contamination"),
            ["auto", "custom"],
            horizontal=True,
            format_func=lambda value: "auto" if value == "auto" else tr(lang, "custom"),
        )
        contamination_value = st.slider(
            tr(lang, "custom_contamination"),
            0.01,
            0.50,
            0.10,
            step=0.01,
            disabled=contamination_mode == "auto",
        )

        st.markdown("---")
        st.markdown(f"**{tr(lang, 'risk_strategy')}**")
        risk_policy_mode = st.radio(
            tr(lang, "risk_policy_mode"),
            ["auto", "manual"],
            horizontal=True,
            format_func=lambda value: tr(lang, "risk_policy_auto")
            if value == "auto"
            else tr(lang, "risk_policy_manual"),
        )
        low_threshold = st.slider(
            tr(lang, "low_threshold"),
            0.0,
            0.95,
            0.015,
            step=0.005,
            disabled=risk_policy_mode == "auto",
        )
        high_min = min(round(low_threshold + 0.005, 3), 1.0)
        high_default = max(0.20, high_min)
        high_threshold = st.slider(
            tr(lang, "high_threshold"),
            high_min,
            1.0,
            high_default,
            step=0.005,
            disabled=risk_policy_mode == "auto",
        )
        medium_streak_n = st.number_input(
            tr(lang, "medium_streak_n"),
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            disabled=risk_policy_mode == "auto",
        )

        st.markdown("---")
        st.markdown(f"**{tr(lang, 'features_analyzed')}**")
        visible_features = FEATURE_COLUMNS
        if st.session_state.get("train_df") is not None:
            visible_features = feature_columns_from_dataframe(st.session_state.train_df)
        for col in visible_features:
            st.markdown(f"- `{col}`")

        st.markdown("---")
        st.markdown(f"**{tr(lang, 'pqc_policy')}**")
        st.markdown(f"- {tr(lang, 'normal_policy')}")
        st.markdown(f"- {tr(lang, 'anomaly_policy')}")
        st.caption(tr(lang, "pqc_simulation_note"))

    return {
        "lang": lang,
        "live_sim": live_sim,
        "sim_delay": sim_delay,
        "seed_mode": seed_mode,
        "fixed_seed": int(fixed_seed),
        "contamination": (
            "auto" if contamination_mode == "auto" else float(contamination_value)
        ),
        "risk_policy_mode": risk_policy_mode,
        "low_threshold": float(low_threshold),
        "high_threshold": float(high_threshold),
        "medium_streak_n": int(medium_streak_n),
    }


def render_train_input(settings: dict[str, Any]) -> None:
    lang = settings["lang"]
    st.markdown(
        f'<p class="section-header">{tr(lang, "training_csv")}</p>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        tr(lang, "upload_training_csv"),
        type=["csv"],
        help=tr(lang, "csv_help"),
        key="train_csv_uploader",
    )

    if uploaded is not None and uploaded.name != st.session_state.last_train_upload:
        try:
            raw_df = pd.read_csv(uploaded, low_memory=False)
            train_df = standardize_flow_dataframe(raw_df)
            st.session_state.train_df = train_df
            st.session_state.test_df = None
            st.session_state.uploaded_test_df = None
            st.session_state.pipeline_result = None
            st.session_state.live_logs = []
            st.session_state.live_rows = []
            st.session_state.live_context = None
            st.session_state.stop_requested = False
            st.session_state.trained_detector = None
            st.session_state.trained_model_config = None
            st.session_state.last_train_upload = uploaded.name
            st.session_state.last_test_upload = None
            st.success(
                tr(
                    lang,
                    "loaded_training",
                    rows=len(train_df),
                    name=uploaded.name,
                )
            )
        except Exception as exc:
            st.error(str(exc))

    if st.session_state.train_df is not None:
        train_col, info_col = st.columns([1, 3])
        with train_col:
            train_clicked = st.button(
                tr(lang, "train_model"),
                use_container_width=True,
                disabled=st.session_state.live_context is not None,
            )
        with info_col:
            if st.session_state.trained_detector is None:
                st.info(tr(lang, "train_after_upload"))
            elif not model_matches_settings(settings):
                st.warning(tr(lang, "params_changed"))
            else:
                config = st.session_state.trained_model_config
                st.caption(
                    tr(
                        lang,
                        "model_trained_caption",
                        contamination=config["contamination"],
                        random_state=config["random_state"],
                    )
                )

        if train_clicked:
            train_current_model(settings)

        with st.expander(tr(lang, "preview_training"), expanded=False):
            st.dataframe(
                st.session_state.train_df.head(10),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(
                tr(lang, "total_training_rows", rows=len(st.session_state.train_df))
            )


def render_test_input(settings: dict[str, Any]) -> None:
    lang = settings["lang"]
    st.markdown(
        f'<p class="section-header">{tr(lang, "test_data")}</p>',
        unsafe_allow_html=True,
    )
    if st.session_state.train_df is None:
        st.info(tr(lang, "upload_train_first"))
        return

    source = st.radio(
        tr(lang, "test_data_source"),
        ["simulate_train", "upload_test"],
        horizontal=True,
        format_func=lambda value: tr(lang, "simulate_from_train")
        if value == "simulate_train"
        else tr(lang, "upload_test_csv"),
    )

    if source == "simulate_train":
        col_count, col_action = st.columns([1, 2])
        with col_count:
            n_samples = st.slider(
                tr(lang, "simulated_test_rows"),
                50,
                1000,
                200,
                step=50,
            )
        with col_action:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(tr(lang, "generate_test_data"), use_container_width=True):
                seed = resolve_random_state(settings)
                st.session_state.test_df = generate_simulated_test_data(
                    st.session_state.train_df,
                    n_samples=n_samples,
                    random_state=seed,
                )
                reset_results()
                st.success(tr(lang, "generated_from_train", rows=n_samples))
    else:
        uploaded = st.file_uploader(
            tr(lang, "upload_test_csv"),
            type=["csv"],
            help=tr(lang, "csv_help"),
            key="test_csv_uploader",
        )
        if uploaded is not None and uploaded.name != st.session_state.last_test_upload:
            try:
                raw_df = pd.read_csv(uploaded, low_memory=False)
                test_df = standardize_flow_dataframe(raw_df)
                st.session_state.uploaded_test_df = test_df
                st.session_state.test_df = test_df
                reset_results()
                st.session_state.last_test_upload = uploaded.name
                st.success(
                    tr(lang, "loaded_test", rows=len(test_df), name=uploaded.name)
                )
            except Exception as exc:
                st.error(str(exc))

        if st.session_state.uploaded_test_df is not None:
            restore_col, restore_info = st.columns([1, 2])
            with restore_col:
                if st.button(tr(lang, "use_uploaded_test"), use_container_width=True):
                    st.session_state.test_df = st.session_state.uploaded_test_df.copy()
                    reset_results()
                    st.success(tr(lang, "using_uploaded_test"))
            with restore_info:
                st.caption(tr(lang, "loaded_test", rows=len(st.session_state.uploaded_test_df), name=st.session_state.last_test_upload))

            col_count, col_action = st.columns([1, 2])
            with col_count:
                n_samples = st.slider(
                    tr(lang, "simulated_rows_from_test"),
                    50,
                    1000,
                    200,
                    step=50,
                )
            with col_action:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(tr(lang, "simulate_from_test"), use_container_width=True):
                    seed = resolve_random_state(settings)
                    st.session_state.test_df = generate_simulated_test_data(
                        st.session_state.uploaded_test_df,
                        n_samples=n_samples,
                        random_state=seed,
                    )
                    reset_results()
                    st.success(tr(lang, "generated_from_test", rows=n_samples))

    if st.session_state.test_df is not None:
        with st.expander(tr(lang, "preview_test"), expanded=False):
            st.dataframe(
                st.session_state.test_df.head(10),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(tr(lang, "total_test_rows", rows=len(st.session_state.test_df)))


def render_run_section(settings: dict[str, Any]) -> None:
    lang = settings["lang"]
    st.markdown(
        f'<p class="section-header">{tr(lang, "detection")}</p>',
        unsafe_allow_html=True,
    )
    active = st.session_state.live_context is not None

    run_col, stop_col, info_col = st.columns([1, 1, 3])
    with run_col:
        run_clicked = st.button(
            tr(lang, "run_test"),
            type="primary",
            use_container_width=True,
            disabled=not can_run_detection() or not model_matches_settings(settings) or active,
        )
    with stop_col:
        st.button(
            tr(lang, "stop_test"),
            use_container_width=True,
            disabled=not active,
            on_click=request_stop,
        )
    with info_col:
        if st.session_state.train_df is None:
            st.info(tr(lang, "upload_training_begin"))
        elif st.session_state.trained_detector is None:
            st.info(tr(lang, "click_train_before_test"))
        elif not model_matches_settings(settings):
            st.warning(tr(lang, "params_changed"))
        elif st.session_state.test_df is None:
            st.info(tr(lang, "prepare_test_data"))
        elif active:
            context = st.session_state.live_context
            st.caption(
                tr(
                    lang,
                    "running_test",
                    done=context["index"],
                    total=context["configured_total"],
                )
            )
        else:
            st.caption(
                tr(
                    lang,
                    "ready",
                    train_rows=len(st.session_state.train_df),
                    test_rows=len(st.session_state.test_df),
                )
            )

    if run_clicked:
        start_detection(settings)


def start_detection(settings: dict[str, Any]) -> None:
    reset_results()
    st.session_state.stop_requested = False

    if settings["live_sim"]:
        start_live_detection(settings)
    else:
        run_batch_detection(settings)


def train_current_model(settings: dict[str, Any]) -> None:
    lang = settings["lang"]
    train_df, X_train_all, y_train = dataframe_to_arrays(st.session_state.train_df)
    feature_columns = feature_columns_from_dataframe(train_df)
    if y_train is not None:
        normal_mask = y_train == 1
        if not normal_mask.any():
            st.error("Training CSV has labels but no normal/BENIGN rows for one-class training.")
            return
        X_train = X_train_all[normal_mask]
    else:
        X_train = X_train_all
    random_state = resolve_random_state(settings)
    contamination = settings["contamination"]
    with st.spinner(tr(lang, "training_spinner")):
        detector, _ = train_detector(
            X_train,
            random_state=random_state,
            contamination=contamination,
            feature_columns=feature_columns,
        )
    st.session_state.trained_detector = detector
    st.session_state.trained_model_config = build_model_config(
        settings,
        random_state,
    )
    reset_results()
    st.success(
        tr(
            lang,
            "trained_success",
            contamination=contamination,
            random_state=random_state,
        )
    )


def run_batch_detection(settings: dict[str, Any]) -> None:
    lang = st.session_state.get("ui_lang", "en")
    feature_columns = st.session_state.trained_detector.feature_columns
    _, X_train, _ = dataframe_to_arrays(
        st.session_state.train_df,
        feature_columns=feature_columns,
    )
    _, X_test, y_test = dataframe_to_arrays(
        st.session_state.test_df,
        feature_columns=feature_columns,
    )
    with st.spinner(tr(lang, "running_spinner")):
        result = run_detection_pipeline(
            X_train,
            X_test=X_test,
            y_test=y_test,
            detector=st.session_state.trained_detector,
            language=lang,
            risk_policy_mode=settings["risk_policy_mode"],
            low_threshold=settings["low_threshold"],
            high_threshold=settings["high_threshold"],
            medium_streak_n=settings["medium_streak_n"],
        )
    st.session_state.pipeline_result = result
    st.session_state.live_logs = result.logs
    st.session_state.live_rows = result.rows


def start_live_detection(settings: dict[str, Any]) -> None:
    lang = st.session_state.get("ui_lang", "en")
    detector = st.session_state.trained_detector
    _, X_test, y_test = dataframe_to_arrays(
        st.session_state.test_df,
        feature_columns=detector.feature_columns,
    )
    predictions = detector.predict_with_scores(X_test)

    st.session_state.pipeline_result = PipelineResult(
        scores=pd.Series([], dtype=float).to_numpy(),
        labels=pd.Series([], dtype=int).to_numpy(),
    )
    st.session_state.live_logs = []
    st.session_state.live_rows = []
    st.session_state.live_context = {
        "predictions": predictions,
        "pqc": PQCSimulator(),
        "index": 0,
        "configured_total": len(X_test),
        "y_test": y_test,
        "policy_state": RiskPolicyState(),
        "policy_labels": [],
        "policy_scores": [],
        "risk_policy_mode": settings["risk_policy_mode"],
        "low_threshold": settings["low_threshold"],
        "high_threshold": settings["high_threshold"],
        "medium_streak_n": settings["medium_streak_n"],
        "language": lang,
        "delay": st.session_state.get("sim_delay", 0.0),
    }


def advance_live_detection(settings: dict[str, Any]) -> None:
    lang = settings["lang"]
    context = st.session_state.live_context
    if context is None:
        return

    context["delay"] = settings["sim_delay"]
    context["language"] = lang
    result = st.session_state.pipeline_result

    progress = st.progress(
        context["index"] / max(context["configured_total"], 1),
        text=tr(
            lang,
            "testing_row",
            done=context["index"],
            total=context["configured_total"],
        ),
    )
    status_box = st.empty()
    log_box = st.empty()

    if st.session_state.stop_requested:
        finalize_live_detection(stopped=True, lang=lang)
        progress.progress(1.0, text=tr(lang, "test_stopped"))
        return

    predictions = context["predictions"]
    if context["index"] >= len(predictions):
        finalize_live_detection(stopped=False, lang=lang)
        progress.progress(1.0, text=tr(lang, "detection_complete"))
        return

    chunk_size = 50 if context["delay"] == 0 else 20
    last_sample = None
    while context["index"] < len(predictions) and chunk_size > 0:
        idx = context["index"]
        pred = predictions[idx]
        sample, batch_logs, policy_label = build_policy_sample(
            idx,
            pred,
            context["pqc"],
            context["policy_state"],
            risk_policy_mode=context["risk_policy_mode"],
            low_threshold=context["low_threshold"],
            high_threshold=context["high_threshold"],
            medium_streak_n=context["medium_streak_n"],
            language=lang,
        )

        result.rows.append(sample)
        result.logs.extend(batch_logs)
        st.session_state.live_rows.append(sample)
        st.session_state.live_logs.extend(batch_logs)
        context["policy_labels"].append(policy_label)
        context["policy_scores"].append(pred.score)
        context["index"] += 1
        chunk_size -= 1
        last_sample = sample

    done = context["index"]
    progress.progress(
        done / max(context["configured_total"], 1),
        text=tr(
            lang,
            "testing_row",
            done=done,
            total=context["configured_total"],
        ),
    )
    if last_sample is not None:
        pill_class = "pill-anomaly" if last_sample.status == "ANOMALY" else "pill-normal"
        display_status = localized_status(last_sample.status, lang)
        status_box.markdown(
            f'<span class="status-pill {pill_class}">'
            f"{tr(lang, 'sample_status', sample_id=last_sample.sample_id, status=display_status, action=last_sample.pqc_action)}"
            f"</span>",
            unsafe_allow_html=True,
        )
    log_box.markdown(
        format_log_html(st.session_state.live_logs[-12:]),
        unsafe_allow_html=True,
    )

    if done >= context["configured_total"]:
        finalize_live_detection(stopped=False, lang=lang)
    else:
        if context["delay"] > 0:
            time.sleep(context["delay"])
        st.rerun()


def finalize_live_detection(stopped: bool, lang: str) -> None:
    context = st.session_state.live_context
    result = st.session_state.pipeline_result
    if context is None or result is None:
        return

    if stopped:
        stop_log = build_log_entry("INFO", tr(lang, "stopped_log"))
        result.logs.append(stop_log)
        st.session_state.live_logs.append(stop_log)

    anomaly_count = sum(1 for row in result.rows if row.status == "ANOMALY")
    low_count = sum(1 for row in result.rows if row.risk_level == "LOW")
    medium_count = sum(1 for row in result.rows if row.risk_level == "MEDIUM")
    high_count = sum(1 for row in result.rows if row.risk_level == "HIGH")
    result.scores = pd.Series(context["policy_scores"], dtype=float).to_numpy()
    result.labels = pd.Series(context["policy_labels"], dtype=int).to_numpy()
    if context["y_test"] is not None and len(result.labels) > 0:
        result.metrics = evaluate_predictions(
            context["y_test"][: len(result.labels)],
            result.labels,
        )
    elif len(result.labels) == 0:
        result.metrics = {}
    result.summary = {
        "total": len(result.rows),
        "configured_total": context["configured_total"],
        "anomalies": anomaly_count,
        "normal": len(result.rows) - anomaly_count,
        "low_risk": low_count,
        "medium_risk": medium_count,
        "high_risk": high_count,
        "renegotiations": context["pqc"].state.renegotiation_count,
        "direct_renegotiations": context["policy_state"].direct_renegotiations,
        "streak_renegotiations": context["policy_state"].streak_renegotiations,
        "final_algorithm": context["pqc"].current_algorithm,
        "stopped": stopped,
    }
    st.session_state.live_context = None
    st.session_state.stop_requested = False


def render_results() -> None:
    lang = st.session_state.get("ui_lang", "en")
    result = st.session_state.pipeline_result
    if result is None or not result.summary:
        return

    st.markdown(
        f'<p class="section-header">{tr(lang, "detection_results")}</p>',
        unsafe_allow_html=True,
    )

    s = result.summary
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric(tr(lang, "processed"), f"{s['total']} / {s['configured_total']}")
    m2.metric(tr(lang, "normal"), s["normal"])
    m3.metric(tr(lang, "anomalies"), s["anomalies"])
    m4.metric(tr(lang, "false_positive_rate"), format_rate(result.metrics, "false_positive_rate"))
    m5.metric(tr(lang, "false_negative_rate"), format_rate(result.metrics, "false_negative_rate"))

    status = tr(lang, "stopped") if s.get("stopped") else tr(lang, "complete")
    st.markdown(
        f"**{tr(lang, 'test_status')}:** `{status}` | "
        f"**{tr(lang, 'current_pqc_mode')}:** `{s['final_algorithm']}` | "
        f"**{tr(lang, 'key_renegotiations')}:** `{s['renegotiations']}`",
        unsafe_allow_html=True,
    )
    st.caption(
        tr(
            lang,
            "risk_level_summary",
            low=s.get("low_risk", 0),
            medium=s.get("medium_risk", 0),
            high=s.get("high_risk", 0),
        )
    )
    st.caption(
        tr(
            lang,
            "renegotiation_summary",
            direct=s.get("direct_renegotiations", 0),
            streak=s.get("streak_renegotiations", 0),
        )
    )

    display_rows = result.rows[:MAX_RESULT_TABLE_ROWS]
    results_df = results_to_dataframe(display_rows, language=lang)
    if not results_df.empty:
        if len(result.rows) > len(display_rows):
            st.caption(
                display_limit_message(
                    lang,
                    shown=len(display_rows),
                    total=len(result.rows),
                    item="rows",
                )
            )
        st.dataframe(
            styled_results_table(results_df, language=lang),
            use_container_width=True,
            hide_index=True,
            height=min(420, 38 + len(results_df) * 35),
        )


def render_visualizations() -> None:
    lang = st.session_state.get("ui_lang", "en")
    result = st.session_state.pipeline_result
    if result is None or len(result.scores) == 0 or not result.summary:
        return

    st.markdown(
        f'<p class="section-header">{tr(lang, "visual_analytics")}</p>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        chart_scores, chart_labels = sample_for_display(
            result.scores,
            result.labels,
            MAX_CHART_POINTS,
        )
        if len(result.scores) > len(chart_scores):
            st.caption(
                display_limit_message(
                    lang,
                    shown=len(chart_scores),
                    total=len(result.scores),
                    item="points",
                )
            )
        score_fig = create_anomaly_score_figure(chart_scores, chart_labels)
        score_fig.update_layout(
            title=tr(lang, "score_chart"),
            xaxis_title=tr(lang, "score_x"),
            yaxis_title=tr(lang, "score_y"),
        )
        for annotation in score_fig.layout.annotations:
            annotation.text = tr(lang, "median")
        st.plotly_chart(score_fig, use_container_width=True)
    with col_b:
        status_fig = create_status_count_figure(
            result.summary["normal"],
            result.summary["anomalies"],
        )
        status_fig.update_layout(
            title=tr(lang, "status_chart"),
            yaxis_title=tr(lang, "count"),
        )
        status_fig.update_xaxes(
            ticktext=[tr(lang, "normal"), tr(lang, "anomalies")],
            tickvals=["Normal", "Anomaly"],
        )
        st.plotly_chart(status_fig, use_container_width=True)

    if result.metrics:
        with st.expander(tr(lang, "model_metrics"), expanded=False):
            st.text(result.metrics.get("classification_report", ""))
            cols = st.columns(3)
            cols[0].metric(tr(lang, "accuracy"), format_rate(result.metrics, "accuracy"))
            cols[1].metric(
                tr(lang, "false_positive_rate"),
                format_rate(result.metrics, "false_positive_rate"),
            )
            cols[2].metric(
                tr(lang, "false_negative_rate"),
                format_rate(result.metrics, "false_negative_rate"),
            )


def render_event_log() -> None:
    lang = st.session_state.get("ui_lang", "en")
    result = st.session_state.pipeline_result
    if result is None or not result.logs:
        return

    st.markdown(
        f'<p class="section-header">{tr(lang, "event_log")}</p>',
        unsafe_allow_html=True,
    )
    logs = st.session_state.live_logs or result.logs
    display_logs = logs[-MAX_EVENT_LOG_DISPLAY:]
    if len(logs) > len(display_logs):
        st.caption(
            display_limit_message(
                lang,
                shown=len(display_logs),
                total=len(logs),
                item="logs",
            )
        )
    st.markdown(
        f'<div style="max-height:320px;overflow-y:auto;padding:8px;'
        f'border:1px solid #dde4ea;border-radius:8px;background:#fafbfc;">'
        f"{format_log_html(display_logs)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.download_button(
        tr(lang, "download_log"),
        data="\n".join(logs),
        file_name="pqc_event_log.txt",
        mime="text/plain",
    )


def can_run_detection() -> bool:
    return (
        st.session_state.train_df is not None
        and st.session_state.test_df is not None
        and st.session_state.trained_detector is not None
    )


def reset_results() -> None:
    st.session_state.pipeline_result = None
    st.session_state.live_logs = []
    st.session_state.live_rows = []
    st.session_state.live_context = None
    st.session_state.stop_requested = False


def request_stop() -> None:
    st.session_state.stop_requested = True


def resolve_random_state(settings: dict[str, Any]) -> int:
    if settings["seed_mode"] == "Dynamic":
        return int(time.time_ns() % 2_147_483_647)
    return int(settings["fixed_seed"])


def build_model_config(settings: dict[str, Any], random_state: int) -> dict[str, Any]:
    feature_columns = []
    if st.session_state.train_df is not None:
        feature_columns = feature_columns_from_dataframe(st.session_state.train_df)
    return {
        "contamination": settings["contamination"],
        "seed_mode": settings["seed_mode"],
        "fixed_seed": settings["fixed_seed"],
        "random_state": random_state,
        "feature_columns": feature_columns,
    }


def model_matches_settings(settings: dict[str, Any]) -> bool:
    config = st.session_state.trained_model_config
    if config is None:
        return False
    detector = st.session_state.trained_detector
    if detector is None or not hasattr(detector, "preprocessor"):
        return False
    if config["contamination"] != settings["contamination"]:
        return False
    if config["seed_mode"] != settings["seed_mode"]:
        return False
    if settings["seed_mode"] == "Fixed" and config["fixed_seed"] != settings["fixed_seed"]:
        return False
    if st.session_state.train_df is not None:
        current_features = feature_columns_from_dataframe(st.session_state.train_df)
        if config.get("feature_columns") != current_features:
            return False
    return True


def format_rate(metrics: dict, key: str) -> str:
    if key not in metrics:
        return "N/A"
    return f"{metrics[key]:.1%}"


def localized_status(status: str, lang: str) -> str:
    if lang != "zh":
        return status
    return "异常" if status == "ANOMALY" else "正常"


def sample_for_display(scores, labels, max_points: int):
    if len(scores) <= max_points:
        return scores, labels
    indices = pd.Series(range(len(scores))).sample(
        n=max_points,
        random_state=42,
    ).sort_values().to_numpy()
    return scores[indices], labels[indices]


def display_limit_message(lang: str, shown: int, total: int, item: str) -> str:
    if lang == "zh":
        names = {
            "rows": "结果行",
            "points": "图表点",
            "logs": "日志",
        }
        return f"为保证页面流畅，仅显示 {shown} / {total} 条{names.get(item, item)}；统计指标仍基于全量数据。"
    names = {
        "rows": "result rows",
        "points": "chart points",
        "logs": "log entries",
    }
    return (
        f"Showing {shown} / {total} {names.get(item, item)} for UI performance; "
        "metrics still use the full dataset."
    )


def main() -> None:
    init_session_state()
    settings = render_sidebar()
    render_header(settings["lang"])
    render_train_input(settings)
    render_test_input(settings)
    render_run_section(settings)
    advance_live_detection(settings)
    render_results()
    render_visualizations()
    render_event_log()


if __name__ == "__main__":
    main()
