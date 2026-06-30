import { Badge, Tag } from 'antd';
import { LockOutlined, SafetyCertificateOutlined, ApiOutlined } from '@ant-design/icons';

export default function PQCStatus({ mode, systemStatus, detecting }) {
  const isAlert = systemStatus === 'alert';
  const modeClass = mode === 'Kyber768' ? 'kyber768' : 'kyber512';

  return (
    <div className={`pqc-status-banner ${isAlert ? 'alert' : 'secure'}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        {/* icon */}
        <div style={{
          width: 48, height: 48,
          borderRadius: 12,
          background: isAlert ? '#fee2e2' : '#dcfce7',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22,
          flexShrink: 0,
          transition: 'background 0.5s',
        }}>
          <LockOutlined style={{ color: isAlert ? '#ef4444' : '#22c55e' }} />
        </div>
        <div>
          <div style={{ color: '#6b7280', fontSize: 12, fontWeight: 500, marginBottom: 4 }}>
            当前 PQC 加密模式
          </div>
          <div className={`pqc-mode-text ${modeClass}`}>{mode || 'Kyber512'}</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
        {/* Algorithm chip */}
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: '#6b7280', fontSize: 11, fontWeight: 500, marginBottom: 6 }}>
            <ApiOutlined /> 安全级别
          </div>
          <div style={{
            fontSize: 13, fontWeight: 700, padding: '4px 12px',
            borderRadius: 99,
            background: isAlert ? '#fee2e2' : '#eff6ff',
            color: isAlert ? '#ef4444' : '#1677ff',
            border: `1px solid ${isAlert ? '#fecaca' : '#bfdbfe'}`,
          }}>
            {mode === 'Kyber768' ? 'Level 3 (Enhanced)' : 'Level 1 (Standard)'}
          </div>
        </div>

        {/* System status */}
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: '#6b7280', fontSize: 12, fontWeight: 500, marginBottom: 8 }}>
            <SafetyCertificateOutlined /> 系统状态
          </div>
          {detecting ? (
            <Tag color="processing" style={{ fontSize: 13, padding: '3px 10px' }}>检测中...</Tag>
          ) : (
            <Badge
              status={isAlert ? 'error' : 'success'}
              text={
                <span style={{ fontSize: 15, fontWeight: 700, color: isAlert ? '#ef4444' : '#22c55e' }}>
                  {isAlert ? '告警 · 发现异常流量' : '安全 · 流量正常'}
                </span>
              }
            />
          )}
        </div>
      </div>
    </div>
  );
}
