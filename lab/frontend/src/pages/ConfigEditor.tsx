import React, { useState, useEffect } from 'react';
import { Form, Input, InputNumber, Select, Button, Switch, Row, Col, Card, message, Space } from 'antd';
import { generateConfig } from '../api';

const modelPresets: Record<string, any> = {
  SwinIR: { upscale: 4, embed_dim: 180, depths: [6, 6, 6, 6], num_heads: [6, 6, 6, 6], window_size: 8 },
  EDSR: { upscale: 4, num_feat: 64, num_block: 16 },
  RCAN: { upscale: 4, num_feat: 64, num_group: 10, num_block: 20 },
};

const ConfigEditor: React.FC = () => {
  const [form] = Form.useForm();
  const [yaml, setYaml] = useState('');
  const [selectedModel, setSelectedModel] = useState('SwinIR');

  const handleGenerate = async () => {
    const vals = await form.validateFields();
    const modelParams = modelPresets[vals.model_type] || {};
    const data = {
      experiment_name: vals.exp_name,
      model_type: vals.model_type,
      model_params: { ...modelParams, ...vals.extra_params },
      batch_size: vals.batch_size,
      lr: vals.lr,
      total_iter: vals.total_iter,
      fp16: vals.fp16,
      train_root: vals.train_root,
      val_root: vals.val_root,
      gt_size: vals.gt_size,
      gpu_ids: vals.gpu_ids,
    };
    const res = await generateConfig(data);
    setYaml(res.yaml);
    message.success('YAML 生成成功');
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(yaml);
    message.success('已复制');
  };

  return (
    <div>
      <h2>📝 配置编辑器</h2>
      <Row gutter={24}>
        <Col span={14}>
          <Card title="参数配置" size="small">
            <Form form={form} layout="vertical" initialValues={{
              exp_name: 'exp_001', model_type: 'SwinIR',
              batch_size: 16, lr: 0.0002, total_iter: 500000, fp16: true,
              train_root: './datasets/DIV2K', val_root: './datasets/Set5',
              gt_size: 128, gpu_ids: '0',
            }}>
              <Form.Item name="exp_name" label="实验名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="model_type" label="模型类型">
                <Select onChange={setSelectedModel} options={[
                  { label: 'SwinIR', value: 'SwinIR' },
                  { label: 'EDSR', value: 'EDSR' },
                  { label: 'RCAN', value: 'RCAN' },
                ]} />
              </Form.Item>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="batch_size" label="Batch Size"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="lr" label="学习率"><InputNumber min={1e-7} max={1} step={1e-5} style={{ width: '100%' }} /></Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="total_iter" label="总迭代"><InputNumber min={1000} style={{ width: '100%' }} /></Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="gt_size" label="Patch Size"><InputNumber min={32} max={256} style={{ width: '100%' }} /></Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="gpu_ids" label="GPU"><Input placeholder="0,1,2" /></Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="fp16" label="FP16" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="train_root" label="训练集路径"><Input /></Form.Item>
              <Form.Item name="val_root" label="验证集路径"><Input /></Form.Item>
              <Button type="primary" onClick={handleGenerate}>📄 生成 YAML</Button>
            </Form>
          </Card>
        </Col>
        <Col span={10}>
          <Card title="YAML 预览" size="small" extra={<Button size="small" onClick={handleCopy}>复制</Button>}>
            <pre style={{ background: '#f5f5f5', padding: 12, borderRadius: 4, maxHeight: '60vh', overflow: 'auto', fontSize: 12 }}>
              {yaml || '(点击生成预览)'}
            </pre>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ConfigEditor;
