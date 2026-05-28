"""
Runtime Configuration
"""
from typing import Optional
from .config import Config, load_config, DEFAULT_CONFIG


class RuntimeConfig:
    """Runtime configuration singleton"""

    _instance: Optional['RuntimeConfig'] = None
    _config: Config = DEFAULT_CONFIG

    def __init__(self):
        raise RuntimeError("Use get_instance() instead")

    @classmethod
    def get_instance(cls) -> 'RuntimeConfig':
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

    @classmethod
    def get_config(cls) -> Config:
        return cls._config

    @classmethod
    def set_config(cls, config: Config) -> None:
        cls._config = config

    @classmethod
    def load(cls) -> Config:
        cls._config = load_config()
        return cls._config


def get_runtime_config() -> RuntimeConfig:
    """Get runtime configuration"""
    return RuntimeConfig.get_instance()


def get_config() -> Config:
    """Get current configuration"""
    return RuntimeConfig.get_config()