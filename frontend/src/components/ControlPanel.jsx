import { Card, Select, Slider, Switch, Divider } from 'antd';
import { SettingOutlined, LockOutlined, TableOutlined, ThunderboltOutlined } from '@ant-design/icons';

function Label({ children }) {
  return (
    <div style={{ fontSize: 12, fontWeight: 600, color: '#374151', marginBottom: 8 }}>
      {children}
    </div>
  );
}

export default function ControlPanel({
  pqcMode,
  setPqcMode,
  sampleCount,
  setSampleCount,
  liveSim,
  setLiveSim,
  delay,
  setDelay,
}) {
  return (
    <Card
      className="panel-card"
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <SettingOutlined style={{ color: '#1677ff' }} /> 配置面板
        </span>
      }
      size="small"
    >
      {/* PQC Mode */}
      <div style={{ marginBottom: 20 }}>
        <Label><LockOutlined style={{ marginRight: 5, color: '#1677ff' }} />PQC 加密模式</Label>
        <Select
          style={{ width: '100%' }}
          value={pqcMode}
          onChange={setPqcMode}
          options={[
            {
              value: 'Kyber512',
              label: (
                <span>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                    background: '#22c55e', marginRight: 7,
                  }} />
                  Kyber512 · Level 1
                </span>
              ),
            },
            {
              value: 'Kyber768',
              label: (
                <span>
                  <span style={{
                    display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                    background: '#ef4444', marginRight: 7,
                  }} />
                  Kyber768 · Level 3
                </span>
              ),
            },
          ]}
        />
        <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>
          {pqcMode === 'Kyber512' ? '标准安全 · 128-bit equivalent' : '增强安全 · 192-bit equivalent'}
        </div>
      </div>

      <Divider style={{ margin: '4px 0 16px' }} />

      {/* Sample count */}
      <div style={{ marginBottom: 20 }}>
        <Label>
          <TableOutlined style={{ marginRight: 5, color: '#1677ff' }} />
          合成数据数量：<span style={{ color: '#1677ff', fontWeight: 700 }}>{sampleCount}</span>
        </Label>
        <Slider
          min={50} max={500} step={50}
          value={sampleCount}
          onChange={setSampleCount}
          marks={{ 50: '50', 200: '200', 500: '500' }}
          tooltip={{ formatter: (v) => `${v} 条` }}
        />
      </div>

      <Divider style={{ margin: '4px 0 16px' }} />

      {/* Live simulation */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <Label><ThunderboltOutlined style={{ marginRight: 5, color: '#1677ff' }} />实时流模拟</Label>
          <Switch
            checked={liveSim}
            onChange={setLiveSim}
            size="small"
          />
        </div>
        <div style={{ fontSize: 11, color: '#9ca3af' }}>
          {liveSim ? '逐条推流，实时展示检测过程' : '批量检测，一次性返回所有结果'}
        </div>
      </div>

      {/* Delay */}
      <div>
        <Label>刷新延迟：{delay.toFixed(2)} 秒</Label>
        <Slider
          min={0} max={0.3} step={0.05}
          value={delay}
          onChange={setDelay}
          disabled={!liveSim}
          marks={{ 0: '0', 0.15: '0.15', 0.3: '0.3s' }}
          tooltip={{ formatter: (v) => `${v}s` }}
        />
      </div>
    </Card>
  );
}
