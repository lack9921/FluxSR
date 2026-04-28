# FluxSR - Refined Super-Resolution Framework
# flake8: noqa

# Lazy imports: defer torch-dependent modules until they're actually needed.
# This allows submodules (e.g. queue) to be imported without requiring torch.
def __getattr__(name):
    import importlib
    lazy_modules = {
        'archs': '.archs',
        'data': '.data',
        'losses': '.losses',
        'metrics': '.metrics',
        'models': '.models',
        'ops': '.ops',
        'test': '.test',
        'train': '.train',
        'utils': '.utils',
    }
    if name in lazy_modules:
        return importlib.import_module(lazy_modules[name], __name__)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

from .version import __gitsha__, __version__

# Also expose module-level star-import names via __all__ for backwards compatibility
__all__ = ['archs', 'data', 'losses', 'metrics', 'models', 'ops', 'test', 'train', 'utils']
