import { Row, Col } from 'antd';
import AnimatedNumber from './AnimatedNumber';

function StatCard({ label, value, colorClass }) {
  return (
    <div className={`stat-card ${colorClass}`}>
      <div className="label">{label}</div>
      <div className="value">
        <AnimatedNumber value={value} />
      </div>
    </div>
  );
}

export default function StatsCards({ summary }) {
  const s = summary || { total: 0, normal: 0, anomalies: 0, renegotiations: 0 };
  return (
    <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
      <Col xs={12} sm={6}>
        <StatCard label="总流量数" value={s.total} colorClass="blue" />
      </Col>
      <Col xs={12} sm={6}>
        <StatCard label="正常流量" value={s.normal} colorClass="green" />
      </Col>
      <Col xs={12} sm={6}>
        <StatCard label="异常流量" value={s.anomalies} colorClass="red" />
      </Col>
      <Col xs={12} sm={6}>
        <StatCard label="PQC 重协商次数" value={s.renegotiations} colorClass="amber" />
      </Col>
    </Row>
  );
}
