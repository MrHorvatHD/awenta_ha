"""Load the integration's pure modules by file path (the integration folder has a select.py that would shadow the stdlib)."""
import importlib.util
import os
import sys

_DIR = os.path.join(os.path.dirname(__file__), "..", "custom_components", "awenta_ahr")


def load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(_DIR, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # also makes `import frames` inside unit_server work
    spec.loader.exec_module(module)
    return module
