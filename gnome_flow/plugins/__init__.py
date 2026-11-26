import importlib.util
import os
from pathlib import Path

BUILTIN_PLUGINS_DIR = Path(__file__).resolve().parent
USER_PLUGINS_DIR = Path(os.path.expanduser("~/.config/gnome-flow/plugins"))

# Regisztrált plug-inok: {block_type: module}
_REGISTRY: dict[str, object] = {}
_LOADED = False


def discover_plugins(force_reload: bool = False) -> dict[str, object]:
    """Betölti a beépített és a felhasználói (~/.config/gnome-flow/plugins) modulokat."""
    global _LOADED
    if _LOADED and not force_reload:
        return _REGISTRY

    _REGISTRY.clear()
    USER_PLUGINS_DIR.mkdir(parents=True, exist_ok=True)

    for folder in (BUILTIN_PLUGINS_DIR, USER_PLUGINS_DIR):
        if not folder.is_dir():
            continue
        for py_file in sorted(folder.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            _load_single_plugin(py_file)

    _LOADED = True
    return _REGISTRY


def _load_single_plugin(filepath: Path):
    mod_name = f"gnome_flow_plugin_{filepath.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, filepath)
    if not spec or not spec.loader:
        return
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        block_type = getattr(module, "TYPE", None)
        mode = getattr(module, "MODE", None)  # 'trigger', 'action', vagy 'condition'
        if block_type and mode in ("trigger", "action", "condition"):
            _REGISTRY[block_type] = module
    except Exception as e:
        print(f"[GNOME Flow Plugin] Failed to load '{filepath.name}': {e}")


def get_plugins_by_mode(mode: str) -> list[object]:
    discover_plugins()
    return [m for m in _REGISTRY.values() if getattr(m, "MODE", None) == mode]


def get_plugin(block_type: str) -> object | None:
    discover_plugins()
    return _REGISTRY.get(block_type)