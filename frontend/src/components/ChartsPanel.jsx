import ReactECharts from 'echarts-for-react';

export default function ChartsPanel({ scores, labels, summary }) {
  const scoreOption = {
    backgroundColor: 'transparent',
    title: {
      text: '异常评分分布（Isolation Forest Score）',
      textStyle: { color: '#374151', fontSize: 13, fontWeight: 600 },
      left: 0,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#ffffff',
      borderColor: '#e5e9f2',
      textStyle: { color: '#111827' },
      formatter: (params) => {
        const p = params[0];
        return `样本 #${p.dataIndex}<br/>Score: <b>${p.value?.toFixed(4)}</b>`;
      },
    },
    grid: { left: 48, right: 16, top: 48, bottom: 30 },
    xAxis: {
      type: 'category',
      data: scores?.map((_, i) => i) || [],
      axisLabel: { color: '#9ca3af', fontSize: 11 },
      axisLine: { lineStyle: { color: '#e5e9f2' } },
      axisTick: { lineStyle: { color: '#e5e9f2' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9ca3af', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    },
    series: [
      {
        type: 'bar',
        data: (scores || []).map((s, i) => ({
          value: s,
          itemStyle: {
            color: labels?.[i] === -1 ? '#ef4444' : '#22c55e',
            borderRadius: [3, 3, 0, 0],
          },
        })),
        barMaxWidth: 14,
      },
    ],
  };

  const pieOption = {
    backgroundColor: 'transparent',
    title: {
      text: '流量分类统计',
      textStyle: { color: '#374151', fontSize: 13, fontWeight: 600 },
      left: 0,
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: '#ffffff',
      borderColor: '#e5e9f2',
      textStyle: { color: '#111827' },
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#6b7280', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['38%', '62%'],
        center: ['50%', '48%'],
        label: {
          color: '#374151',
          fontSize: 12,
          formatter: '{b}: {c} ({d}%)',
        },
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        data: [
          { value: summary?.normal || 0, name: '正常', itemStyle: { color: '#22c55e' } },
          { value: summary?.anomalies || 0, name: '异常', itemStyle: { color: '#ef4444' } },
        ],
      },
    ],
  };

  if (!scores?.length) {
    return (
      <div style={{
        color: '#9ca3af',
        textAlign: 'center',
        padding: '48px 20px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
      }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" strokeWidth="1.5">
          <path d="M3 3v18h18M7 16l4-4 4 4 4-8" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span style={{ fontSize: 13 }}>运行检测后显示可视化图表</span>
      </div>
    );
  }

  return (
    <div>
      <ReactECharts option={scoreOption} style={{ height: 260 }} />
      <ReactECharts option={pieOption} style={{ height: 260, marginTop: 8 }} />
    </div>
  );
}
