import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

// ── 任务队列 ──

export interface Task {
  id: string;
  name: string;
  config_path: string;
  override_args: string;
  gpu_count: number;
  status: string;
  priority: number;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  log_path?: string;
  exit_code?: number;
  error_msg?: string;
}

export interface TaskStats {
  total: number;
  queued?: number;
  running?: number;
  completed?: number;
  failed?: number;
}

export const fetchTasks = (status?: string) =>
  api.get<{ tasks: Task[]; stats: TaskStats }>('/tasks', { params: { status } }).then(r => r.data);

export const createTask = (data: { name: string; config_path: string; override_args?: string; gpu_count?: number; priority?: number }) =>
  api.post<{ task: Task }>('/tasks', data).then(r => r.data);

export const cancelTask = (id: string) =>
  api.post(`/tasks/${id}/cancel`).then(r => r.data);

export const deleteTask = (id: string) =>
  api.delete(`/tasks/${id}`).then(r => r.data);

export const fetchTaskLog = (id: string, tail = 100) =>
  api.get<{ log: string }>(`/tasks/${id}/log`, { params: { tail } }).then(r => r.data);

// ── 实验管理 ──

export interface Checkpoint {
  name: string;
  size_mb: number;
  mtime: string;
}

export interface ExpImage {
  name: string;
  path: string;
}

export interface Experiment {
  name: string;
  status: string;
  has_config: boolean;
  has_log: boolean;
  has_psnr: boolean;
  has_ssim: boolean;
  val_dataset?: string;
  log_lines: number;
  mtime: string;
  checkpoints: Checkpoint[];
  images: ExpImage[];
  config_path?: string;
  log_path?: string;
}

export const fetchExperiments = (root?: string) =>
  api.get<{ experiments: Experiment[]; root: string }>('/experiments', { params: { root } }).then(r => r.data);

export const fetchExperiment = (name: string, root?: string) =>
  api.get<{ experiment: Experiment | null }>(`/experiments/${name}`, { params: { root } }).then(r => r.data);

export const fetchExpConfig = (name: string, root?: string) =>
  api.get<{ content: string }>(`/experiments/${name}/config`, { params: { root } }).then(r => r.data);

export const fetchExpLog = (name: string, tail = 100, root?: string) =>
  api.get<{ log: string }>(`/experiments/${name}/log`, { params: { tail, root } }).then(r => r.data);

// ── 训练监控 ──

export interface MetricPoint {
  iter: number;
  value: number;
}

export const fetchMetrics = (name: string, tag: string) =>
  api.get<{ tag: string; data: MetricPoint[] }>(`/experiments/${name}/metrics`, { params: { tag } }).then(r => r.data);

export const fetchAllMetrics = (name: string) =>
  api.get<{ metrics: Record<string, MetricPoint[]>; info: any }>(`/experiments/${name}/all-metrics`).then(r => r.data);

export const fetchTags = (name: string) =>
  api.get<{ tags: string[] }>(`/experiments/${name}/tags`).then(r => r.data);

// ── YAML 配置生成 ──

export interface ConfigGenerateReq {
  experiment_name: string;
  model_type: string;
  model_params: Record<string, unknown>;
  batch_size: number;
  lr: number;
  total_iter: number;
  fp16: boolean;
  train_root: string;
  val_root: string;
  gt_size: number;
  gpu_ids: string;
}

export const generateConfig = (data: ConfigGenerateReq) =>
  api.post<{ yaml: string }>('/configs/generate', data).then(r => r.data);

// ── 信息 ──

export interface LabInfo {
  exp_root: string;
  tb_root: string;
  project_root: string;
}

export const fetchLabInfo = () =>
  api.get<LabInfo>('/info').then(r => r.data);
