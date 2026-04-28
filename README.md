# FluxSR 🔥

> A refined super-resolution framework built on the shoulders of [BasicSR](https://github.com/XPixelGroup/BasicSR).  
> Cleaner codebase, modular design, and extended capabilities for modern SR research.

FluxSR is an evolution of BasicSR — preserving its solid foundation while rethinking the architecture for better extensibility, cleaner code organization, and easier customization.

## 🌟 Key Features

- **Modular Architecture**: Carefully restructured components for plug-and-play experimentation
- **Familiar Workflow**: Train, test, and inference pipelines inherited from BasicSR — minimal learning curve
- **Extended Capabilities**: Built-in support for attention-based architectures (SwinIR, etc.)
- **Production-Ready**: Comprehensive training scripts, loss functions, and metric evaluations
- **Training Queue**: Web-based queue manager for batch experiment submission and monitoring

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

### Training Queue

FluxSR includes a web-based training queue system for managing multiple experiments:

```bash
# Install queue dependencies
pip install fastapi uvicorn

# Start the queue server
python -m fluxsr.queue.server

# Open http://localhost:8899 in your browser
```

Features:
- Submit, reorder, and monitor training tasks from a web dashboard
- Auto-generated experiment names with timestamps
- Dynamic config overrides via `--override key=value`
- Failed task retry with one click

See [Training Queue Documentation](docs/queue.md) for details.

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
│   ├── queue/        # Training queue system (Web UI + scheduler)
│   └── utils/        # Utilities & helpers
├── options/          # Config files
├── scripts/          # Utility scripts
├── tests/            # Unit tests
└── docs/             # Documentation
```

## 📄 License

This project is licensed under the Apache License 2.0.

## 🙏 Acknowledgements

FluxSR stands on the shoulders of [BasicSR](https://github.com/XPixelGroup/BasicSR) by Xintao Wang et al. We are deeply grateful for their foundational work in the image super-resolution community.
