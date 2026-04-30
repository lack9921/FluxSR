import React, { useEffect, useState } from 'react';
import {
  Form, Input, InputNumber, Select, Button, Switch, Row, Col, Card,
  message, Steps, Collapse, Divider, Modal, Space, Tag, Typography,
} from 'antd';
import {
  SettingOutlined, DatabaseOutlined, ApartmentOutlined,
  ThunderboltOutlined, ControlOutlined, FileTextOutlined,
} from '@ant-design/icons';
import { fetchLabInfo } from '../api';

const { Text, Title } = Typography;

// ── 后端数据定义 ──

interface ArchParamDef {
  name: string;
  label: string;
  type: 'int' | 'float' | 'list_int' | 'select';
  default: any;
  min?: number;
  max?: number;
  hint?: string;
  options?: string[];
}

interface ArchDef {
  params: ArchParamDef[];
}

interface ModelTypeEntry {
  label: string;
  archs: string[];
}

interface ConfigInfo {
  model_types: Record<string, ModelTypeEntry>;
  arch_params: Record<string, ArchDef>;
  loss_templates: Record<string, any>;
  scheduler_templates: Record<string, any>;
  datasets: string[];
  options_dirs: string[];
  settings: { train_root: string; val_root: string };
}

// ── 组件 ──

