"""Plugin agent loader — hot-discovers BasePlugin subclasses in plugins/."""

import os
import sys
import importlib
import inspect
import pkgutil
from pathlib import Path
from core.logger import setup_logger


class PluginAgent:
    """Base class for all plugin agents. Subclass this to create a custom agent."""

    def __init__(self, name: str, config: dict, llm=None, kali=None):
        self.name = name
        self.config = config
        self.logger = setup_logger(name)
        self.llm = llm
        self.kali = kali
        self.work_dir = Path(__file__).resolve().parent.parent
        self.description = ""
        self.version = "1.0.0"
        self.author = ""

    async def on_load(self):
        pass

    async def on_tick(self, cycle: int) -> str | None:
        return None

    def get_metadata(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
        }


def discover_plugins(plugin_dir: str | Path = None) -> list[PluginAgent]:
    logger = setup_logger("plugin_loader")
    if plugin_dir is None:
        plugin_dir = Path(__file__).resolve().parent
    else:
        plugin_dir = Path(plugin_dir)

    plugins = []
    plugin_dir_str = str(plugin_dir)

    if plugin_dir_str not in sys.path:
        sys.path.insert(0, plugin_dir_str)

    for importer, modname, is_pkg in pkgutil.iter_modules([plugin_dir_str]):
        if modname.startswith("__"):
            continue
        if is_pkg:
            continue
        try:
            module = importlib.import_module(modname)
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, PluginAgent) and cls is not PluginAgent:
                    try:
                        instance = cls(config={})
                    except TypeError:
                        try:
                            instance = cls()
                        except TypeError:
                            logger.warning(
                                f"Could not instantiate {name}: incompatible constructor"
                            )
                            continue
                    plugins.append(instance)
                    logger.info(f"Plugin loaded: {instance.name} (v{instance.version})")
        except Exception as e:
            logger.warning(f"Failed to load plugin {modname}: {e}")

    return plugins
