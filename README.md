# AI + PQC 安全监控系统

React + Ant Design + ECharts 前端 + FastAPI 后端的学术演示平台。

## 系统架构

```
网络流量数据 → Isolation Forest 异常检测 → 风险评分 → PQC 策略决策 → Kyber512 / Kyber768
```

## 快速启动

### 1. 安装依赖

```bash
cd ~/AI_PQC_UI
pip install -r requirements.txt
cd frontend && npm install
```

### 2. 启动后端（终端 1）

```bash
cd ~/AI_PQC_UI
python api.py
```

API 地址：http://127.0.0.1:8000

### 3. 启动前端（终端 2）

```bash
cd ~/AI_PQC_UI/frontend
npm run dev
```

界面地址：http://127.0.0.1:5173

## 答辩演示流程

1. 左侧配置面板：设置合成数据数量、开启实时模拟
2. 点击 **生成合成数据**
3. 点击红色 **开始检测** 按钮
4. 观察：
   - PQC 模式大字切换（Kyber512 ↔ Kyber768）
   - 统计卡片数字动画
   - 流量表格异常行高亮
   - ECharts 异常评分图 + 饼图
   - 事件日志实时滚动
5. 点击任意表格行 → 查看 AI 异常判定原因

## 项目结构

```
AI_PQC_UI/
├── api.py              # FastAPI 后端
├── data.py             # 数据集
├── model.py            # Isolation Forest
├── pqc.py              # PQC 模拟
├── utils.py            # 检测流水线
├── requirements.txt
└── frontend/
    ├── src/App.jsx     # 主界面
    └── src/components/ # UI 组件
```

## CSV 格式

必需字段：`duration`, `packet_count`, `byte_size`, `src_bytes`, `dst_bytes`, `flow_rate`

可选：`label`（-1=异常, 1=正常）
