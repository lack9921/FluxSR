import React, { useState, useEffect } from 'react';
import { ConfigProvider, Layout, Menu, theme } from 'antd';
import {
  DashboardOutlined,
  OrderedListOutlined,
  LineChartOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';

import Dashboard from './pages/Dashboard';
import TaskQueue from './pages/TaskQueue';
import TrainingMonitor from './pages/TrainingMonitor';
import ConfigEditor from './pages/ConfigEditor';
import FileExplorer from './pages/FileExplorer';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '概览' },
  { key: '/tasks', icon: <OrderedListOutlined />, label: '训练队列' },
  { key: '/monitor', icon: <LineChartOutlined />, label: '训练监控' },
  { key: '/config', icon: <FileTextOutlined />, label: '配置编辑器' },
  { key: '/files', icon: <FolderOpenOutlined />, label: '实验文件' },
];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="dark">
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 'bold', fontSize: collapsed ? 14 : 18 }}>
          {collapsed ? '🧪' : '🧪 FluxSR Lab'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8, overflow: 'auto' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tasks" element={<TaskQueue />} />
            <Route path="/monitor" element={<TrainingMonitor />} />
            <Route path="/config" element={<ConfigEditor />} />
            <Route path="/files" element={<FileExplorer />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