const ConfigEditor: React.FC = () => {
  const [step, setStep] = useState(0);
  const [info, setInfo] = useState<ConfigInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [yaml, setYaml] = useState('');
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);

  // 表单值
  const [form] = Form.useForm();
  const [selectedModelType, setSelectedModelType] = useState('SRModel');
  const [selectedArch, setSelectedArch] = useState('MSRResNet');
  const [archParams, setArchParams] = useState<ArchParamDef[]>([]);
  const [saving, setSaving] = useState(false);

  // 加载元信息
  useEffect(() => {
    fetch(`/api/configs/info`)
      .then(r => r.json())
      .then(d => {
        setInfo(d);
        const arch = d.arch_params['MSRResNet'];
        if (arch) setArchParams(arch.params);
      })
      .finally(() => setLoading(false));
  }, []);

  // 切换模型类型时更新可用网络架构
  const handleModelTypeChange = (mt: string) => {
    setSelectedModelType(mt);
    if (!info) return;
    const entry = info.model_types[mt];
    if (entry && entry.archs.length > 0) {
      const arch = entry.archs[0];
      setSelectedArch(arch);
      if (info.arch_params[arch]) {
        setArchParams(info.arch_params[arch].params);
      }
    }
  };

  // 切换网络架构时更新参数表单
  const handleArchChange = (arch: string) => {
    setSelectedArch(arch);
    if (info && info.arch_params[arch]) {
      setArchParams(info.arch_params[arch].params);
    }
  };

  // 生成配置
  const handleGenerate = async () => {
    try {
      const vals = await form.validateFields();
      const res = await fetch('/api/configs/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(vals),
      });
      const d = await res.json();
      setYaml(d.yaml);
      message.success('YAML 生成成功');
      setStep(5); // 跳到预览
    } catch {
      message.error('请检查表单填写');
    }
  };

  // 保存配置到文件
  const handleSave = async () => {
    if (!yaml) { message.error('请先生成 YAML'); return; }
    setSaving(true);
    try {
      const dir = form.getFieldValue('save_subdir') || 'Custom';
      const fname = form.getFieldValue('save_filename') || form.getFieldValue('name');
      const res = await fetch('/api/configs/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yaml_content: yaml, subdir: dir, filename: fname }),
      });
      const d = await res.json();
      if (d.ok) {
        message.success(`已保存到 ${d.path}`);
        setSaveModalOpen(false);
      } else {
        message.error('保存失败');
      }
    } catch {
      message.error('保存请求失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>加载配置模板...</div>;
  if (!info) return <div style={{ padding: 40, textAlign: 'center' }}>加载失败</div>;

  const steps = [
    { title: '选择模型', icon: <ApartmentOutlined /> },
    { title: '基础参数', icon: <SettingOutlined /> },
    { title: '数据集', icon: <DatabaseOutlined /> },
    { title: '网络参数', icon: <ControlOutlined /> },
    { title: '训练参数', icon: <ThunderboltOutlined /> },
    { title: '预览', icon: <FileTextOutlined /> },
  ];

  // 网络参数动态渲染
  const renderArchParams = () => {
    return archParams.map(p => {
      const name = `network_params.${p.name}`;
      switch (p.type) {
        case 'int':
          return (
            <Col span={8} key={p.name}>
              <Form.Item name={name} label={p.label} initialValue={p.default}
                rules={[{ required: true, message: `请输入${p.label}` }]}>
                <InputNumber min={p.min} max={p.max} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          );
        case 'float':
          return (
            <Col span={8} key={p.name}>
              <Form.Item name={name} label={p.label} initialValue={p.default}
                rules={[{ required: true, message: `请输入${p.label}` }]}>
                <InputNumber min={p.min} max={p.max} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          );
        case 'select':
          return (
            <Col span={8} key={p.name}>
              <Form.Item name={name} label={p.label} initialValue={p.default}>
                <Select options={(p.options || []).map(o => ({ label: o, value: o }))} />
              </Form.Item>
            </Col>
          );
        case 'list_int':
          return (
            <Col span={12} key={p.name}>
              <Form.Item name={name} label={p.label} initialValue={p.default.join(',')}
                help={p.hint}>
                <Input />
              </Form.Item>
            </Col>
          );
        default:
          return null;
      }
    });
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>📝 配置编辑器</h2>
        <Space>
          <Button icon={<SettingOutlined />} onClick={() => setSettingsModalOpen(true)}>
            数据集设置
          </Button>
        </Space>
      </div>

      <Steps current={step} items={steps} style={{ marginBottom: 24 }} />

      {/* Step 0: 选择模型 */}
      {step === 0 && (
        <Card title="选择模型类型">
          <Form.Item label="模型类型" style={{ marginBottom: 8 }}>
            <Select value={selectedModelType} onChange={handleModelTypeChange}
              style={{ width: 400 }}
              options={Object.entries(info.model_types).map(([k, v]) => ({
                label: v.label, value: k,
              }))} />
          </Form.Item>
          <Form.Item label="网络架构" style={{ marginBottom: 8 }}>
            <Select value={selectedArch} onChange={handleArchChange}
              style={{ width: 400 }}
              options={(info.model_types[selectedModelType]?.archs || []).map(a => ({
                label: a, value: a,
              }))} />
          </Form.Item>
          <div style={{ marginTop: 16 }}>
            {archParams.length > 0 && (
              <Text type="secondary">
                已选择 <Tag>{selectedArch}</Tag>，含 {archParams.length} 个可配参数，
                将在下一步中配置。
              </Text>
            )}
          </div>
        </Card>
      )}

      {/* Step 1: 基础参数 */}
      {step === 1 && (
        <Card title="基础参数">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="实验名称" initialValue="exp_001"
                rules={[{ required: true, message: '请输入实验名称' }]}>
                <Input placeholder="ex: 001_MSRResNet_x4_DIV2K" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="scale" label="放大倍数" initialValue={4}
                rules={[{ required: true }]}>
                <Select options={[
                  { label: '×2', value: 2 },
                  { label: '×3', value: 3 },
                  { label: '×4', value: 4 },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="num_gpu" label="GPU 数量" initialValue={1}>
                <InputNumber min={0} max={8} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="manual_seed" label="随机种子" initialValue={0}
                help="0=随机">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="gpu_ids" label="GPU 编号" initialValue="0"
                help="逗号分隔，ex: 0,1,2">
                <Input placeholder="0,1,2" />
              </Form.Item>
            </Col>
          </Row>
        </Card>
      )}

      {/* Step 2: 数据集 */}
      {step === 2 && (
        <Card title="数据集配置">
          <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
            数据集的默认路径在「数据集设置」中配置。如需修改请点击右上角按钮。
          </Text>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="train_root" label="训练集根路径"
                initialValue={info.settings?.train_root || ''}>
                <Input placeholder="./datasets/DIV2K" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="val_root" label="验证集根路径"
                initialValue={info.settings?.val_root || ''}>
                <Input placeholder="./datasets/Set5" />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="gt_size" label="Patch Size" initialValue={128}>
                <InputNumber min={16} max={512} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="dataset_enlarge_ratio" label="数据集放大" initialValue={1}
                help="相当于 epoch 数">
                <InputNumber min={1} max={1000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="batch_size_per_gpu" label="Batch Size/GPU" initialValue={16}>
                <InputNumber min={1} max={256} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="num_worker_per_gpu" label="加载线程/GPU" initialValue={4}>
                <InputNumber min={1} max={16} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="use_hflip" label="水平翻转" valuePropName="checked" initialValue={true}>
                <Switch />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="use_rot" label="旋转" valuePropName="checked" initialValue={true}>
                <Switch />
              </Form.Item>
            </Col>
          </Row>
          <Collapse size="small" items={[{
            key: 'dataset_names',
            label: '数据集名称（用于 YAML 标识和 meta_info 文件查找）',
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="train_dataset_name" label="训练集名" initialValue="DIV2K"
                    help="影响 meta_info 文件路径">
                    <Select mode="tags" maxCount={1}
                      options={(info.datasets || []).map(d => ({ label: d, value: d }))}
                      onChange={v => form.setFieldValue('train_dataset_name', v[0] || 'DIV2K')} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="val_dataset_name" label="验证集名" initialValue="Set5">
                    <Input placeholder="Set5 / Set14 / Urban100 / etc" />
                  </Form.Item>
                </Col>
              </Row>
            ),
          }]} />
        </Card>
      )}

      {/* Step 3: 网络参数 */}
      {step === 3 && (
        <Card title={`网络参数 — ${selectedArch}`}>
          <Row gutter={16}>
            {renderArchParams()}
          </Row>
          <Divider />
          <Text type="secondary">
            提示：List 类型参数请用逗号分隔输入，如 <Tag>6,6,6,6,6,6</Tag>
          </Text>
        </Card>
      )}

      {/* Step 4: 训练参数 */}
      {step === 4 && (
        <div>
          <Card title="优化器" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="optim_type" label="优化器" initialValue="Adam">
                  <Select options={[
                    { label: 'Adam', value: 'Adam' },
                    { label: 'AdamW', value: 'AdamW' },
                    { label: 'SGD', value: 'SGD' },
                  ]} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="lr" label="学习率" initialValue={0.0002}>
                  <InputNumber min={1e-7} max={1} step={1e-5} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="weight_decay" label="权重衰减" initialValue={0}>
                  <InputNumber min={0} step={1e-5} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="ema_decay" label="EMA 衰减" initialValue={0.999}
                  help="0=不启用">
                  <InputNumber min={0} max={0.9999} step={0.001} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card title="学习率调度器" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="scheduler_type" label="调度器类型" initialValue="MultiStepLR">
                  <Select onChange={v => {
                    const tpl = info.scheduler_templates[v];
                    if (tpl && tpl.milestones) {
                      form.setFieldValue('scheduler_params.milestones', tpl.milestones.join(','));
                      form.setFieldValue('scheduler_params.gamma', tpl.gamma);
                    }
                  }} options={Object.keys(info.scheduler_templates).map(k => ({ label: k, value: k }))} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name={['scheduler_params', 'milestones']} label="学习率下降节点"
                  initialValue="250000,400000,450000,475000"
                  help="逗号分隔">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name={['scheduler_params', 'gamma']} label="衰减因子" initialValue={0.5}>
                  <InputNumber min={0.01} max={1} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card title="迭代与 Loss" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="total_iter" label="总迭代数" initialValue={500000}
                  rules={[{ required: true }]}>
                  <InputNumber min={1000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="warmup_iter" label="Warmup 迭代" initialValue={-1}
                  help="-1 = 不启用">
                  <InputNumber min={-1} max={50000} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="use_amp" label="混合精度(AMP)" valuePropName="checked" initialValue={false}>
                  <Switch />
                </Form.Item>
              </Col>
            </Row>
            <Divider>损失函数</Divider>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="pixel_loss_type" label="像素损失" initialValue="L1Loss">
                  <Select options={Object.keys(info.loss_templates).map(k => ({
                    label: k, value: k,
                  }))} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="pixel_loss_weight" label="像素损失权重" initialValue={1.0}>
                  <InputNumber min={0} step={0.1} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="has_perceptual_loss" label="感知损失" valuePropName="checked" initialValue={false}>
                  <Switch />
                </Form.Item>
              </Col>
              {form.getFieldValue('has_perceptual_loss') && (
                <Col span={6}>
                  <Form.Item name="perceptual_loss_weight" label="感知损失权重" initialValue={0.1}>
                    <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              )}
            </Row>
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="has_gan_loss" label="GAN 损失" valuePropName="checked" initialValue={false}>
                  <Switch />
                </Form.Item>
              </Col>
              {form.getFieldValue('has_gan_loss') && (
                <Col span={6}>
                  <Form.Item name="gan_loss_weight" label="GAN 损失权重" initialValue={0.1}>
                    <InputNumber min={0} step={0.01} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              )}
            </Row>
          </Card>

          <Collapse size="small" items={[{
            key: 'advanced',
            label: '⚙ 高级参数',
            children: (
              <div>
                <Card title="日志与验证" size="small" style={{ marginBottom: 12 }}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <Form.Item name="print_freq" label="打印频率" initialValue={100}>
                        <InputNumber min={1} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="save_checkpoint_freq" label="保存频率" initialValue={5000}>
                        <InputNumber min={100} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="val_freq" label="验证频率" initialValue={5000}>
                        <InputNumber min={100} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col span={6}>
                      <Form.Item name="save_img" label="保存验证图" valuePropName="checked" initialValue={true}>
                        <Switch />
                      </Form.Item>
                    </Col>
                  </Row>
                </Card>
                <Collapse size="small" items={[{
                  key: 'optim_betas',
                  label: '优化器 betas（仅 Adam 系列）',
                  children: (
                    <Row gutter={16}>
                      <Col span={6}>
                        <Form.Item name="betas" label="Betas" initialValue="0.9,0.999"
                          help="逗号分隔的两个值">
                          <Input />
                        </Form.Item>
                      </Col>
                    </Row>
                  ),
                }]} />
              </div>
            ),
          }]} />
        </div>
      )}

      {/* Step 5: 预览 */}
      {step === 5 && (
        <Card title="YAML 预览"
          extra={
            <Space>
              <Button type="primary" icon={<FileTextOutlined />}
                onClick={() => setSaveModalOpen(true)}
                disabled={!yaml}>
                保存到文件
              </Button>
              <Button onClick={() => { navigator.clipboard.writeText(yaml); message.success('已复制'); }}>
                复制
              </Button>
            </Space>
          }>
          <pre style={{
            background: '#f5f5f5', padding: 16, borderRadius: 4,
            maxHeight: '65vh', overflow: 'auto', fontSize: 12, fontFamily: 'monospace',
          }}>
            {yaml || '（请先生成 YAML）'}
          </pre>
        </Card>
      )}

      {/* 导航按钮 */}
      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <Space>
          {step > 0 && <Button onClick={() => setStep(s => s - 1)}>上一步</Button>}
          {step < 4 && <Button type="primary" onClick={() => setStep(s => s + 1)}>下一步</Button>}
          {step === 4 && (
            <Button type="primary" onClick={handleGenerate}>
              📄 生成 YAML
            </Button>
          )}
          {step === 5 && (
            <Button onClick={() => setStep(0)}>重新配置</Button>
          )}
        </Space>
      </div>

      {/* 保存对话框 */}
      <Modal title="保存配置到文件" open={saveModalOpen}
        onCancel={() => setSaveModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        okText="保存">
        <Form layout="vertical">
          <Form.Item name="save_subdir" label="保存到子目录"
            initialValue={(info.model_types[selectedModelType]?.label || '').split(' ')[0] || 'Custom'}>
            <Select mode="tags" maxCount={1}
              options={(info.options_dirs || []).map(d => ({ label: d, value: d }))}
              placeholder="输入或选择子目录"
              onChange={v => form.setFieldValue('save_subdir', v[0] || 'Custom')} />
          </Form.Item>
          <Form.Item name="save_filename" label="文件名（不含路径）"
            initialValue={form.getFieldValue('name') || 'config'}
            help="自动补 .yml 后缀">
            <Input placeholder="train_MSRResNet_x4" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 数据集设置对话框 */}
      <Modal title="数据集默认路径设置" open={settingsModalOpen}
        onCancel={() => setSettingsModalOpen(false)}
        onOk={async () => {
          await fetch('/api/configs/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              train_root: form.getFieldValue('_settings_train_root') || info.settings.train_root,
              val_root: form.getFieldValue('_settings_val_root') || info.settings.val_root,
            }),
          });
          message.success('设置已保存');
          setSettingsModalOpen(false);
        }}
        okText="保存设置">
        <Form layout="vertical">
          <Form.Item name="_settings_train_root" label="默认训练集根路径"
            initialValue={info.settings?.train_root || ''}>
            <Input placeholder="./datasets" />
          </Form.Item>
          <Form.Item name="_settings_val_root" label="默认验证集根路径"
            initialValue={info.settings?.val_root || ''}>
            <Input placeholder="./datasets" />
          </Form.Item>
          <Text type="secondary">
            这些路径将作为新配置的默认值。可在生成配置时单独覆盖。
          </Text>
        </Form>
      </Modal>
    </div>
  );
};

export default ConfigEditor;
