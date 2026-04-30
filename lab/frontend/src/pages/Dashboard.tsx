import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Tag } from 'antd';
import { OrderedListOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { fetchTasks, fetchExperiments, TaskStats, Experiment } from '../api';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<TaskStats>({ total: 0 });
  const [recentExps, setRecentExps] = useState<Experiment[]>([]);

  useEffect(() => {
    fetchTasks().then(d => setStats(d.stats));
    fetchExperiments().then(d => setRecentExps(d.experiments.slice(-5).reverse()));
  }, []);

  const getStatusDisplay = (r: Experiment) => {
    if (r.is_running) return <Tag color="processing">运行中</Tag>;
    if (r.status === "completed") return <Tag color="success">已完成</Tag>;
    if (r.status === "stopped") return <Tag color="error">已停止 / 中断</Tag>;
    return <Tag color="default">等待训练</Tag>;
  };

  const expColumns = [
    { title: '实验名', dataIndex: 'name', key: 'name' },
    {
      title: '状态', key: 'status',
      render: (_: any, r: Experiment) => getStatusDisplay(r),
    },
    { title: '检查点', dataIndex: 'checkpoints', key: 'ckpts', render: (v: any[]) => v?.length || 0 },
    { title: '日志行', dataIndex: 'log_lines', key: 'log', render: (v: number) => v ? v.toLocaleString() : '-' },
    { title: '修改时间', dataIndex: 'mtime', key: 'mtime' },
  ];

  return (
    <div>
      <h2>📊 概览</h2>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card><Statistic title="总任务" value={stats.total} prefix={<OrderedListOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="排队中" value={stats.queued || 0} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#faad14' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="运行中" value={stats.running || 0} prefix={<ClockCircleOutlined />} valueStyle={{ color: '#1677ff' }} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="已完成" value={stats.completed || 0} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
      </Row>
      <h3>最近实验</h3>
      <Table dataSource={recentExps} columns={expColumns} rowKey="name" pagination={false} size="small" />
    </div>
  );
};

export default Dashboard;
