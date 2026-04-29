import React, { useEffect, useState } from 'react';
import { Select, Button, Card, Row, Col, Spin, Space } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { fetchExperiments, fetchTags, fetchMetrics, Experiment } from '../api';

const TrainingMonitor: React.FC = () => {
  const [exps, setExps] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<string>('');
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string>('val/psnr');
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchExperiments().then(d => setExps(d.experiments)); }, []);

  const loadData = () => {
    if (!selectedExp) return;
    setLoading(true);
    Promise.all([
      fetchTags(selectedExp),
      fetchMetrics(selectedExp, selectedTag),
    ]).then(([tagsRes, metricsRes]) => {
      setTags(tagsRes.tags);
      if (!tagsRes.tags.includes(selectedTag) && tagsRes.tags.length > 0) {
        setSelectedTag(tagsRes.tags[0]);
      }
      const option = {
        tooltip: { trigger: 'axis' as const },
        xAxis: { type: 'category' as const, data: metricsRes.data.map(d => d.step) },
        yAxis: { type: 'value' as const, name: selectedTag.split('/').pop() },
        series: [{
          data: metricsRes.data.map(d => d.value),
          type: 'line',
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.1 },
        }],
        grid: { left: '5%', right: '5%', top: '5%', bottom: '10%' },
      };
      setChartData(option);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { if (selectedExp) loadData(); }, [selectedExp]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>📈 训练监控</h2>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Select style={{ width: '100%' }} placeholder="选择实验" value={selectedExp || undefined} onChange={setSelectedExp}
            options={exps.map(e => ({ label: e.name, value: e.name }))} />
        </Col>
        <Col span={8}>
          <Select style={{ width: '100%' }} placeholder="选择指标" value={selectedTag} onChange={setSelectedTag}
            options={tags.map(t => ({ label: t, value: t }))} />
        </Col>
        <Col span={8}>
          <Space>
            {selectedExp && (
              <span style={{ color: '#888' }}>
                {exps.find(e => e.name === selectedExp)?.is_running ? '🔄 运行中' : '✅ 已完成'}
              </span>
            )}
          </Space>
        </Col>
      </Row>

      <Spin spinning={loading}>
        <Card>
          {chartData ? (
            <ReactECharts option={chartData} style={{ height: 400 }} />
          ) : (
            <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
              {selectedExp ? '加载中...' : '请选择实验和指标'}
            </div>
          )}
        </Card>
      </Spin>
    </div>
  );
};

export default TrainingMonitor;
