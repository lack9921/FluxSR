import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Modal, Form, Input, InputNumber, message, Space, Drawer, Descriptions } from 'antd';
import { PlusOutlined, StopOutlined, DeleteOutlined, ReloadOutlined, EyeOutlined, FileTextOutlined } from '@ant-design/icons';
import { fetchTasks, createTask, cancelTask, deleteTask, fetchTaskLog, Task, TaskStats } from '../api';

const statusMap: Record<string, { color: string; text: string }> = {
  queued: { color: 'processing', text: '排队中' },
  running: { color: 'success', text: '运行中' },
  completed: { color: 'default', text: '已完成' },
  failed: { color: 'error', text: '失败' },
  cancelled: { color: 'warning', text: '已取消' },
};

const TaskQueue: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<TaskStats>({ total: 0 });
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [logContent, setLogContent] = useState('');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [form] = Form.useForm();

  const load = () => {
    setLoading(true);
    fetchTasks().then(d => { setTasks(d.tasks); setStats(d.stats); }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); const timer = setInterval(load, 10000); return () => clearInterval(timer); }, []);

  const handleSubmit = async () => {
    const vals = await form.validateFields();
    await createTask(vals);
    message.success('任务已提交');
    setModalOpen(false);
    form.resetFields();
    load();
  };

  const handleCancel = async (id: string) => {
    await cancelTask(id);
    message.success('已取消');
    load();
  };

  const handleDelete = async (id: string) => {
    await deleteTask(id);
    message.success('已删除');
    load();
  };

  const showLog = async (task: Task) => {
    setSelectedTask(task);
    try {
      const d = await fetchTaskLog(task.id);
      setLogContent(d.log);
    } catch { setLogContent('(读取失败)'); }
    setDrawerOpen(true);
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: string) => {
        const m = statusMap[s] || { color: 'default', text: s };
        return <Tag color={m.color}>{m.text}</Tag>;
      },
    },
    { title: 'GPU', dataIndex: 'gpu_count', key: 'gpu', width: 60 },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 70 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180, render: (v: string) => v.slice(5, 19) },
    {
      title: '操作', key: 'action', width: 200,
      render: (_: any, record: Task) => (
        <Space>
          {record.status === 'queued' && <Button size="small" icon={<StopOutlined />} onClick={() => handleCancel(record.id)} danger>取消</Button>}
          {(record.status === 'queued' || record.status === 'failed' || record.status === 'cancelled') &&
            <Button size="small" icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)} />}
          <Button size="small" icon={<FileTextOutlined />} onClick={() => showLog(record)}>日志</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>🎯 训练队列</h2>
        <Space>
          <span>排队 {stats.queued || 0} / 运行 {stats.running || 0} / 完成 {stats.completed || 0}</span>
          <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>提交任务</Button>
        </Space>
      </div>

      <Table dataSource={tasks} columns={columns} rowKey="id" loading={loading} size="small" pagination={{ pageSize: 20 }} />

      <Modal title="提交新任务" open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
            <Input placeholder="my_experiment" />
          </Form.Item>
          <Form.Item name="config_path" label="配置文件路径" rules={[{ required: true }]}>
            <Input placeholder="experiments/xxx/train.yml" />
          </Form.Item>
          <Form.Item name="override_args" label="额外参数">
            <Input placeholder="batch_size=8 lr=1e-4" />
          </Form.Item>
          <Form.Item name="gpu_count" label="GPU 数量" initialValue={1}>
            <InputNumber min={1} max={8} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue={0}>
            <InputNumber min={0} max={10} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title={selectedTask ? `日志: ${selectedTask.name} (${selectedTask.id.slice(0, 8)})` : '日志'}
        open={drawerOpen} onClose={() => setDrawerOpen(false)} width="60%">
        {selectedTask && (
          <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="状态">{selectedTask.status}</Descriptions.Item>
            <Descriptions.Item label="配置文件">{selectedTask.config_path}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{selectedTask.created_at}</Descriptions.Item>
            <Descriptions.Item label="开始时间">{selectedTask.started_at || '-'}</Descriptions.Item>
            <Descriptions.Item label="错误">{selectedTask.error_msg || '-'}</Descriptions.Item>
          </Descriptions>
        )}
        <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: '60vh', overflow: 'auto', fontSize: 12 }}>
          {logContent || '(无日志)'}
        </pre>
      </Drawer>
    </div>
  );
};

export default TaskQueue;
