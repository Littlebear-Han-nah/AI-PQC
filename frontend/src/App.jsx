import { useCallback, useState } from 'react';
import { Layout, Row, Col, Card, Button, Progress, message } from 'antd';
import { ThunderboltOutlined, SafetyOutlined } from '@ant-design/icons';

import ControlPanel from './components/ControlPanel';
import DataInput from './components/DataInput';
import StatsCards from './components/StatsCards';
import ResultsTable from './components/ResultsTable';
import ChartsPanel from './components/ChartsPanel';
import EventLog from './components/EventLog';
import PQCStatus from './components/PQCStatus';
import RowDetailModal from './components/RowDetailModal';
import AnomalyReplayModal from './components/AnomalyReplayModal';
import { runDetection } from './api/client';

const { Sider, Content } = Layout;

export default function App() {
  const [pqcMode, setPqcMode] = useState('Kyber512');
  const [sampleCount, setSampleCount] = useState(200);
  const [liveSim, setLiveSim] = useState(true);
  const [delay, setDelay] = useState(0.05);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [progress, setProgress] = useState(0);

  const [result, setResult] = useState(null);
  const [liveRows, setLiveRows] = useState([]);
  const [liveLogs, setLiveLogs] = useState([]);
  const [currentPqcMode, setCurrentPqcMode] = useState('Kyber512');
  const [systemStatus, setSystemStatus] = useState('secure');
  const [liveSummary, setLiveSummary] = useState(null);

  // Row detail modal
  const [detailRow, setDetailRow] = useState(null);
  const [detailOpen, setDetailOpen] = useState(false);

  // Anomaly replay modal
  const [replayRow, setReplayRow] = useState(null);
  const [replayOpen, setReplayOpen] = useState(false);

  const applyResult = useCallback((data) => {
    setResult(data);
    setLiveRows(data.rows || []);
    setLiveLogs(data.logs || []);
    setCurrentPqcMode(data.summary?.final_algorithm || pqcMode);
    setSystemStatus(data.summary?.system_status || 'secure');
    setLiveSummary(data.summary);
  }, [pqcMode]);

  const handleDetect = async () => {
    if (!datasetInfo) {
      message.warning('请先生成或上传数据集');
      return;
    }

    setDetecting(true);
    setProgress(0);
    setLiveRows([]);
    setLiveLogs([]);
    setResult(null);
    setLiveSummary(null);
    setCurrentPqcMode(pqcMode);
    setSystemStatus('secure');

    try {
      if (liveSim) {
        await runDetection({
          defaultPqcMode: pqcMode,
          live: true,
          delay,
          onEvent: (event) => {
            if (event.type === 'init') {
              setProgress(5);
            }
            if (event.type === 'sample') {
              setLiveRows((prev) => {
                const next = [...prev, event.sample];
                const anomalies = next.filter((r) => r.status === 'ANOMALY').length;
                setLiveSummary({
                  total: next.length,
                  normal: next.length - anomalies,
                  anomalies,
                  renegotiations: event.renegotiations,
                });
                return next;
              });
              setLiveLogs((prev) => [...prev, ...event.logs]);
              setCurrentPqcMode(event.pqc_mode);
              setProgress(Math.round(event.progress * 100));
              if (event.sample.status === 'ANOMALY') {
                setSystemStatus('alert');
              }
            }
          },
          onComplete: (data) => {
            applyResult(data);
            setProgress(100);
            message.success('检测完成');
          },
        });
      } else {
        const data = await runDetection({ defaultPqcMode: pqcMode, live: false, delay });
        applyResult(data);
        setProgress(100);
        message.success('检测完成');
      }
    } catch (err) {
      message.error(err.message || '检测失败，请确认后端已启动');
    } finally {
      setDetecting(false);
    }
  };

  const displaySummary = liveSummary || result?.summary;
  const displayRows    = liveRows.length ? liveRows : result?.rows || [];
  const displayLogs    = liveLogs.length ? liveLogs : result?.logs || [];
  const displayScores  = result?.scores || liveRows.map((r) => r.score);
  const displayLabels  = result?.labels || liveRows.map((r) => (r.status === 'ANOMALY' ? -1 : 1));

  return (
    <div className="soc-layout">
      {/* ── Header ── */}
      <div className="soc-header">
        <div>
          <h1 className="soc-title">
            <span className="soc-title-icon">
              <SafetyOutlined style={{ fontSize: 18 }} />
            </span>
            AI + PQC 安全监控系统
          </h1>
          <p className="soc-subtitle">
            网络流量 → Isolation Forest 异常检测 → 后量子密码响应
          </p>
        </div>
        <div style={{
          fontSize: 12, color: '#9ca3af', textAlign: 'right', lineHeight: 1.6,
        }}>
          <div style={{ fontWeight: 600, color: '#6b7280' }}>Post-Quantum Security Lab</div>
          <div>Kyber · ML-KEM · NIST PQC</div>
        </div>
      </div>

      <Layout style={{ background: 'transparent', gap: 16 }}>
        <Sider width={270} style={{ background: 'transparent' }} breakpoint="lg" collapsedWidth={0}>
          <ControlPanel
            pqcMode={pqcMode}
            setPqcMode={setPqcMode}
            sampleCount={sampleCount}
            setSampleCount={setSampleCount}
            liveSim={liveSim}
            setLiveSim={setLiveSim}
            delay={delay}
            setDelay={setDelay}
          />
        </Sider>

        <Content>
          {/* PQC Status Banner */}
          <PQCStatus mode={currentPqcMode} systemStatus={systemStatus} detecting={detecting} />

          {/* Data input + Run control */}
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={15}>
              <DataInput
                sampleCount={sampleCount}
                onDatasetReady={setDatasetInfo}
                datasetInfo={datasetInfo}
                loading={loading}
                setLoading={setLoading}
              />
            </Col>
            <Col xs={24} lg={9}>
              <Card className="panel-card" title="检测控制" size="small">
                <Button
                  type="primary"
                  block
                  className="run-btn"
                  icon={<ThunderboltOutlined />}
                  loading={detecting}
                  disabled={!datasetInfo}
                  onClick={handleDetect}
                >
                  开始检测（Run Detection）
                </Button>
                {detecting && (
                  <Progress
                    percent={progress}
                    status="active"
                    strokeColor={{ from: '#1677ff', to: '#4096ff' }}
                    style={{ marginTop: 12 }}
                  />
                )}
                {!detecting && displaySummary && (
                  <div style={{
                    marginTop: 10, fontSize: 12, color: '#6b7280',
                    background: '#f8fafc', borderRadius: 8, padding: '8px 12px',
                    border: '1px solid #e5e9f2',
                  }}>
                    上次检测：<strong style={{ color: '#1677ff' }}>{displaySummary.total}</strong> 条样本，
                    异常 <strong style={{ color: '#ef4444' }}>{displaySummary.anomalies}</strong> 条，
                    重协商 <strong style={{ color: '#f59e0b' }}>{displaySummary.renegotiations}</strong> 次
                  </div>
                )}
              </Card>
            </Col>
          </Row>

          {/* Stats */}
          <div style={{ marginTop: 16 }}>
            <div className="section-title">检测结果统计</div>
            <StatsCards summary={displaySummary} />
          </div>

          {/* Table + Charts */}
          <Row gutter={[16, 16]} style={{ marginTop: 4 }}>
            <Col xs={24} xl={15}>
              <Card
                className="panel-card"
                title={
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    流量数据表
                    <span style={{
                      fontSize: 11, fontWeight: 500, color: '#6b7280',
                      background: '#f1f5f9', borderRadius: 99, padding: '1px 8px',
                    }}>
                      点击行查看详情 · ▶ 回放检测过程
                    </span>
                  </span>
                }
                size="small"
              >
                <ResultsTable
                  rows={displayRows}
                  loading={detecting && !displayRows.length}
                  onRowClick={(row) => {
                    setDetailRow(row);
                    setDetailOpen(true);
                  }}
                  onReplayClick={(row) => {
                    setReplayRow(row);
                    setReplayOpen(true);
                  }}
                />
              </Card>
            </Col>
            <Col xs={24} xl={9}>
              <Card className="panel-card" title="AI 分析可视化" size="small">
                <ChartsPanel
                  scores={displayScores}
                  labels={displayLabels}
                  summary={displaySummary}
                />
              </Card>
              <div style={{ marginTop: 16 }}>
                <EventLog logs={displayLogs} />
              </div>
            </Col>
          </Row>
        </Content>
      </Layout>

      {/* ── Modals ── */}
      <RowDetailModal
        row={detailRow}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      />
      <AnomalyReplayModal
        row={replayRow}
        open={replayOpen}
        onClose={() => setReplayOpen(false)}
      />
    </div>
  );
}
