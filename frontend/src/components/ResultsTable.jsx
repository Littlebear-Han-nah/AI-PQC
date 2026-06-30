import { Table, Tag, Button, Tooltip } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';

export default function ResultsTable({ rows, onRowClick, onReplayClick, loading }) {
  const columns = [
    {
      title: 'ID',
      dataIndex: 'sample_id',
      width: 55,
      fixed: 'left',
      render: (v) => <span style={{ fontWeight: 600, color: '#374151' }}>#{v}</span>,
    },
    {
      title: 'duration',
      dataIndex: 'duration',
      width: 88,
      render: (v) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v?.toFixed?.(2)}</span>,
    },
    { title: 'packets', dataIndex: 'packet_count', width: 72 },
    { title: 'bytes', dataIndex: 'byte_size', width: 72 },
    {
      title: 'flow_rate',
      dataIndex: 'flow_rate',
      width: 82,
      render: (v) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v?.toFixed?.(1)}</span>,
    },
    {
      title: '标签',
      dataIndex: 'label',
      width: 75,
      render: (v) => (
        <Tag
          color={v === '异常' ? 'error' : 'success'}
          style={{ fontSize: 11, fontWeight: 600 }}
        >
          {v}
        </Tag>
      ),
    },
    {
      title: '风险',
      dataIndex: 'risk',
      width: 72,
      sorter: (a, b) => a.risk - b.risk,
      render: (v) => {
        const pct = v * 100;
        const color = v > 0.6 ? '#ef4444' : v > 0.4 ? '#f59e0b' : '#22c55e';
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 32, height: 5, borderRadius: 99, background: '#f1f5f9', overflow: 'hidden', flexShrink: 0,
            }}>
              <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 99 }} />
            </div>
            <span style={{ color, fontWeight: 700, fontSize: 12 }}>{v}</span>
          </div>
        );
      },
    },
    {
      title: 'PQC',
      dataIndex: 'pqc_action',
      width: 95,
      render: (v) => (
        <Tag color={v === 'Kyber768' ? 'error' : 'success'} style={{ fontSize: 11 }}>{v}</Tag>
      ),
    },
    {
      title: '回放',
      key: 'replay',
      width: 60,
      fixed: 'right',
      render: (_, record) =>
        record.status === 'ANOMALY' ? (
          <Tooltip title="回放检测过程">
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined style={{ color: '#ef4444', fontSize: 16 }} />}
              style={{ padding: 0 }}
              onClick={(e) => {
                e.stopPropagation();
                onReplayClick?.(record);
              }}
            />
          </Tooltip>
        ) : (
          <Tooltip title="回放检测过程">
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined style={{ color: '#22c55e', fontSize: 16 }} />}
              style={{ padding: 0 }}
              onClick={(e) => {
                e.stopPropagation();
                onReplayClick?.(record);
              }}
            />
          </Tooltip>
        ),
    },
  ];

  return (
    <Table
      size="small"
      loading={loading}
      dataSource={(rows || []).map((r) => ({ ...r, key: r.sample_id }))}
      columns={columns}
      pagination={{ pageSize: 8, showSizeChanger: false, showTotal: (t) => `共 ${t} 条` }}
      scroll={{ x: 680 }}
      onRow={(record) => ({
        onClick: () => onRowClick?.(record),
        className: record.status === 'ANOMALY' ? 'anomaly-row' : 'normal-row',
        style: { cursor: 'pointer' },
      })}
    />
  );
}
