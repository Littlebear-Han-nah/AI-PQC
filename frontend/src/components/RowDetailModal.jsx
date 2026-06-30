import { Modal, Descriptions, Tag, Divider } from 'antd';
import { WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';

export default function RowDetailModal({ row, open, onClose }) {
  if (!row) return null;
  const isAnomaly = row.status === 'ANOMALY';

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isAnomaly ? (
            <span style={{
              width: 28, height: 28, borderRadius: 8,
              background: '#fee2e2', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <WarningOutlined style={{ color: '#ef4444', fontSize: 14 }} />
            </span>
          ) : (
            <span style={{
              width: 28, height: 28, borderRadius: 8,
              background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <CheckCircleOutlined style={{ color: '#22c55e', fontSize: 14 }} />
            </span>
          )}
          <span>流量 #{row.sample_id} 检测详情</span>
        </div>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={560}
      styles={{ header: { borderBottom: '1px solid #e5e9f2', paddingBottom: 14 } }}
    >
      <Descriptions column={2} size="small" style={{ marginTop: 16 }}>
        <Descriptions.Item label="状态">
          <Tag color={isAnomaly ? 'error' : 'success'}>{row.label}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="风险评分">
          <span style={{ fontWeight: 700, color: isAnomaly ? '#ef4444' : '#22c55e' }}>
            {row.risk}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="PQC 策略">
          <Tag color={row.pqc_action === 'Kyber768' ? 'error' : 'success'}>{row.pqc_action}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="IF Score">
          <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{row.score}</span>
        </Descriptions.Item>
        <Descriptions.Item label="duration">{row.duration?.toFixed?.(2)}</Descriptions.Item>
        <Descriptions.Item label="packet_count">{row.packet_count}</Descriptions.Item>
        <Descriptions.Item label="byte_size">{row.byte_size}</Descriptions.Item>
        <Descriptions.Item label="flow_rate">{row.flow_rate?.toFixed?.(1)}</Descriptions.Item>
      </Descriptions>

      <Divider style={{ margin: '14px 0' }} />

      <div
        style={{
          padding: '12px 14px',
          background: isAnomaly ? '#fff5f5' : '#f0fdf4',
          borderRadius: 8,
          border: `1px solid ${isAnomaly ? '#fecaca' : '#bbf7d0'}`,
        }}
      >
        <strong style={{ fontSize: 13, color: '#374151' }}>AI 判定说明：</strong>
        <p style={{ margin: '8px 0 0', color: '#4b5563', lineHeight: 1.65, fontSize: 13 }}>
          {row.explanation}
        </p>
      </div>
    </Modal>
  );
}
