# FluxSR 🔥

> A refined super-resolution framework built on the shoulders of [BasicSR](https://github.com/XPixelGroup/BasicSR).  
> Cleaner codebase, modular design, and extended capabilities for modern SR research.

FluxSR is an evolution of BasicSR — preserving its solid foundation while rethinking the architecture for better extensibility, cleaner code organization, and easier customization.

## 🌟 Key Features

- **Modular Architecture**: Carefully restructured components for plug-and-play experimentation
- **Familiar Workflow**: Train, test, and inference pipelines inherited from BasicSR — minimal learning curve
- **Extended Capabilities**: Built-in support for attention-based architectures (SwinIR, etc.)
- **Production-Ready**: Comprehensive training scripts, loss functions, and metric evaluations

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/lack9921/FluxSR.git
cd FluxSR
pip install -r requirements.txt
python setup.py develop
```

### Training

```bash
# Single GPU
python fluxsr/train.py -opt options/train/train_SRGAN.yml

# Distributed training
bash scripts/dist_train.sh 8 /path/to/config
```

### Testing

```bash
python fluxsr/test.py -opt options/test/test_SRGAN.yml
```

## 🧪 FluxSR Lab

A full-stack training management panel for BasicSR experiments. Provides a modern web UI for task queuing, experiment monitoring, config generation, and file management.

```
lab/
├── backend/          FastAPI backend (20 REST endpoints)
└── frontend/         React + TypeScript + Ant Design UI
```

### Getting Started

```bash
# 1. Build the frontend
cd lab/frontend
npm install && npm run build

# 2. Start the backend (serves both API and frontend on port 8899)
cd lab/backend
pip install -r requirements.txt
python main.py

# 3. Open http://localhost:8899 in your browser
```

### Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Queue stats, recent experiments overview |
| **Training Queue** | Submit/cancel/delete training tasks, view real-time logs |
| **Training Monitor** | ECharts curves from TensorBoard data (loss, PSNR, SSIM, LR) |
| **Config Editor** | Form-based YAML config generation for BasicSR |
| **File Explorer** | Browse experiment artifacts (checkpoints, logs, validation images) |

### Usage Tips

- The Lab runs independently from FluxSR core — no code coupling, just subprocess + filesystem access
- VS Code Remote SSH users: start the backend on the server, forward port 8899 to your local browser
- Point `FLUXSR_EXP_ROOT` environment variable to your experiments directory if it's not at the default path

## 📚 Documentation

Coming soon. For now, BasicSR documentation applies with `basicsr` → `fluxsr`.

## 📦 Project Structure

```
FluxSR/
├── fluxsr/           # Main source code
│   ├── archs/        # Model architectures
│   ├── data/         # Data loading & preprocessing
│   ├── losses/       # Loss functions
│   ├── metrics/      # Evaluation metrics
│   ├── models/       # Training/validation models
│   ├── ops/          # Custom operations
│   └── utils/        # Utilities & helpers
├── lab/              # FluxSR Lab — training management panel
│   ├── backend/      # FastAPI backend
│   └── frontend/     # React frontend
├── options/          # Config files
├── scripts/          # Utility scripts
├── tests/            # Unit tests
└── docs/             # Documentation
```

## 📄 License

This project is licensed under the Apache License 2.0.

## 🙏 Acknowledgements

FluxSR stands on the shoulders of [BasicSR](https://github.com/XPixelGroup/BasicSR) by Xintao Wang et al. We are deeply grateful for their foundational work in the image super-resolution community.
