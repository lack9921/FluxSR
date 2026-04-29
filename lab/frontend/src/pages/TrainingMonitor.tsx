import React, { useEffect, useState } from 'react';
import { Select, Button, Card, Row, Col, Spin, Space, message } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { fetchExperiments, fetchAllMetrics, Experiment } from '../api';

const METRIC_LABELS: Record<string, string> = {
  l_pix: 'L_pix (Loss)',
  psnr: 'PSNR',
  ssim: 'SSIM',
};

const METRIC_COLORS: Record<string, string> = {
  l_pix: '#5470c6',
  psnr: '#91cc75',
  ssim: '#ee6666',
};

const TrainingMonitor: React.FC = () => {
  const [exps, setExps] = useState<Experiment[]>([]);
  const [selectedExp, setSelectedExp] = useState<string>('');
  const [metricsData, setMetricsData] = useState<Record<string, any>>({});
  const [metricsInfo, setMetricsInfo] = useState<any>({});
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['l_pix']);
  const [chartOption, setChartOption] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchExperiments().then(d => setExps(d.experiments)).catch(() => {});
  }, []);

  const loadData = () => {
    if (!selectedExp) return;
    setLoading(true);
    fetchAllMetrics(selectedExp)
      .then((res) => {
        const metrics = res.metrics || {};
        const info = res.info || {};
        setMetricsData(metrics);
        setMetricsInfo(info);

        const available = Object.keys(metrics);
        if (available.length === 0) {
          message.warning('该实验没有可用的指标数据（日志中未找到 l_pix 或验证结果）');
          setChartOption(null);
          return;
        }

        // 自动选择：优先 psnr/ssim，否则第一个
        let toShow: string[];
        if (available.includes('psnr')) toShow = ['psnr'];
        else if (available.includes('ssim')) toShow = ['ssim'];
        else toShow = [available[0]];
        setSelectedMetrics(toShow);
        buildChart(metrics, toShow);
      })
      .catch((err) => {
        message.error('加载指标失败');
        setChartOption(null);
      })
      .finally(() => setLoading(false));
  };

  const buildChart = (metrics: Record<string, any>, selected: string[]) => {
    const series = selected
      .filter(name => metrics[name] && metrics[name].length > 0)
      .map(name => {
        const data = metrics[name];
        const label = METRIC_LABELS[name] || name;
        return {
          name: label,
          type: 'line' as const,
          data: data.map((d: any) => d.value),
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 2, color: METRIC_COLORS[name] || '#5470c6' },
          itemStyle: { color: METRIC_COLORS[name] || '#5470c6' },
        };
      });

    const xData = selected.length > 0 && metrics[selected[0]]
      ? metrics[selected[0]].map((d: any) => d.iter || d.step)
      : [];

    const option = {
      tooltip: {
        trigger: 'axis' as const,
        formatter: (params: any[]) => {
          const iter = params[0]?.dataIndex != null ? xData[params[0].dataIndex] : '?';
          let html = `<b>iter: ${iter}</b><br/>`;
          params.forEach((p: any) => {
            html += `${p.marker} ${p.seriesName}: <b>${Number(p.value).toFixed(4)}</b><br/>`;
          });
          return html;
        },
      },
      legend: {
        data: series.map(s => s.name),
        bottom: 0,
      },
      xAxis: {
        type: 'category' as const,
        data: xData,
        name: 'Iteration',
        nameLocation: 'center',
        nameGap: 25,
      },
      yAxis: {
        type: 'value' as const,
        name: '',
      },
      series,
      grid: { left: '6%', right: '5%', top: '5%', bottom: '18%' },
      dataZoom: [
        { type: 'inside' as const, start: 0, end: 100 },
        { type: 'slider' as const, start: 0, end: 100, bottom: 30 },
      ],
    };

    setChartOption(option);
  };

  const handleMetricChange = (values: string[]) => {
    setSelectedMetrics(values);
    if (values.length > 0) {
      buildChart(metricsData, values);
    }
  };

  useEffect(() => {
    if (selectedExp) loadData();
  }, [selectedExp]);

  const availableMetrics = Object.keys(metricsData);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2>📈 训练监控</h2>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={10}>
          <Select
            style={{ width: '100%' }}
            placeholder="选择实验"
            value={selectedExp || undefined}
            onChange={setSelectedExp}
            showSearch
            filterOption={(input, option) =>
              (option?.label as string || '').toLowerCase().includes(input.toLowerCase())
            }
            options={exps.map(e => ({
              label: `${e.name}${e.status === 'running' ? ' 🔄' : e.status === 'completed' ? ' ✅' : ''}`,
              value: e.name,
            }))}
          />
        </Col>
        <Col span={10}>
          <Select
            style={{ width: '100%' }}
            mode="multiple"
            placeholder="选择指标（可多选）"
            value={selectedMetrics}
            onChange={handleMetricChange}
            options={availableMetrics.map(t => ({
              label: METRIC_LABELS[t] || t,
              value: t,
            }))}
          />
        </Col>
        <Col span={4}>
          {selectedExp && (
            <Space>
              <span style={{ color: '#888', fontSize: 13 }}>
                {metricsInfo.val_dataset && `验证集: ${metricsInfo.val_dataset}`}
                {metricsInfo.total_iters > 0 && ` | 总迭代: ${metricsInfo.total_iters.toLocaleString()}`}
              </span>
            </Space>
          )}
        </Col>
      </Row>

      <Spin spinning={loading}>
        <Card>
          {chartOption ? (
            <ReactECharts option={chartOption} style={{ height: 450 }} />
          ) : (
            <div style={{ height: 450, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#888' }}>
              {selectedExp
                ? '暂无可用指标数据\n（请确认实验日志包含训练或验证输出）'
                : '请选择实验和指标'}
            </div>
          )}
        </Card>
      </Spin>

      {/* 实验信息卡片 */}
      {selectedExp && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={8}>
            <Card size="small" title="可用指标">
              {availableMetrics.length > 0
                ? availableMetrics.map(m => (
                    <span key={m} style={{ display: 'block', marginBottom: 4 }}>
                      <span style={{
                        display: 'inline-block', width: 8, height: 8, borderRadius: 4,
                        backgroundColor: METRIC_COLORS[m] || '#5470c6', marginRight: 6,
                      }} />
                      {METRIC_LABELS[m] || m}
                      <span style={{ color: '#999', marginLeft: 6, fontSize: 12 }}>
                        ({metricsData[m]?.length || 0} 个数据点)
                      </span>
                    </span>
                  ))
                : <span style={{ color: '#999' }}>日志只包含训练步（l_pix），没有验证结果</span>
              }
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="数据统计">
              {selectedMetrics.map(m => {
                const data = metricsData[m] || [];
                if (data.length === 0) return null;
                const values = data.map((d: any) => d.value);
                return (
                  <div key={m} style={{ marginBottom: 4 }}>
                    <b>{METRIC_LABELS[m] || m}</b>
                    <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                      最佳: {m === 'l_pix' ? Math.min(...values).toFixed(4) : Math.max(...values).toFixed(4)}
                      {' @ '}
                      {m === 'l_pix'
                        ? `${data[values.indexOf(Math.min(...values))].iter || data[values.indexOf(Math.min(...values))].step} iter`
                        : `${data[values.indexOf(Math.max(...values))].iter || data[values.indexOf(Math.max(...values))].step} iter`}
                    </span>
                  </div>
                );
              })}
            </Card>
          </Col>
          <Col span={8}>
            <Card size="small" title="操作提示">
              <ul style={{ margin: 0, paddingLeft: 16, color: '#666', fontSize: 13 }}>
                <li>滚轮缩放曲线</li>
                <li>下方滑块选择显示范围</li>
                <li>多选指标可叠加显示</li>
                <li>悬浮查看具体数值</li>
              </ul>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
};

export default TrainingMonitor;
