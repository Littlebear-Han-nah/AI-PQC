import React from 'react';
import ReactDOM from 'react-dom/client';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import './styles/global.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          colorSuccess: '#22c55e',
          colorError: '#ef4444',
          colorWarning: '#f59e0b',
          borderRadius: 8,
          colorBgContainer: '#ffffff',
          colorBgLayout: '#f7f9fc',
          colorBorder: '#e5e9f2',
          fontFamily:
            "'Inter', 'Helvetica Neue', Helvetica, -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif",
        },
        components: {
          Table: {
            headerBg: '#f8fafd',
            headerColor: '#374151',
            rowHoverBg: '#f0f6ff',
          },
          Card: {
            paddingLG: 16,
          },
          Modal: {
            titleFontSize: 16,
          },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
