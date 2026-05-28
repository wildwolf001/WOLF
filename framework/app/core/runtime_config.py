"""
Runtime Configuration - Dynamic configuration that can be updated at runtime
Supports API key management and model selection for multiple LLM providers
"""
from pydantic import BaseModel
from typing import Optional, Dict
import json
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Supported LLM providers and their models
LLM_PROVIDERS = {
    "minimax": {
        "name": "MiniMax",
        "models": ["abab6.5s-chat", "abab6-chat", "abab5.5s-chat", "MiniMax-M2.7", "MiniMax-M2"],
        "requires_group_id": True,
        "api_key_label": "MiniMax API Key",
        "group_id_label": "MiniMax Group ID"
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-coder"],
        "requires_group_id": False,
        "api_key_label": "DeepSeek API Key",
        "group_id_label": None
    },
    "qwen": {
        "name": "Qwen (Alibaba)",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"],
        "requires_group_id": False,
        "api_key_label": "Qwen API Key",
        "group_id_label": None
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "requires_group_id": False,
        "api_key_label": "OpenAI API Key",
        "group_id_label": None
    },
    "anthropic": {
        "name": "Anthropic",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "requires_group_id": False,
        "api_key_label": "Anthropic API Key",
        "group_id_label": None
    },
    "zhipu": {
        "name": "Zhipu AI (智谱)",
        "models": ["glm-4", "glm-4-flash", "glm-3-turbo"],
        "requires_group_id": False,
        "api_key_label": "Zhipu API Key",
        "group_id_label": None
    },
    "moonshot": {
        "name": "Moonshot (月之暗面)",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "requires_group_id": False,
        "api_key_label": "Moonshot API Key",
        "group_id_label": None
    }
}


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider"""
    api_key: Optional[str] = None
    group_id: Optional[str] = None  # For providers that need it (MiniMax)
    model: str = ""


class RuntimeConfig(BaseModel):
    """Runtime configuration that can be updated without restart"""
    current_provider: str = "minimax"
    providers: Dict[str, ProviderConfig] = {
        "minimax": ProviderConfig(model="MiniMax-M2.7"),
        "deepseek": ProviderConfig(model="deepseek-chat"),
        "qwen": ProviderConfig(model="qwen-turbo"),
        "openai": ProviderConfig(model="gpt-4o"),
        "anthropic": ProviderConfig(model="claude-3-5-sonnet-20241022"),
        "zhipu": ProviderConfig(model="glm-4"),
        "moonshot": ProviderConfig(model="moonshot-v1-8k"),
    }
    # Local Storage Paths
    local_storage_path: str = "./wolf_data"
    knowledge_base_path: str = "./wolf_data/knowledge"
    sessions_path: str = "./wolf_data/sessions"
    upload_path: str = "./wolf_data/uploads"

    # Additional Working Directories - 参照 cc-haha 的 additionalWorkingDirectories
    # 支持多个工作目录，key 是路径，value 是来源标识
    # 来源：originalCwd, cliArg, userSettings, session, mainAgent, auto_added
    additional_working_directories: Dict[str, str] = {}

    def get_additional_working_directories(self) -> Dict[str, str]:
        """获取所有额外的工作目录"""
        return self.additional_working_directories

    def add_working_directory(self, path: str, source: str = "session") -> bool:
        """添加额外的工作目录"""
        if not path:
            return False
        abs_path = os.path.abspath(path)
        self.additional_working_directories[abs_path] = source
        return True

    def remove_working_directory(self, path: str) -> bool:
        """移除工作目录"""
        if not path:
            return False
        abs_path = os.path.abspath(path)
        if abs_path in self.additional_working_directories:
            del self.additional_working_directories[abs_path]
            return True
        return False

    def set_work_directory(self, path: str) -> None:
        """Set the work directory for agent file operations (backward compatibility)"""
        if path:
            self.add_working_directory(path, "cliArg")

    def get_work_directory(self) -> str:
        """Get primary work directory (backward compatibility)"""
        if self.additional_working_directories:
            # 返回第一个目录
            return list(self.additional_working_directories.keys())[0]
        return ""

    def get_all_working_directories(self) -> list:
        """获取所有工作目录（包括原来的 work_directory 兼容）"""
        dirs = list(self.additional_working_directories.keys())
        return dirs

    def set_provider_api_key(self, provider: str, api_key: str) -> None:
        """Set API key for a provider"""
        if provider not in self.providers:
            self.providers[provider] = ProviderConfig()
        self.providers[provider].api_key = api_key

    def set_provider_group_id(self, provider: str, group_id: str) -> None:
        """Set Group ID for a provider (e.g., MiniMax)"""
        if provider not in self.providers:
            self.providers[provider] = ProviderConfig()
        self.providers[provider].group_id = group_id

    def set_provider_model(self, provider: str, model: str) -> None:
        """Set model for a provider"""
        if provider not in self.providers:
            self.providers[provider] = ProviderConfig()
        self.providers[provider].model = model

    def set_storage_path(self, path_type: str, path: str) -> None:
        """Set a storage path"""
        if path_type == "local_storage":
            self.local_storage_path = path
        elif path_type == "knowledge_base":
            self.knowledge_base_path = path
        elif path_type == "sessions":
            self.sessions_path = path
        elif path_type == "upload":
            self.upload_path = path

    def get_storage_paths(self) -> Dict[str, str]:
        """Get all storage paths"""
        return {
            "local_storage_path": self.local_storage_path,
            "knowledge_base_path": self.knowledge_base_path,
            "sessions_path": self.sessions_path,
            "upload_path": self.upload_path
        }

    def to_dict(self) -> dict:
        """Convert to dictionary, masking API keys"""
        result = {
            "current_provider": self.current_provider,
            "providers": {},
            "storage_paths": {
                "local_storage_path": self.local_storage_path,
                "knowledge_base_path": self.knowledge_base_path,
                "sessions_path": self.sessions_path,
                "upload_path": self.upload_path
            },
            "additional_working_directories": self.additional_working_directories,
            "work_directory": self.get_work_directory()  # backward compatibility
        }
        for provider, config in self.providers.items():
            result["providers"][provider] = {
                "api_key": "***" + config.api_key[-4:] if config.api_key else None,
                "group_id": config.group_id,
                "model": config.model,
                "has_api_key": bool(config.api_key)
            }
        return result


# Global runtime config instance
runtime_config = RuntimeConfig()

# Config file path for persistence
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")

# MiniMax API base URL (configurable via MINIMAX_BASE_URL env var)
# Domestic China: https://api.minimaxi.com
# International: https://api.minimax.io
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com")


def save_config() -> None:
    """Save configuration to file"""
    try:
        config_data = {
            "current_provider": runtime_config.current_provider,
            "providers": {},
            "storage_paths": {
                "local_storage_path": runtime_config.local_storage_path,
                "knowledge_base_path": runtime_config.knowledge_base_path,
                "sessions_path": runtime_config.sessions_path,
                "upload_path": runtime_config.upload_path
            },
            "additional_working_directories": runtime_config.additional_working_directories
        }
        for provider, config in runtime_config.providers.items():
            config_data["providers"][provider] = {
                "api_key": config.api_key,
                "group_id": config.group_id,
                "model": config.model
            }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2)
    except Exception as e:
        print(f"Failed to save config: {e}")


def load_config() -> None:
    """Load configuration from file and environment variables"""
    # First load from .env environment variables
    env_provider = os.getenv("LLM_PROVIDER", "minimax")
    if env_provider in runtime_config.providers:
        runtime_config.current_provider = env_provider

    # Load API keys from environment if not already set
    minimax_key = os.getenv("MINIMAX_API_KEY")
    if minimax_key and minimax_key not in ("your-minimax-api-key", "your-api-key", "sk-your-key", "") \
            and not runtime_config.providers["minimax"].api_key:
        runtime_config.providers["minimax"].api_key = minimax_key
        # Only set group_id if it's a real value, not a placeholder
        env_group_id = os.getenv("MINIMAX_GROUP_ID", "")
        if env_group_id and env_group_id not in ("your-group-id", "None", ""):
            runtime_config.providers["minimax"].group_id = env_group_id
        runtime_config.providers["minimax"].model = os.getenv("MINIMAX_MODEL", "abab6.5s-chat")

    # Try to load from config file (overrides env vars if present)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            runtime_config.current_provider = config_data.get("current_provider", "minimax")
            for provider, data in config_data.get("providers", {}).items():
                runtime_config.providers[provider] = ProviderConfig(
                    api_key=data.get("api_key"),
                    group_id=data.get("group_id"),
                    model=data.get("model", "")
                )
            # Load storage paths
            storage_paths = config_data.get("storage_paths", {})
            runtime_config.local_storage_path = storage_paths.get("local_storage_path", "./wolf_data")
            runtime_config.knowledge_base_path = storage_paths.get("knowledge_base_path", "./wolf_data/knowledge")
            runtime_config.sessions_path = storage_paths.get("sessions_path", "./wolf_data/sessions")
            runtime_config.upload_path = storage_paths.get("upload_path", "./wolf_data/uploads")
            # Load additional working directories
            runtime_config.additional_working_directories = config_data.get("additional_working_directories", {})
    except Exception as e:
        print(f"Failed to load config: {e}")


# Load config on module import
load_config()
