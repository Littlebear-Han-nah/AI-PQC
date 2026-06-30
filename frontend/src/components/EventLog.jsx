import { useEffect, useRef } from 'react';
import { Card } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';

const levelMap = {
  info: '[正常]',
  warning: '[异常]',
  system: '[系统]',
};

export default function EventLog({ logs }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [logs]);

  return (
    <Card
      className="panel-card"
      title={
        <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
          <FileTextOutlined style={{ color: '#1677ff' }} /> 事件日志
        </span>
      }
      size="small"
    >
      <div className="event-log-panel" ref={ref}>
        {(logs || []).length === 0 && (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: '20px 0', fontSize: 12 }}>
            等待检测事件...
          </div>
        )}
        {(logs || []).map((log, i) => (
          <div key={i} className={`log-line ${log.level}`}>
            {levelMap[log.level] || '[信息]'} {log.message}
          </div>
        ))}
      </div>
    </Card>
  );
}
