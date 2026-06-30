import { useEffect, useRef, useState } from 'react';
import { Modal, Button, Progress, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  RadarChartOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';

// ─── Phase durations (ms) ────────────────────────────────────────────────────
const PHASES = [
  { id: 0, label: '数据接收', icon: <DatabaseOutlined />,    duration: 900 },
  { id: 1, label: 'AI 推理',  icon: <RadarChartOutlined />, duration: 1600 },
  { id: 2, label: '判决结果', icon: <ThunderboltOutlined />, duration: 800 },
  { id: 3, label: 'PQC 响应', icon: <SafetyOutlined />,     duration: 1000 },
];

const TOTAL_DURATION = PHASES.reduce((s, p) => s + p.duration, 0);

// ─── Sub-components ──────────────────────────────────────────────────────────

function MetricRow({ label, value, highlight }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '7px 0',
      borderBottom: '1px solid #f1f5f9',
    }}>
      <span style={{ color: '#6b7280', fontSize: 13 }}>{label}</span>
      <span style={{
        fontSize: 13, fontWeight: 600,
        color: highlight || '#111827',
        fontFamily: 'monospace',
      }}>{value}</span>
    </div>
  );
}

function RiskBar({ value, color, label }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const t = setTimeout(() => setWidth(value * 100), 80);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
        <span style={{ fontSize: 12, color: '#6b7280', fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>{(value * 100).toFixed(1)}%</span>
      </div>
      <div style={{
        height: 10, borderRadius: 99, background: '#f1f5f9', overflow: 'hidden',
      }}>
        <div
          className="score-bar"
          style={{ width: `${width}%`, background: color }}
        />
      </div>
    </div>
  );
}

// ─── Timeline stepper ────────────────────────────────────────────────────────
function ReplayTimeline({ phase }) {
  return (
    <div className="replay-timeline">
      {PHASES.map((p, idx) => {
        const state = idx < phase ? 'done' : idx === phase ? 'active' : 'pending';
        return (
          <div key={p.id} className={`replay-step ${state}`}>
            <div className="replay-step-dot">
              {state === 'done' ? '✓' : idx + 1}
            </div>
            <div className="replay-step-label">{p.label}</div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Phase 0: Data Received ───────────────────────────────────────────────────
function PhaseData({ row }) {
  const features = [
    { label: 'duration (s)',   value: row.duration?.toFixed?.(3) },
    { label: 'packet_count',  value: row.packet_count },
    { label: 'byte_size (B)', value: row.byte_size },
    { label: 'src_bytes',     value: row.src_bytes },
    { label: 'dst_bytes',     value: row.dst_bytes },
    { label: 'flow_rate',     value: row.flow_rate?.toFixed?.(1) },
  ];
  return (
    <div className="replay-phase">
      <div style={{
        background: '#eff6ff', borderRadius: 10, padding: '10px 14px',
        border: '1px solid #bfdbfe', marginBottom: 14,
      }}>
        <div style={{ fontSize: 12, color: '#1677ff', fontWeight: 600, marginBottom: 4 }}>
          📡 流量样本 #{row.sample_id} 已接收
        </div>
        <div style={{ fontSize: 12, color: '#3b82f6' }}>
          正在解析数据包特征向量，准备输入 AI 模型...
        </div>
      </div>
      {features.map((f) => (
        <MetricRow key={f.label} label={f.label} value={f.value} />
      ))}
    </div>
  );
}

// ─── Phase 1: AI Inference ────────────────────────────────────────────────────
function PhaseInference({ row }) {
  const isAnomaly = row.status === 'ANOMALY';
  const risk = Number(row.risk) || 0;
  const scoreNorm = Math.abs(Number(row.score) || 0);
  // Normalize score to 0-1 for bar (scores typically -0.5 to 0.5)
  const scorePct = Math.min(Math.max((scoreNorm + 0.5), 0), 1);

  return (
    <div className="replay-phase">
      <div style={{
        background: '#fafafa', borderRadius: 10, padding: '10px 14px',
        border: '1px solid #e5e9f2', marginBottom: 16,
      }}>
        <div style={{ fontSize: 12, color: '#374151', fontWeight: 600, marginBottom: 4 }}>
          🤖 Isolation Forest 推理中
        </div>
        <div style={{ fontSize: 12, color: '#6b7280' }}>
          模型正在计算当前流量的异常路径长度，生成孤立评分...
        </div>
      </div>

      <RiskBar
        value={scorePct}
        color={isAnomaly ? '#ef4444' : '#22c55e'}
        label={`IF Score: ${row.score}`}
      />
      <RiskBar
        value={risk}
        color={risk > 0.6 ? '#ef4444' : risk > 0.4 ? '#f59e0b' : '#22c55e'}
        label={`Risk Score: ${row.risk}`}
      />

      <div style={{
        marginTop: 12,
        display: 'flex', gap: 8,
        fontSize: 12, color: '#6b7280',
        background: '#f8fafc', borderRadius: 8, padding: '8px 12px',
      }}>
        <span>阈值：</span>
        <code style={{ color: '#1677ff' }}>IF Score &lt; 0 → 可能异常</code>
        <span style={{ marginLeft: 'auto' }}>
          当前：<code style={{ color: isAnomaly ? '#ef4444' : '#22c55e' }}>{row.score}</code>
        </span>
      </div>
    </div>
  );
}

// ─── Phase 2: Decision ────────────────────────────────────────────────────────
function PhaseDecision({ row }) {
  const isAnomaly = row.status === 'ANOMALY';
  return (
    <div className="replay-phase" style={{ textAlign: 'center', padding: '8px 0' }}>
      <div className="decision-badge" style={{
        display: 'inline-flex', flexDirection: 'column', alignItems: 'center',
        padding: '20px 36px',
        borderRadius: 16,
        background: isAnomaly ? '#fff5f5' : '#f0fdf4',
        border: `2px solid ${isAnomaly ? '#ef4444' : '#22c55e'}`,
        marginBottom: 16,
      }}>
        <div style={{ fontSize: 36, marginBottom: 8 }}>{isAnomaly ? '⚠️' : '✅'}</div>
        <div style={{
          fontSize: 22, fontWeight: 800, letterSpacing: 1,
          color: isAnomaly ? '#ef4444' : '#22c55e',
        }}>
          {isAnomaly ? 'ANOMALY' : 'NORMAL'}
        </div>
        <div style={{ fontSize: 13, color: '#6b7280', marginTop: 6 }}>
          {row.label}
        </div>
      </div>
      <div style={{
        background: '#f8fafc', borderRadius: 10, padding: '12px 14px',
        border: '1px solid #e5e9f2', textAlign: 'left',
      }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 6 }}>
          AI 判定理由：
        </div>
        <div style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.65 }}>
          {row.explanation}
        </div>
      </div>
    </div>
  );
}

// ─── Phase 3: PQC Response ────────────────────────────────────────────────────
function PhasePQC({ row }) {
  const isAnomaly = row.status === 'ANOMALY';
  const upgraded = row.pqc_action === 'Kyber768';

  return (
    <div className="replay-phase">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 24, marginBottom: 20 }}>
        {/* Before */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8, fontWeight: 500 }}>初始状态</div>
          <div style={{
            padding: '10px 18px', borderRadius: 10, fontSize: 14, fontWeight: 700,
            background: '#dcfce7', color: '#22c55e', border: '1.5px solid #86efac',
          }}>Kyber512</div>
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 6 }}>Level 1 · Standard</div>
        </div>

        {/* Arrow */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{ fontSize: 22 }}>{upgraded ? '→' : '→'}</div>
          <div style={{
            fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 99,
            background: upgraded ? '#fee2e2' : '#dcfce7',
            color: upgraded ? '#ef4444' : '#22c55e',
          }}>
            {upgraded ? '升级' : '保持'}
          </div>
        </div>

        {/* After */}
        <div className="pqc-switch-anim" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 8, fontWeight: 500 }}>响应后</div>
          <div style={{
            padding: '10px 18px', borderRadius: 10, fontSize: 14, fontWeight: 700,
            background: upgraded ? '#fee2e2' : '#dcfce7',
            color: upgraded ? '#ef4444' : '#22c55e',
            border: `1.5px solid ${upgraded ? '#fca5a5' : '#86efac'}`,
          }}>
            {row.pqc_action}
          </div>
          <div style={{ fontSize: 11, color: '#6b7280', marginTop: 6 }}>
            {upgraded ? 'Level 3 · Enhanced' : 'Level 1 · Standard'}
          </div>
        </div>
      </div>

      <div style={{
        padding: '12px 14px', borderRadius: 10,
        background: upgraded ? '#fff5f5' : '#f0fdf4',
        border: `1px solid ${upgraded ? '#fecaca' : '#bbf7d0'}`,
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: upgraded ? '#ef4444' : '#22c55e', marginBottom: 6 }}>
          {upgraded ? '🔒 PQC 密钥重协商已触发' : '✅ 当前加密强度满足要求'}
        </div>
        <div style={{ fontSize: 13, color: '#4b5563', lineHeight: 1.6 }}>
          {upgraded
            ? `检测到异常流量（Risk: ${row.risk}），系统已自动将 KEM 算法从 Kyber512 升级至 Kyber768，密钥安全位数从 128-bit 提升至 192-bit，密钥重协商已完成。`
            : `当前流量风险评分（${row.risk}）在安全阈值内，Kyber512 加密方案维持不变，无需重协商。`
          }
        </div>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function AnomalyReplayModal({ row, open, onClose }) {
  const [phase, setPhase]       = useState(-1);   // -1 = not started
  const [playing, setPlaying]   = useState(false);
  const [elapsed, setElapsed]   = useState(0);
  const timerRef  = useRef(null);
  const elapsedRef = useRef(0);

  // ── helpers ──
  const reset = () => {
    clearInterval(timerRef.current);
    setPhase(-1);
    setPlaying(false);
    setElapsed(0);
    elapsedRef.current = 0;
  };

  const startFrom = (startElapsed, startPhase) => {
    setPlaying(true);
    let e = startElapsed;
    let p = startPhase;
    const TICK = 50;

    timerRef.current = setInterval(() => {
      e += TICK;
      elapsedRef.current = e;
      setElapsed(e);

      // figure out which phase we're in
      let acc = 0;
      let nextPhase = PHASES.length; // done
      for (let i = 0; i < PHASES.length; i++) {
        acc += PHASES[i].duration;
        if (e < acc) { nextPhase = i; break; }
      }

      if (nextPhase !== p) {
        p = nextPhase;
        setPhase(nextPhase >= PHASES.length ? PHASES.length - 1 : nextPhase);
      }

      if (e >= TOTAL_DURATION) {
        clearInterval(timerRef.current);
        setPlaying(false);
        setPhase(PHASES.length - 1);
      }
    }, TICK);
  };

  const handlePlay = () => {
    if (elapsed >= TOTAL_DURATION) { reset(); return; }
    if (phase === -1) {
      setPhase(0);
      startFrom(0, 0);
    } else {
      startFrom(elapsedRef.current, phase);
    }
  };

  const handlePause = () => {
    clearInterval(timerRef.current);
    setPlaying(false);
  };

  const handleReplay = () => {
    clearInterval(timerRef.current);
    setPhase(0);
    setElapsed(0);
    elapsedRef.current = 0;
    setPlaying(false);
    setTimeout(() => startFrom(0, 0), 50);
  };

  // Auto-start when modal opens
  useEffect(() => {
    if (open && row) {
      reset();
      setTimeout(() => { setPhase(0); startFrom(0, 0); }, 200);
    }
    return () => clearInterval(timerRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, row?.sample_id]);

  // Cleanup on close
  useEffect(() => {
    if (!open) reset();
  }, [open]);

  if (!row) return null;
  const isAnomaly = row.status === 'ANOMALY';
  const progressPct = Math.min((elapsed / TOTAL_DURATION) * 100, 100);

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{
            width: 32, height: 32, borderRadius: 9,
            background: isAnomaly ? '#fee2e2' : '#dcfce7',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            fontSize: 16,
          }}>
            {isAnomaly ? '⚠️' : '✅'}
          </span>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, lineHeight: 1.3 }}>
              Anomaly Replay — 样本 #{row.sample_id}
            </div>
            <div style={{ fontSize: 12, color: '#6b7280', fontWeight: 400 }}>
              {isAnomaly ? '异常流量检测回放' : '正常流量检测回放'}
            </div>
          </div>
        </div>
      }
      open={open}
      onCancel={() => { reset(); onClose(); }}
      footer={null}
      width={580}
      styles={{
        header: { borderBottom: '1px solid #e5e9f2', paddingBottom: 14 },
        body: { padding: '20px 24px' },
      }}
      destroyOnClose
    >
      {/* ── Timeline ── */}
      <ReplayTimeline phase={phase} />

      {/* ── Progress bar + controls ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18,
      }}>
        <div style={{ flex: 1 }}>
          <Progress
            percent={Math.round(progressPct)}
            size="small"
            strokeColor={isAnomaly ? '#ef4444' : '#22c55e'}
            trailColor="#f1f5f9"
            showInfo={false}
          />
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          {playing ? (
            <Tooltip title="暂停">
              <Button
                size="small" shape="circle" type="text"
                icon={<PauseCircleOutlined style={{ fontSize: 18, color: '#1677ff' }} />}
                onClick={handlePause}
              />
            </Tooltip>
          ) : (
            <Tooltip title="继续 / 播放">
              <Button
                size="small" shape="circle" type="text"
                icon={<PlayCircleOutlined style={{ fontSize: 18, color: '#1677ff' }} />}
                onClick={handlePlay}
              />
            </Tooltip>
          )}
          <Tooltip title="重播">
            <Button
              size="small" shape="circle" type="text"
              icon={<ReloadOutlined style={{ fontSize: 16, color: '#6b7280' }} />}
              onClick={handleReplay}
            />
          </Tooltip>
        </div>
      </div>

      {/* ── Phase content ── */}
      <div style={{
        minHeight: 280,
        background: '#fafbfd',
        borderRadius: 12,
        border: '1px solid #e5e9f2',
        padding: '18px 20px',
      }}>
        {phase === -1 && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: '#9ca3af' }}>
            <PlayCircleOutlined style={{ fontSize: 36, marginBottom: 10, display: 'block' }} />
            <div>正在初始化回放...</div>
          </div>
        )}
        {phase === 0 && <PhaseData row={row} />}
        {phase === 1 && <PhaseInference row={row} />}
        {phase === 2 && <PhaseDecision row={row} />}
        {phase === 3 && <PhasePQC row={row} />}
      </div>

      {/* ── Phase label ── */}
      <div style={{
        textAlign: 'center', marginTop: 12, fontSize: 12,
        color: '#9ca3af', fontWeight: 500,
      }}>
        {phase >= 0 && phase < PHASES.length
          ? `步骤 ${phase + 1}/${PHASES.length} — ${PHASES[phase].label}`
          : phase === PHASES.length - 1 && !playing
          ? '✓ 回放完成'
          : ''}
      </div>
    </Modal>
  );
}
