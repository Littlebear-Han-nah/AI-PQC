import { Button, Card, Space, Table, Upload, message } from 'antd';
import { CloudUploadOutlined, DatabaseOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { generateDataset, uploadDataset } from '../api/client';

export default function DataInput({ sampleCount, onDatasetReady, datasetInfo, loading, setLoading }) {
  const handleGenerate = async () => {
    setLoading(true);
    try {
      const data = await generateDataset(sampleCount);
      message.success(data.message);
      onDatasetReady(data);
    } catch (err) {
      message.error(err.response?.data?.detail || '生成数据失败');
    } finally {
      setLoading(false);
    }
  };

  const uploadProps = {
    accept: '.csv',
    showUploadList: false,
    beforeUpload: async (file) => {
      setLoading(true);
      try {
        const data = await uploadDataset(file);
        message.success(data.message);
        onDatasetReady(data);
      } catch (err) {
        message.error(err.response?.data?.detail || '上传失败');
      } finally {
        setLoading(false);
      }
      return false;
    },
  };

  const previewColumns = [
    { title: 'duration', dataIndex: 'duration', width: 90, render: (v) => v?.toFixed?.(3) ?? v },
    { title: 'packet_count', dataIndex: 'packet_count', width: 100 },
    { title: 'byte_size', dataIndex: 'byte_size', width: 90 },
    { title: 'flow_rate', dataIndex: 'flow_rate', width: 90, render: (v) => v?.toFixed?.(1) ?? v },
  ];

  return (
    <Card
      className="panel-card"
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <DatabaseOutlined style={{ color: '#1677ff' }} /> 数据输入
        </span>
      }
      size="small"
    >
      <Space wrap>
        <Upload {...uploadProps}>
          <Button icon={<CloudUploadOutlined />} loading={loading}>
            上传 CSV 文件
          </Button>
        </Upload>
        <Button
          type="primary"
          ghost
          icon={<DatabaseOutlined />}
          loading={loading}
          onClick={handleGenerate}
        >
          生成合成数据（{sampleCount} 条）
        </Button>
      </Space>

      {datasetInfo && (
        <div style={{ marginTop: 14 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
            padding: '8px 12px',
            background: '#f0fdf4', borderRadius: 8, border: '1px solid #bbf7d0',
          }}>
            <CheckCircleOutlined style={{ color: '#22c55e', fontSize: 16 }} />
            <span style={{ fontSize: 13, color: '#374151' }}>
              已加载{' '}
              <strong style={{ color: '#1677ff' }}>{datasetInfo.total}</strong> 条网络流量
              {datasetInfo.anomalies !== undefined && (
                <> · 含 <strong style={{ color: '#ef4444' }}>{datasetInfo.anomalies}</strong> 条异常</>
              )}
            </span>
          </div>
          {datasetInfo.preview?.length > 0 && (
            <Table
              size="small"
              dataSource={datasetInfo.preview.map((r, i) => ({ ...r, key: i }))}
              columns={previewColumns}
              pagination={false}
              scroll={{ x: true }}
            />
          )}
        </div>
      )}
    </Card>
  );
}
