import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Space, Input, Drawer, Image, Descriptions, message } from 'antd';
import { ReloadOutlined, FolderOpenOutlined, EyeOutlined } from '@ant-design/icons';
import { fetchExperiments, fetchExpConfig, fetchExpLog, Experiment } from '../api';

const FileExplorer: React.FC = () => {
  const [exps, setExps] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(false);
  const [expRoot, setExpRoot] = useState('');
  const [rootInput, setRootInput] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerExp, setDrawerExp] = useState<Experiment | null>(null);
  const [drawerContent, setDrawerContent] = useState('');

  const load = async (root?: string) => {
    setLoading(true);
    try {
      const d = await fetchExperiments(root || undefined);
      setExps(d.experiments);
      setExpRoot(d.root);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const showConfig = async (exp: Experiment) => {
    setDrawerExp(exp);
    try {
      const d = await fetchExpConfig(exp.name);
      setDrawerContent(d.content || '(无配置文件)');
    } catch { setDrawerContent('(读取失败)'); }
    setDrawerOpen(true);
  };

  const showLog = async (exp: Experiment) => {
    setDrawerExp(exp);
    try {
      const d = await fetchExpLog(exp.name, 200);
      setDrawerContent(d.log || '(无日志)');
    } catch { setDrawerContent('(读取失败)'); }
    setDrawerOpen(true);
  };

  const columns = [
    { title: '实验名', dataIndex: 'name', key: 'name', width: 250 },
    {
      title: '状态', key: 'status', width: 80,
      render: (_: any, r: Experiment) => r.is_running ? <Tag color="processing">运行中</Tag> : <Tag>已停止</Tag>,
    },
    { title: '迭代', dataIndex: 'max_iter', key: 'iter', width: 100, render: (v: number) => v ? v.toLocaleString() : '-' },
    { title: '检查点', key: 'ckpts', width: 80, render: (_: any, r: Experiment) => r.checkpoints?.length || 0 },
    { title: '图像', key: 'imgs', width: 80, render: (_: any, r: Experiment) => r.images?.length || 0 },
    { title: '日志行', dataIndex: 'log_lines', key: 'log', width: 80 },
    { title: '修改时间', dataIndex: 'mtime', key: 'mtime', width: 150 },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: any, r: Experiment) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => showConfig(r)}>配置</Button>
          <Button size="small" onClick={() => showLog(r)}>日志</Button>
        </Space>
      ),
    },
  ];

  const expandedRowRender = (exp: Experiment) => (
    <div>
      <h4>检查点</h4>
      {exp.checkpoints && exp.checkpoints.length > 0 ? (
        <Table dataSource={exp.checkpoints} columns={[
          { title: '文件名', dataIndex: 'name', key: 'name' },
          { title: '大小', dataIndex: 'size_mb', key: 'size', render: (v: number) => `${v} MB` },
          { title: '修改时间', dataIndex: 'mtime', key: 'mtime' },
        ]} rowKey="name" pagination={false} size="small" />
      ) : <span style={{ color: '#888' }}>无检查点</span>}
      <h4 style={{ marginTop: 12 }}>验证结果</h4>
      {exp.images && exp.images.length > 0 ? (
        <Image.PreviewGroup>
          <Space wrap>
            {exp.images.slice(0, 10).map(img => (
              <Image key={img.path} src={`/api/experiments/${exp.name}/image?path=${encodeURIComponent(img.path)}`}
                width={120} preview={{ mask: '查看' }} />
            ))}
          </Space>
        </Image.PreviewGroup>
      ) : <span style={{ color: '#888' }}>无结果图</span>}
    </div>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>📁 实验文件浏览器</h2>
        <Space>
          <span style={{ color: '#888' }}>{expRoot}</span>
          <Button icon={<ReloadOutlined />} onClick={() => load()}>刷新</Button>
        </Space>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Space>
          <Input placeholder="切换实验根目录" value={rootInput} onChange={e => setRootInput(e.target.value)} style={{ width: 400 }} />
          <Button icon={<FolderOpenOutlined />} onClick={() => load(rootInput)}>切换</Button>
        </Space>
      </div>

      <Table dataSource={exps} columns={columns} rowKey="name" loading={loading}
        expandable={{ expandedRowRender, rowExpandable: () => true }}
        size="small" pagination={{ pageSize: 20 }} />

      <Drawer title={drawerExp ? drawerExp.name : ''} open={drawerOpen}
        onClose={() => setDrawerOpen(false)} width="50%">
        <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: '80vh', overflow: 'auto', fontSize: 12 }}>
          {drawerContent}
        </pre>
      </Drawer>
    </div>
  );
};

export default FileExplorer;
