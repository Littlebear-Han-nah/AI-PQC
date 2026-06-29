# AI + PQC Security Monitoring — Streamlit Demo UI

Presentation-ready dashboard for the AI + Post-Quantum Cryptography research prototype.

## Quick Start

```bash
cd ~/AI_PQC_UI
pip install -r requirements.txt
python api.py
```

```bash
cd ~/AI_PQC_UI/frontend
npm install
npm run dev
```

## Features

- Upload CSV or generate synthetic network flows
- Isolation Forest anomaly detection
- PQC response: Kyber512 (normal) / Kyber768 + renegotiation (anomaly)
- Color-coded results table and event log
- Plotly charts: anomaly scores + normal vs anomaly counts
- Live simulation mode with progress bar

## Project Structure

| File | Description |
|------|-------------|
| `app.py` | Streamlit dashboard |
| `model.py` | Isolation Forest wrapper |
| `pqc.py` | Simulated PQC module |
| `data.py` | Dataset loading & synthesis |
| `utils.py` | Pipeline + visualization helpers |

## CSV Format

Required columns: `duration`, `packet_count`, `byte_size`, `src_bytes`, `dst_bytes`, `flow_rate`

Optional: `label` (-1 = anomaly, 1 = normal) for evaluation metrics.
