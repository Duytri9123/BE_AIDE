# Import routers on demand. Importing one endpoint must not scan the entire CAD catalog.
from importlib import import_module

def __getattr__(name):
    if name.startswith('_'):
        raise AttributeError(name)
    try:
        module = import_module(f'{__name__}.{name}')
    except ModuleNotFoundError as error:
        if error.name == f'{__name__}.{name}':
            raise AttributeError(name) from error
        raise
    globals()[name] = module
    return module

__all__ = [
    "analyze",
    "bom",
    "export",
    "chat",
    "user_library",
    "auth",
    "users",
    "projects",
    "devices",
    "providers",
]
